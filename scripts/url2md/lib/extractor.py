"""内容提取器：文章提取、列表提取、Markdown 转换."""

import asyncio
import html
import json
import logging
import random
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from .selectors import Platform, get_platform_config, is_article_page

logger = logging.getLogger(__name__)

ZHIHU_QUESTION_RE = re.compile(r"zhihu\.com/question/(?P<qid>\d+)/?(?:[?#]|$)")
ZHIHU_ANSWER_URL_RE = re.compile(r"zhihu\.com/question/(?P<qid>\d+)/answer/(?P<aid>\d+)")
ZHIHU_INITIAL_DATA_SELECTOR = "script#js-initialData, script[data-initial-state]"

X_TWEET_ARTICLE_SELECTOR = "article"
X_LOGIN_URL_MARKER = "/i/flow/login"

# x.com 未登录页已剥离 data-testid / div[lang] 等稳定钩子，只能对 article 的
# innerText 做行级解析：handle 行之后是（可选）日期行与正文，互动数字等噪声行截断。
_X_ENGAGEMENT_LINE_RE = re.compile(
    r"^(?:\d[\d.,]*万?|\d+(?:\.\d+)?[KkMm]|\d{1,2}:\d{2}(?:\s*·.*)?|Views|查看|翻译|Translate"
    r"|Show more|显示更多|Show this thread|回复|转发|喜欢|书签|分享|GIF"
    r"|Reply|Repost|Like|Bookmark|Share)$",
    re.I,
)
_X_DATE_LINE_RE = re.compile(
    r"^(?:\d{1,2}\s*(?:秒|分钟|小时|天|周|月|年)前?|\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2}"
    r"|\d{1,2}-\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{1,2}"
    r"(?:,?\s*\d{4})?|\d+[smhd])$",
    re.I,
)


def _parse_x_tweet_lines(lines: list[str]) -> dict:
    """从单条推文 article 的 innerText 行序列中解析 {author, text}."""
    author = ""
    start = len(lines)
    for i, line in enumerate(lines[:8]):
        s = line.strip()
        if s.startswith("@") and 1 < len(s) <= 16 and " " not in s:
            author = s
            start = i + 1
            break
    if not author:
        return {"author": "", "text": ""}
    if start < len(lines) and _X_DATE_LINE_RE.match(lines[start].strip()):
        start += 1
    text_parts: list[str] = []
    for line in lines[start:]:
        s = line.strip()
        if _X_ENGAGEMENT_LINE_RE.match(s):
            break
        text_parts.append(s)
    return {"author": author, "text": "\n".join(text_parts)}


async def _wait_x_articles(page, timeout_ms: int = 20000) -> bool:
    """等待 X 推文 article 渲染出现."""
    try:
        await page.wait_for_selector(X_TWEET_ARTICLE_SELECTOR, timeout=timeout_ms)
        return True
    except Exception:
        return False

DEFAULT_MAX_SCROLL_NO_CHANGE = 3
DEFAULT_TAIL_SCAN_LINES = 30
DEFAULT_SCROLL_STEP_DELAY = 0.3
DEFAULT_SCROLL_SETTLE_DELAY = 0.5
DEFAULT_IMAGE_WIDTH = 600

_DEFAULT_NOISE_HTML_PATTERNS = [
    (r'<div[^>]*class="[^"]*qr-code[^"]*"[^>]*>.*?</div>', ""),
    (r'<div[^>]*class="[^"]*recommend[^"]*"[^>]*>.*?</div>', ""),
    (r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>', ""),
    (r'<div[^>]*id="[^"]*ad[^"]*"[^>]*>.*?</div>', ""),
    (r'<section[^>]*class="[^"]*mp_profile_popup[^"]*"[^>]*>.*?</section>', ""),
    (r'<section[^>]*class="[^"]*js_ad[^"]*"[^>]*>.*?</section>', ""),
    (r'<a[^>]*class="[^"]*appmsg_card[^"]*"[^>]*>.*?</a>', ""),
]


class ExtractError(Exception):
    """提取操作异常."""

    pass


def clean_image_url(url: str, platform: Platform | None = None) -> str:
    """清理图片 URL，移除不必要的参数."""
    if not url:
        return url
    url = url.replace("&amp;", "&")
    try:
        parsed = urlparse(url)
        keep_params = []
        if parsed.query:
            params = parse_qs(parsed.query)
            if platform is not None:
                config = get_platform_config(platform)
                keep_keys = config.get("keep_query_params", [])
            else:
                keep_keys = ["wx_fmt", "tp"]
            for key in keep_keys:
                if key in params:
                    keep_params.append((key, params[key][0]))
        new_query = urlencode(keep_params) if keep_params else ""
        clean_url = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, "")
        )
        return clean_url
    except (ValueError, TypeError):
        return url.split("?")[0].split("#")[0]


