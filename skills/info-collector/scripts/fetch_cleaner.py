from __future__ import annotations
import re


_SKIP_CLEAN_TOOLS = frozenset({"exa_web_fetch_exa", "piped"})

_COOKIE_PATTERN = re.compile(
    r"(?mi).{0,40}(we use cookies|accept cookies|cookie preferences|gdpr|隐私政策|cookie 设置).{0,80}\n?"
)
_SOCIAL_PATTERN = re.compile(
    r"(?mi).{0,20}(share on (twitter|facebook|linkedin|reddit|微信|weibo)|分享到(微信|微博|豆瓣)|分享这篇文章).{0,60}\n?"
)
_BREADCRUMB_PATTERN = re.compile(
    r"^[\w\s\u4e00-\u9fff]+(>\s*[\w\s\u4e00-\u9fff]+){2,}\n",
    re.MULTILINE | re.IGNORECASE,
)
_COMMENT_HEADINGS = re.compile(
    r"^#{1,3}\s*(comments|评论区|leave a comment|reader comments|discussion)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RELATED_HEADINGS = re.compile(
    r"^#{1,3}\s*(related (articles|posts|reading)|推荐阅读|相关文章|you might also like)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_HTML_NAV = re.compile(r"<nav\b[^>]*>.*?</nav>", re.DOTALL | re.IGNORECASE)
_HTML_FOOTER = re.compile(r"<footer\b[^>]*>.*?</footer>", re.DOTALL | re.IGNORECASE)
_HTML_ASIDE = re.compile(r"<aside\b[^>]*>.*?</aside>", re.DOTALL | re.IGNORECASE)


def _strip_html_blocks(text: str) -> str:
    text = _HTML_NAV.sub("", text)
    text = _HTML_FOOTER.sub("", text)
    text = _HTML_ASIDE.sub("", text)
    return text


def _strip_section_by_heading(text: str, heading_pattern: re.Pattern[str]) -> str:
    lines = text.split("\n")
    result: list[str] = []
    skip = False
    for line in lines:
        if heading_pattern.match(line):
            skip = True
            continue
        if skip and re.match(r"^#{1,3}\s", line):
            skip = False
            result.append(line)
            continue
        if not skip:
            result.append(line)
    return "\n".join(result)


def clean(content: str, tool: str) -> str:
    if tool in _SKIP_CLEAN_TOOLS:
        return content
    content = _strip_html_blocks(content)
    content = _strip_section_by_heading(content, _COMMENT_HEADINGS)
    content = _strip_section_by_heading(content, _RELATED_HEADINGS)
    content = _COOKIE_PATTERN.sub("", content)
    content = _SOCIAL_PATTERN.sub("", content)
    content = _BREADCRUMB_PATTERN.sub("", content)
    return content.strip() + "\n" if content.strip() else ""
