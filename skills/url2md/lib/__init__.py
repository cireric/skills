"""url2md skill — self-contained crawl library."""

from .api import CrawlResult, crawl_url
from .browser import BrowserManager
from .downloader import download_images, download_single_image
from .extractor import (
    ArticleData,
    ExtractError,
    convert_to_markdown,
    extract_article,
    extract_list_links,
)
from .selectors import (
    Platform,
    detect_platform,
    get_platform_config,
    is_article_page,
    is_list_page,
)
from .utils import (
    configure_asyncio,
    exponential_backoff,
    load_state,
    sanitize_filename,
    save_state,
)

__all__ = [
    "crawl_url",
    "CrawlResult",
    "BrowserManager",
    "Platform",
    "detect_platform",
    "get_platform_config",
    "is_article_page",
    "is_list_page",
    "ArticleData",
    "ExtractError",
    "extract_article",
    "extract_list_links",
    "convert_to_markdown",
    "download_images",
    "download_single_image",
    "sanitize_filename",
    "load_state",
    "save_state",
    "exponential_backoff",
    "configure_asyncio",
]