def remove_noise_elements(content: str, platform: Platform | None = None) -> str:
    """移除内容中的噪音元素（广告、推荐等）.

    当 platform 为 None 时，使用内置默认模式（向后兼容）。
    当 platform 指定时，从 platforms.yaml 的 noise_html_patterns 读取。
    """
    if platform is not None:
        config = get_platform_config(platform)
        patterns = config.get("noise_html_patterns", [])
    else:
        patterns = [p for p, _ in _DEFAULT_NOISE_HTML_PATTERNS]
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.IGNORECASE)
    return content


@dataclass
class ArticleData:
    """文章数据."""

    title: str
    author: str
    date: str
    url: str
    content: str
    images: list[str] | None = None

    def __post_init__(self):
        if self.images is None:
            self.images = []


def filter_x_thread_tweets(tweets: list[dict]) -> list[dict]:
    """过滤 X 推文串：仅保留与首条推文同作者的推文（主线），保持原顺序.

    首条无作者信息时视为无法判定主线，返回全部推文。
    """
    if not tweets:
        return []
    root_author = tweets[0].get("author") or ""
    if not root_author:
        return tweets
    return [t for t in tweets if (t.get("author") or "") == root_author]


def build_author_text_html(posts: list[dict]) -> str:
    """将 {author, text} 列表合成为 HTML（每条一段，块间以 <hr> 分隔）.

    文本经 html.escape 转义；空文本跳过；相邻重复项去重。
    """
    blocks = []
    prev_key = None
    for t in posts:
        text = (t.get("text") or "").strip()
        if not text:
            continue
        author = html.escape(t.get("author") or "")
        escaped = html.escape(text)
        key = (author, text)
        if key == prev_key:
            continue  # 相邻重复条目（引用视图与时间线视图各渲染一次）
        prev_key = key
        blocks.append(f"<p><strong>{author}</strong></p><p>{escaped}</p>")
    return "\n<hr>\n".join(blocks)


def build_x_thread_html(tweets: list[dict]) -> str:
    """X 推文串渲染入口，见 build_author_text_html."""
    return build_author_text_html(tweets)


async def _extract_x_article(
    page,
    scroll_step_delay: float = DEFAULT_SCROLL_STEP_DELAY,
    scroll_settle_delay: float = DEFAULT_SCROLL_SETTLE_DELAY,
) -> ArticleData | None:
    """提取 X/Twitter 推文串：等待渲染、滚动加载、逐条抽取 tweetText.

    x.com 未登录渲染不稳定（概率性风控墙/慢加载），等待超时后重载重试一次。
    """
    found = await _wait_x_articles(page, timeout_ms=20000)
    if not found:
        try:
            await page.reload(wait_until="domcontentloaded")
            found = await _wait_x_articles(page, timeout_ms=20000)
        except Exception:
            found = False
    if not found:
        current_url = page.url
        if X_LOGIN_URL_MARKER in current_url:
            raise ExtractError(
                "X 页面重定向到登录墙。请在 scripts/url2md/config.yaml 配置 cookies_file 后重试。"
            )
        raise ExtractError(
            f"未找到推文内容（x.com 未登录渲染不稳定，可重试或配置 cookies_file）：{current_url}"
        )
    await _scroll_page(page, step_delay=scroll_step_delay, settle_delay=scroll_settle_delay)
    raw_articles = await page.evaluate(
        """() => {
            // 只取叶子 article：嵌套容器 article 的 innerText 会包含子推文，造成重复
            const all = Array.from(document.querySelectorAll("article"));
            const leaves = all.filter(a => !a.querySelector("article"));
            return (leaves.length ? leaves : all).map(a => ({
                lines: a.innerText.split("\\n").map(s => s.trim()).filter(Boolean),
            }));
        }"""
    )
    kept = filter_x_thread_tweets([_parse_x_tweet_lines(a["lines"]) for a in (raw_articles or [])])
    content_html = build_x_thread_html(kept)
    first = kept[0] if kept else {}
    handle = first.get("author", "")
    snippet = re.sub(r"\s+", " ", first.get("text", ""))[:50].strip()
    title = f"{handle} on X: {snippet}" if handle else await page.title()
    return ArticleData(
        title=title.strip(),
        author=handle,
        date="",
        url=page.url,
        content=content_html,
    )


