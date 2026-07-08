"""各平台 CSS 选择器配置."""

import logging
import re
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Platform(Enum):
    """支持的平台."""

    WECHAT = "wechat"
    ZHIHU = "zhihu"
    JIANSHU = "jianshu"
    BILIBILI = "bilibili"
    GENERIC = "generic"


_DEFAULT_PLATFORM_CONFIGS: dict[Platform, dict[str, Any]] = {
    Platform.WECHAT: {
        "name": "微信公众号",
        "article_patterns": [r"mp\.weixin\.qq\.com/s/"],
        "list_patterns": [r"mp\.weixin\.qq\.com/mp/profile_ext"],
        "article_selector": "#js_content",
        "title_selector": "#activity-name",
        "author_selector": "#js_name",
        "date_selector": "#publish_time",
        "list_link_selector": "a[href*='/s/']",
        "needs_scroll": True,
        "wait_selector": "#js_content",
    },
    Platform.ZHIHU: {
        "name": "知乎专栏",
        "article_patterns": [r"zhuanlan\.zhihu\.com/p/"],
        "list_patterns": [r"zhuanlan\.zhihu\.com/p/\?page=", r"zhihu\.com/people/.*/posts"],
        "article_selector": ".Post-RichText, .RichText, .RichContent-inner",
        "title_selector": ".Post-Title, .ContentItem-title, h1.Post-Title",
        "author_selector": ".AuthorInfo-name, .UserLink-author",
        "date_selector": ".ContentItem-time, .Post-Time",
        "list_link_selector": "a[href*='/p/']",
        "needs_scroll": False,
        "wait_selector": ".Post-RichText, .RichText",
    },
    Platform.JIANSHU: {
        "name": "简书",
        "article_patterns": [r"jianshu\.com/p/"],
        "list_patterns": [r"jianshu\.com/u/"],
        "article_selector": "article, .article, ._2gDJMmCVA5UvC-cfDwZzJw",
        "title_selector": "h1, .title, ._2zeTMsM5q05HTvYg3D5KVC",
        "author_selector": ".author .name, .nickname, ._23I9m-aPK-9hXkE8bPTh7V",
        "date_selector": ".publish-time, .time, [data-testid='public-time']",
        "list_link_selector": "a[href*='/p/']",
        "needs_scroll": True,
        "wait_selector": "article, .article",
    },
    Platform.BILIBILI: {
        "name": "Bilibili专栏",
        "article_patterns": [r"bilibili\.com/read/cv"],
        "list_patterns": [r"space\.bilibili\.com/.*/article"],
        "article_selector": ".article-content, .read-article-box, #read-article-holder",
        "title_selector": "h1.title, .article-title, h1",
        "author_selector": ".author-name, .up-name, .name",
        "date_selector": ".publish-time, .time, .pubdate",
        "list_link_selector": "a[href*='/read/cv']",
        "needs_scroll": True,
        "wait_selector": ".article-content",
    },
    Platform.GENERIC: {
        "name": "通用网页",
        "article_patterns": [],
        "list_patterns": [],
        "article_selector": "article, main, .content, .post, .entry",
        "title_selector": "h1, .title, .post-title",
        "author_selector": ".author, .byline",
        "date_selector": ".date, .time, .published",
        "list_link_selector": "a",
        "needs_scroll": False,
    },
}


def get_platform_configs() -> dict[Platform, dict[str, Any]]:
    """获取所有平台配置（内置，无 YAML 依赖）."""
    return _DEFAULT_PLATFORM_CONFIGS.copy()


def detect_platform(url: str) -> Platform:
    """根据 URL 检测平台."""
    configs = get_platform_configs()
    for platform, config in configs.items():
        if platform == Platform.GENERIC:
            continue
        patterns = config.get("article_patterns", []) + config.get("list_patterns", [])
        for pattern in patterns:
            if re.search(pattern, url):
                return platform
    return Platform.GENERIC


def get_platform_config(platform: Platform) -> dict[str, Any]:
    """获取平台配置."""
    configs = get_platform_configs()
    return configs.get(platform, configs[Platform.GENERIC])


def is_article_page(url: str, platform: Platform | None = None) -> bool:
    """判断是否为文章页."""
    if platform is None:
        platform = detect_platform(url)
    config = get_platform_config(platform)
    patterns = config.get("article_patterns", [])
    return any(re.search(pattern, url) for pattern in patterns)


def is_list_page(url: str, platform: Platform | None = None) -> bool:
    """判断是否为列表页."""
    if platform is None:
        platform = detect_platform(url)
    config = get_platform_config(platform)
    patterns = config.get("list_patterns", [])
    return any(re.search(pattern, url) for pattern in patterns)
