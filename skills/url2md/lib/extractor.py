"""内容提取器：文章提取、列表提取、Markdown 转换."""

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from .selectors import Platform, get_platform_config, is_article_page

logger = logging.getLogger(__name__)

MAX_SCROLL_NO_CHANGE = 3


class ExtractError(Exception):
    """提取操作异常."""

    pass


def clean_image_url(url: str) -> str:
    """清理图片 URL，移除不必要的参数."""
    if not url:
        return url
    url = url.replace("&amp;", "&")
    try:
        parsed = urlparse(url)
        keep_params = []
        if parsed.query:
            params = parse_qs(parsed.query)
            for key in ["wx_fmt", "tp"]:
                if key in params:
                    keep_params.append((key, params[key][0]))
        new_query = urlencode(keep_params) if keep_params else ""
        clean_url = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, "")
        )
        return clean_url
    except (ValueError, TypeError):
        return url.split("?")[0].split("#")[0]


def remove_noise_elements(content: str) -> str:
    """移除内容中的噪音元素（广告、推荐等）."""
    noise_patterns = [
        (r'<div[^>]*class="[^"]*qr-code[^"]*"[^>]*>.*?</div>', ""),
        (r'<div[^>]*class="[^"]*recommend[^"]*"[^>]*>.*?</div>', ""),
        (r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>', ""),
        (r'<div[^>]*id="[^"]*ad[^"]*"[^>]*>.*?</div>', ""),
        (r'<section[^>]*class="[^"]*mp_profile_popup[^"]*"[^>]*>.*?</section>', ""),
        (r'<section[^>]*class="[^"]*js_ad[^"]*"[^>]*>.*?</section>', ""),
        (r'<a[^>]*class="[^"]*appmsg_card[^"]*"[^>]*>.*?</a>', ""),
    ]
    for pattern, replacement in noise_patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.IGNORECASE)
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


async def _scroll_page(page) -> None:
    """滚动页面以加载所有内容."""
    await page.evaluate("""
        async () => {
            const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
            const scrollHeight = document.documentElement.scrollHeight;
            const viewportHeight = window.innerHeight;
            const steps = Math.ceil(scrollHeight / viewportHeight);

            for (let i = 0; i < steps; i++) {
                window.scrollTo(0, viewportHeight * i);
                await delay(300);
            }
            window.scrollTo(0, 0);
        }
    """)
    await asyncio.sleep(0.5)


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


async def extract_article(page, platform: Platform) -> ArticleData | None:
    """提取文章内容."""
    try:
        config = get_platform_config(platform)
        await _scroll_page(page)
        title = await _extract_field(page, config.get("title_selector"))
        if not title:
            title = await page.title()
        author = await _extract_field(page, config.get("author_selector"))
        date = await _extract_field(page, config.get("date_selector"))
        content = ""
        article_selector = config.get("article_selector")
        if article_selector:
            content_elem = await page.query_selector(article_selector)
            if content_elem:
                content = await content_elem.inner_html()
        images = []
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
                            src = clean_image_url(src)
                            if src and src not in images:
                                images.append(src)
                    except Exception as e:
                        logger.debug(f"提取图片失败: {e}")
                        continue
            except Exception as e:
                logger.debug(f"查询图片元素失败: {e}")
                continue
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


async def extract_list_links(page, platform: Platform, scroll: bool = True) -> list[str]:
    """提取列表页的文章链接."""
    try:
        config = get_platform_config(platform)
        link_selector = config.get("list_link_selector", "a")
        links: set[str] = set()
        if scroll and config.get("needs_scroll", False):
            prev_count = 0
            no_change_count = 0
            while no_change_count < MAX_SCROLL_NO_CHANGE:
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
        return list(set(article_links))
    except Exception as e:
        logger.error(f"提取列表链接失败: {e}")
        raise ExtractError(f"提取列表链接失败: {e}") from e


def convert_img_tag(img_tag: str) -> str:
    """将 img 标签转换为 Markdown 格式."""
    src_match = re.search(r'(?:data-)?src=["\']([^"\']+)["\']', img_tag)
    alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
    if not src_match:
        return ""
    src = src_match.group(1)
    alt = alt_match.group(1) if alt_match else "image"
    src = clean_image_url(src)
    return f'\n![{alt}]({src}){{width="600"}}\n'


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


def _convert_html_to_markdown(content: str) -> str:
    content = remove_noise_elements(content)
    for _name, pattern, replacement in _HTML_TO_MD_STEPS:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    content = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(r"<img[^>]*>", lambda m: convert_img_tag(m.group(0)), content)
    content = re.sub(r"!\[.*?\]\(data:image[^)]+\)", "", content)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def convert_to_markdown(article: ArticleData, image_dir: str | None = None) -> str:
    """将文章转换为 Markdown 格式."""
    lines = []
    lines.append(f"# {article.title}")
    lines.append("")
    if article.author:
        lines.append(f"**作者：** {article.author}")
    if article.date:
        lines.append(f"**发布时间：** {article.date}")
    lines.append(f"**来源：** {article.url}")
    lines.append("")
    lines.append("---")
    lines.append("")
    content = _convert_html_to_markdown(article.content)
    lines.append(content)
    return "\n".join(lines)