async def _scroll_page(page, step_delay: float = DEFAULT_SCROLL_STEP_DELAY, settle_delay: float = DEFAULT_SCROLL_SETTLE_DELAY) -> None:
    """滚动页面以加载所有内容."""
    await page.evaluate(f"""
        async () => {{
            const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
            const scrollHeight = document.documentElement.scrollHeight;
            const viewportHeight = window.innerHeight;
            const steps = Math.ceil(scrollHeight / viewportHeight);

            for (let i = 0; i < steps; i++) {{
                window.scrollTo(0, viewportHeight * i);
                await delay({int(step_delay * 1000)});
            }}
            window.scrollTo(0, 0);
        }}
    """)
    await asyncio.sleep(settle_delay)


async def _extract_field(page, selector: str | None, fallback_method=None) -> str:
    """提取页面字段."""
    if not selector:
        return fallback_method() if fallback_method else ""
    try:
        elem = await page.query_selector(selector)
        if elem:
            text = await elem.inner_text()
            return text.strip() if text else ""
    except Exception as e:
        logger.debug(f"提取字段失败 (selector: {selector}): {e}")
    return fallback_method() if fallback_method else ""


async def _extract_reddit_article(page) -> ArticleData | None:
    """提取 Reddit 帖子：shreddit web components 结构化取值，避免 main 内脚本噪声."""
    data = await page.evaluate(
        """() => {
            const post = document.querySelector("shreddit-post");
            if (!post) return null;
            const titleEl = post.querySelector("[slot='title']");
            const authorAttr = post.getAttribute("author") || "";
            const dateEl = post.querySelector("time");
            const bodyEl = post.querySelector("[slot='text-body'] .md")
                || post.querySelector("[slot='text-body']")
                || post.querySelector(".md");
            const comments = Array.from(document.querySelectorAll("shreddit-comment"))
                .filter(c => !c.parentElement.closest("shreddit-comment"))
                .map(c => {
                    const body = c.querySelector("[slot='comment']");
                    return { author: "u/" + (c.getAttribute("author") || "?"), text: body ? body.innerText : "" };
                });
            return {
                title: titleEl ? titleEl.innerText : "",
                author: authorAttr ? "u/" + authorAttr : "",
                date: dateEl ? dateEl.innerText : "",
                bodyHtml: bodyEl ? bodyEl.innerHTML : "",
                comments,
                url: location.href.split("?")[0],
            };
        }"""
    )
    if not data:
        raise ExtractError("未找到 shreddit-post（页面可能被登录墙拦截或结构变更）")
    comments_html = build_author_text_html(data.get("comments") or [])
    body_html = data.get("bodyHtml") or ""
    content = body_html + (f"\n<hr>\n{comments_html}" if comments_html else "")
    return ArticleData(
        title=(data.get("title") or "").strip(),
        author=data.get("author") or "",
        date=data.get("date") or "",
        url=data.get("url") or page.url,
        content=content,
    )


