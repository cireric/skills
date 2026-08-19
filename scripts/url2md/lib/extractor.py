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


async def extract_article(page, platform: Platform, scroll_step_delay: float = DEFAULT_SCROLL_STEP_DELAY, scroll_settle_delay: float = DEFAULT_SCROLL_SETTLE_DELAY) -> ArticleData | None:
    """提取文章内容."""
    try:
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


def convert_img_tag(img_tag: str, platform: Platform | None = None, image_width: int = DEFAULT_IMAGE_WIDTH) -> str:
    """将 img 标签转换为 Markdown 格式."""
    src_match = re.search(r'(?:data-)?src=["\']([^"\']+)["\']', img_tag)
    alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
    if not src_match:
        return ""
    src = src_match.group(1)
    alt = alt_match.group(1) if alt_match else "image"
    src = clean_image_url(src, platform=platform)
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


def _extract_code_lang(tag: str) -> str:
    m = re.search(r'class=["\'](?:language-|lang-)(\w+)["\']', tag)
    return m.group(1) if m else ""


def _convert_html_to_markdown(content: str, platform: Platform | None = None, image_width: int = DEFAULT_IMAGE_WIDTH) -> str:
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
    content = re.sub(r"<img[^>]*>", lambda m: convert_img_tag(m.group(0), platform=platform, image_width=image_width), content)
    content = re.sub(r"!\[.*?\]\(data:image[^)]+\)", "", content)
    content = re.sub(r"<[^>]+>", "", content)
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


def convert_to_markdown(article: ArticleData, platform: Platform | None = None, labels: dict[str, str] | None = None, image_width: int = DEFAULT_IMAGE_WIDTH) -> str:
    """将文章转换为 Markdown 格式."""
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
    content = _convert_html_to_markdown(article.content, platform=platform, image_width=image_width)
    if platform is not None:
        config = get_platform_config(platform)
        markers = config.get("tail_noise_markers", [])
        if markers:
            content = truncate_tail_noise(content, markers)
    lines.append(content)
    return "\n".join(lines)