async def extract_article(page, platform: Platform, scroll_step_delay: float = DEFAULT_SCROLL_STEP_DELAY, scroll_settle_delay: float = DEFAULT_SCROLL_SETTLE_DELAY) -> ArticleData | None:
    """提取文章内容."""
    try:
        if platform == Platform.XTWITTER:
            return await _extract_x_article(
                page,
                scroll_step_delay=scroll_step_delay,
                scroll_settle_delay=scroll_settle_delay,
            )
        if platform == Platform.REDDIT:
            await page.wait_for_selector("shreddit-post", timeout=20000)
            article = await _extract_reddit_article(page)
            return article
        config = get_platform_config(platform)
        wait_selector = config.get("wait_selector")
        if wait_selector:
            await page.wait_for_selector(wait_selector)
        await _scroll_page(page, step_delay=scroll_step_delay, settle_delay=scroll_settle_delay)
        title = await _extract_field(page, config.get("title_selector"))
        if not title:
            title = await page.title()
        author = await _extract_field(page, config.get("author_selector"))
        date = await _extract_field(page, config.get("date_selector"))
        content = ""
        content_elem = None
        article_selector = config.get("article_selector")
        if article_selector:
            content_elem = await page.query_selector(article_selector)
            if content_elem:
                content = await content_elem.inner_html()
        images = []
        # 图片收集：按配置的每个子选择器查询其内 img，避免只取第一个匹配元素时漏图
        try:
            img_selectors = []
            if article_selector:
                for sel in article_selector.split(","):
                    img_selectors.append(f"{sel.strip()} img")
            else:
                img_selectors = ["img"]
            for img_sel in img_selectors:
                try:
                    img_elements = await page.query_selector_all(img_sel)
                    for img in img_elements:
                        try:
                            src = await img.get_attribute("data-src") or await img.get_attribute("src")
                            if src and not src.startswith("data:"):
                                src = clean_image_url(src, platform=platform)
                                if src and src not in images:
                                    images.append(src)
                        except Exception as e:
                            logger.debug(f"提取图片失败: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"查询图片元素失败: {e}")
                    continue
        except Exception as e:
            logger.debug(f"查询图片元素失败: {e}")
        return ArticleData(
            title=title.strip(),
            author=author.strip(),
            date=date.strip(),
            url=page.url,
            content=content,
            images=images,
        )
    except ExtractError:
        raise
    except Exception as e:
        logger.error(f"提取文章失败: {e}")
        return None


async def _extract_links_from_elements(page, selector: str, links: set) -> None:
    elements = await page.query_selector_all(selector)
    for elem in elements:
        try:
            href = await elem.get_attribute("href")
            if href:
                full_url = urljoin(page.url, href)
                links.add(full_url)
        except Exception as e:
            logger.debug(f"提取链接失败: {e}")


async def extract_list_links(page, platform: Platform, scroll: bool = True, max_scroll_no_change: int = DEFAULT_MAX_SCROLL_NO_CHANGE) -> list[str]:
    """提取列表页的文章链接."""
    try:
        config = get_platform_config(platform)
        link_selector = config.get("list_link_selector", "a")
        links: set[str] = set()
        # 知乎问题页：优先从 js-initialData 提取已加载回答的链接（DOM 链接不可靠）
        if platform == Platform.ZHIHU:
            question_match = ZHIHU_QUESTION_RE.search(page.url)
            if question_match:
                initial_links = await _extract_zhihu_answer_links(page, question_match.group("qid"))
                links.update(initial_links)
        if scroll and config.get("needs_scroll", False):
            prev_count = 0
            no_change_count = 0
            while no_change_count < max_scroll_no_change:
                scroll_distance = random.randint(300, 800)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await _extract_links_from_elements(page, link_selector, links)
                if len(links) == prev_count:
                    no_change_count += 1
                else:
                    no_change_count = 0
                prev_count = len(links)
        else:
            await _extract_links_from_elements(page, link_selector, links)
        article_links = [link for link in links if is_article_page(link, platform)]
        return list(article_links)
    except Exception as e:
        logger.error(f"提取列表链接失败: {e}")
        raise ExtractError(f"提取列表链接失败: {e}") from e


def extract_answer_ids_from_initial_data(script_text: str) -> list[str]:
    """从知乎 js-initialData 中提取已加载回答的 ID 列表.

    结构: JSON → initialState.entities.answers → {answer_id: ...}
    返回按原始顺序的回答 ID；解析失败或结构缺失时返回空列表。
    """
    if not script_text:
        return []
    try:
        data = json.loads(script_text)
    except (ValueError, TypeError):
        logger.warning("js-initialData 解析失败，回退到 DOM 链接提取")
        return []
    answers = ((data or {}).get("initialState") or {}).get("entities", {}).get("answers") or {}
    return [str(aid) for aid in answers if str(aid).isdigit()]


async def _extract_zhihu_answer_links(page, question_id: str) -> list[str]:
    try:
        script_text = await page.evaluate(
            f"""() => {{
                const s = document.querySelector('{ZHIHU_INITIAL_DATA_SELECTOR}');
                return s ? s.textContent : '';
            }}"""
        )
    except Exception as e:
        logger.debug(f"读取 js-initialData 失败: {e}")
        return []
    ids = extract_answer_ids_from_initial_data(script_text)
    return [f"https://www.zhihu.com/question/{question_id}/answer/{aid}" for aid in ids]


def convert_img_tag(img_tag: str, platform: Platform | None = None, image_width: int = DEFAULT_IMAGE_WIDTH, image_map: dict[str, str] | None = None) -> str:
    """将 img 标签转换为 Markdown 格式.

    image_map: 已下载图片的 {清理后URL: 本地相对路径} 映射。命中时输出本地路径，
    否则输出远程 URL。键使用与下载时一致的 clean_image_url 结果，因此不受
    content 中 &amp; 转义或查询参数去除的影响。

    选择图片地址的优先级：先取 ``src``；若其为 ``data:`` 占位图（如知乎懒加载
    的 ``data:image/svg+xml`` 占位），则回退到 ``data-actualsrc`` / ``data-src``
    取真实地址。仍然拿到 ``data:`` 占位图时直接返回空串，避免把占位 SVG 渲染成
    图片、也避免后续行残留 ``{width=...}`` 等属性碎片。
    """
    alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
    alt = alt_match.group(1) if alt_match else "image"
    src = None
    src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
    if src_match:
        src = src_match.group(1)
    if src and src.startswith("data:"):
        for attr in ("data-actualsrc", "data-src"):
            m = re.search(rf'{attr}=["\']([^"\']+)["\']', img_tag)
            if m and not m.group(1).startswith("data:"):
                src = m.group(1)
                break
    if not src or src.startswith("data:"):
        return ""
    src = clean_image_url(src, platform=platform)
    local_path = (image_map or {}).get(src)
    if local_path:
        src = local_path
    return f'\n![{alt}]({src}){{width="{image_width}"}}\n'


_HTML_TO_MD_STEPS: list[tuple[str, str | re.Pattern, str]] = [
    ("br", r"<br\s*/?>", "\n"),
    ("p_open", r"<p[^>]*>", ""),
    ("p_close", r"</p>", "\n\n"),
    ("section_open", r"<section[^>]*>", ""),
    ("section_close", r"</section>", "\n"),
    ("strong", r"<strong[^>]*>((?:(?!<img).)*?)</strong>", r"**\1**"),
    ("b", r"<b[^>]*>((?:(?!<img).)*?)</b>", r"**\1**"),
    ("em", r"<em[^>]*>(.*?)</em>", r"*\1*"),
    ("i", r"<i[^>]*>(.*?)</i>", r"*\1*"),
    ("h6", r"<h6[^>]*>(.*?)</h6>", r"###### \1\n\n"),
    ("h5", r"<h5[^>]*>(.*?)</h5>", r"##### \1\n\n"),
    ("h4", r"<h4[^>]*>(.*?)</h4>", r"#### \1\n\n"),
    ("h3", r"<h3[^>]*>(.*?)</h3>", r"### \1\n\n"),
    ("h2", r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n"),
    ("h1", r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n"),
    ("ul_open", r"<ul[^>]*>", "\n"),
    ("ul_close", r"</ul>", "\n"),
    ("ol_open", r"<ol[^>]*>", "\n"),
    ("ol_close", r"</ol>", "\n"),
    ("li", r"<li[^>]*>", "- "),
    ("li_close", r"</li>", "\n"),
    ("nbsp", r"&nbsp;", " "),
    ("amp", r"&amp;", "&"),
    ("lt", r"&lt;", "<"),
    ("gt", r"&gt;", ">"),
    ("quot", r"&quot;", '"'),
    ("apos", r"&apos;", "'"),
    ("ndash", r"&ndash;", "-"),
    ("mdash", r"&mdash;", "--"),
]


def _dedupe_image_lines(content: str) -> str:
    """去除重复的图片行。

    同一张图常被渲染成多个 <img>（如知乎的 <noscript> 兜底图与懒加载占位图的
    data-actualsrc 指向同一地址），转换后会产生重复的
    ``![...](url){width=...}`` 行。按清理后的 URL 去重，保留首次出现。
    """
    seen: set[str] = set()
    out: list[str] = []
    img_re = re.compile(r'^!\[[^\]]*\]\((\S+?)\)\{width="\d+"\}\s*$')
    for line in content.split("\n"):
        m = img_re.match(line)
        if m:
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
        out.append(line)
    return "\n".join(out)


def _extract_code_lang(tag: str) -> str:
    m = re.search(r'class=["\'](?:language-|lang-)(\w+)["\']', tag)
    return m.group(1) if m else ""


def _convert_html_to_markdown(content: str, platform: Platform | None = None, image_width: int = DEFAULT_IMAGE_WIDTH, image_map: dict[str, str] | None = None) -> str:
    content = remove_noise_elements(content, platform=platform)

    pre_placeholders: list[str] = []

    def _convert_pre_to_fence(match: re.Match) -> str:
        open_tag = match.group(1)
        inner = match.group(2)
        lang = _extract_code_lang(open_tag)
        code_m = re.search(r"<code([^>]*)>", inner)
        if code_m and not lang:
            lang = _extract_code_lang(code_m.group(1))
        inner = re.sub(r"<code[^>]*>", "", inner)
        inner = re.sub(r"</code>", "", inner)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<[^>]+>", "", inner)
        inner = html.unescape(inner)
        inner = inner.replace("\xa0", " ")
        idx = len(pre_placeholders)
        pre_placeholders.append(f"\n```{lang}\n{inner.strip()}\n```\n")
        return f"\x00PRE{idx}\x00"

    content = re.sub(
        r"<pre([^>]*)>(.*?)</pre>",
        _convert_pre_to_fence,
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<code([^>]*)>(.*?)</code>",
        lambda m: f"`{re.sub(r'<[^>]+>', '', m.group(2))}`",
        content,
    )
    for _name, pattern, replacement in _HTML_TO_MD_STEPS:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    content = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'<img\b(?:[^>"]|"[^"]*")*>',
        lambda m: convert_img_tag(m.group(0), platform=platform, image_width=image_width, image_map=image_map),
        content,
        flags=re.DOTALL,
    )
    content = re.sub(r"!\[.*?\]\(data:image[^)]+\)", "", content)
    content = re.sub(r"<[^>]+>", "", content)
    content = _dedupe_image_lines(content)
    for i, block in enumerate(pre_placeholders):
        content = content.replace(f"\x00PRE{i}\x00", block)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def truncate_tail_noise(content: str, markers: list[str], scan_lines: int = DEFAULT_TAIL_SCAN_LINES) -> str:
    """截断 Markdown 文末噪音区域.

    只在最后 scan_lines 行内扫描噪音标记词，从首个匹配行截断。
    若正文中间出现同义词则不受影响。
    """
    if not markers or not content:
        return content
    lines = content.split("\n")
    tail_start = max(0, len(lines) - scan_lines)
    for i in range(tail_start, len(lines)):
        line_stripped = lines[i].strip()
        for marker in markers:
            if marker in line_stripped:
                cut = i
                while cut > 0 and not lines[cut - 1].strip():
                    cut -= 1
                result = "\n".join(lines[:cut]).rstrip()
                return result
    return content


_DEFAULT_LABELS = {
    "author": "作者：",
    "date": "发布时间：",
    "source": "来源：",
}


def convert_to_markdown(article: ArticleData, platform: Platform | None = None, labels: dict[str, str] | None = None, image_width: int = DEFAULT_IMAGE_WIDTH, image_map: dict[str, str] | None = None) -> str:
    """将文章转换为 Markdown 格式.

    image_map: 已下载图片的 {清理后URL: 本地相对路径} 映射（见 convert_img_tag）。
    """
    if labels is None:
        labels = _DEFAULT_LABELS
    lines = []
    lines.append(f"# {article.title}")
    lines.append("")
    if article.author:
        lines.append(f"**{labels.get('author', _DEFAULT_LABELS['author'])}** {article.author}")
    if article.date:
        lines.append(f"**{labels.get('date', _DEFAULT_LABELS['date'])}** {article.date}")
    lines.append(f"**{labels.get('source', _DEFAULT_LABELS['source'])}** {article.url}")
    lines.append("")
    lines.append("---")
    lines.append("")
    content = _convert_html_to_markdown(article.content, platform=platform, image_width=image_width, image_map=image_map)
    if platform is not None:
        config = get_platform_config(platform)
        markers = config.get("tail_noise_markers", [])
        if markers:
            content = truncate_tail_noise(content, markers)
    lines.append(content)
    return "\n".join(lines)
