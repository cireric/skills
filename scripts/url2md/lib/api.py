"""同步 API 适配层 — skill 入口."""

import asyncio
import logging
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from .browser import BrowserManager
from .downloader import download_images
from .extractor import convert_to_markdown, extract_article, extract_list_links
from .selectors import detect_platform, get_platform_config, is_article_page, is_list_page
from .utils import configure_asyncio, sanitize_filename

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """抓取结果."""

    success: bool
    files: list[str] = field(default_factory=list)
    error: str | None = None
    article_count: int = 0


def _run_async(coro):
    """运行异步协程."""
    configure_asyncio()
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return CrawlResult(success=False, error="用户中断操作")
    except Exception as e:
        logger.error(f"异步操作失败: {e}")
        return CrawlResult(success=False, error=str(e))


async def crawl_single_article(
    url: str,
    output_dir: str,
    browser_manager: BrowserManager | None = None,
    download_imgs: bool = False,
    images_dir: str | None = None,
    filename: str | None = None,
    headless: bool = True,
    max_concurrent: int = 3,
    max_retries: int = 3,
    cookies_file: str | None = None,
    user_agent: str | None = None,
    browser_channel: str = "chrome",
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    labels: dict[str, str] | None = None,
    scroll_step_delay: float = 0.3,
    scroll_settle_delay: float = 0.5,
    max_scroll_no_change: int = 3,
    image_width: int = 600,
    image_download_timeout: int = 30,
    delay_jitter: float = 3.0,
    backoff_base: float = 1.0,
    backoff_max_wait: float = 60.0,
) -> tuple[bool, str | None, str | None]:
    """抓取单篇文章."""
    platform = detect_platform(url)
    should_close = False
    if browser_manager is None:
        browser_manager = BrowserManager(
            headless=headless,
            user_agent=user_agent,
            browser_channel=browser_channel,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            locale=locale,
            timezone=timezone,
        )
        await browser_manager.create_context(cookies_file=cookies_file)
        should_close = True
    page = await browser_manager.new_page()
    try:
        config = get_platform_config(platform)
        wait_until = config.get("wait_until", "networkidle")
        await page.goto(url, wait_until=wait_until)
        article = await extract_article(page, platform, scroll_step_delay=scroll_step_delay, scroll_settle_delay=scroll_settle_delay)
        if article is None:
            return False, None, "提取文章失败"
        if download_imgs and article.images:
            img_dir = images_dir or os.path.join(output_dir, "images")
            local_paths = await download_images(
                article.images, img_dir, article.title,
                referer=url, max_concurrent=max_concurrent, max_retries=max_retries,
                timeout=image_download_timeout,
            )
            for orig_url, local_path in local_paths.items():
                rel_path = os.path.relpath(local_path, output_dir).replace(os.sep, "/")
                article.content = re.sub(
                    re.escape(orig_url) + r"(?![\w\-])", rel_path, article.content
                )
        markdown = convert_to_markdown(article, platform=platform, labels=labels, image_width=image_width)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        md_filename = filename or f"{sanitize_filename(article.title)}.md"
        md_path = os.path.join(output_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return True, md_path, None
    except Exception as e:
        logger.error(f"抓取文章失败 {url}: {e}")
        return False, None, str(e)
    finally:
        await page.close()
        if should_close:
            await browser_manager.close()


async def _crawl_list_page(
    url: str,
    output_dir: str,
    browser_manager: BrowserManager | None = None,
    download_imgs: bool = False,
    images_dir: str | None = None,
    limit: int | None = None,
    delay: float = 2.0,
    headless: bool = True,
    max_concurrent: int = 3,
    max_retries: int = 3,
    cookies_file: str | None = None,
    user_agent: str | None = None,
    browser_channel: str = "chrome",
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    labels: dict[str, str] | None = None,
    scroll_step_delay: float = 0.3,
    scroll_settle_delay: float = 0.5,
    max_scroll_no_change: int = 3,
    image_width: int = 600,
    image_download_timeout: int = 30,
    delay_jitter: float = 3.0,
    backoff_base: float = 1.0,
    backoff_max_wait: float = 60.0,
) -> CrawlResult:
    """抓取列表页."""
    platform = detect_platform(url)
    should_close = False
    if browser_manager is None:
        browser_manager = BrowserManager(
            headless=headless,
            user_agent=user_agent,
            browser_channel=browser_channel,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            locale=locale,
            timezone=timezone,
        )
        await browser_manager.create_context(cookies_file=cookies_file)
        should_close = True
    files = []
    errors = []
    try:
        page = await browser_manager.new_page()
        config = get_platform_config(platform)
        wait_until = config.get("wait_until", "networkidle")
        await page.goto(url, wait_until=wait_until)
        links = await extract_list_links(page, platform, max_scroll_no_change=max_scroll_no_change)
        if limit:
            links = links[:limit]
        await page.close()
        for i, link in enumerate(links, 1):
            if i > 1:
                await asyncio.sleep(random.uniform(max(0.5, delay), delay + delay_jitter))
            success, file_path, error = await crawl_single_article(
                link,
                output_dir,
                browser_manager=browser_manager,
                download_imgs=download_imgs,
                images_dir=images_dir,
                max_concurrent=max_concurrent,
                max_retries=max_retries,
                labels=labels,
                scroll_step_delay=scroll_step_delay,
                scroll_settle_delay=scroll_settle_delay,
                image_width=image_width,
                image_download_timeout=image_download_timeout,
                delay_jitter=delay_jitter,
                backoff_base=backoff_base,
                backoff_max_wait=backoff_max_wait,
            )
            if success and file_path:
                files.append(file_path)
            elif error:
                errors.append(f"{link}: {error}")
        return CrawlResult(
            success=len(files) > 0,
            files=files,
            error="\n".join(errors) if errors else None,
            article_count=len(files),
        )
    finally:
        if should_close:
            await browser_manager.close()


async def _crawl_article(
    url: str, output_dir: str, download_imgs: bool, filename: str | None = None,
    headless: bool = True, max_concurrent: int = 3, max_retries: int = 3,
    cookies_file: str | None = None,
    user_agent: str | None = None,
    browser_channel: str = "chrome",
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    labels: dict[str, str] | None = None,
    scroll_step_delay: float = 0.3,
    scroll_settle_delay: float = 0.5,
    max_scroll_no_change: int = 3,
    image_width: int = 600,
    image_download_timeout: int = 30,
    delay_jitter: float = 3.0,
    backoff_base: float = 1.0,
    backoff_max_wait: float = 60.0,
) -> CrawlResult:
    """抓取单篇文章的通用逻辑."""
    success, file_path, error = await crawl_single_article(
        url, output_dir, download_imgs=download_imgs, filename=filename,
        headless=headless, max_concurrent=max_concurrent, max_retries=max_retries,
        cookies_file=cookies_file,
        user_agent=user_agent,
        browser_channel=browser_channel,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        locale=locale,
        timezone=timezone,
        labels=labels,
        scroll_step_delay=scroll_step_delay,
        scroll_settle_delay=scroll_settle_delay,
        image_width=image_width,
        image_download_timeout=image_download_timeout,
        delay_jitter=delay_jitter,
        backoff_base=backoff_base,
        backoff_max_wait=backoff_max_wait,
    )
    return CrawlResult(
        success=success,
        files=[file_path] if file_path else [],
        error=error,
        article_count=1 if success else 0,
    )


def crawl_url(
    url: str,
    output_dir: str | None = None,
    download_images: bool = False,
    limit: int | None = None,
    delay: float = 2.0,
    filename: str | None = None,
    images_dir: str | None = None,
    headless: bool = True,
    max_concurrent: int = 3,
    max_retries: int = 3,
    cookies_file: str | None = None,
    user_agent: str | None = None,
    browser_channel: str = "chrome",
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    locale: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    labels: dict[str, str] | None = None,
    scroll_step_delay: float = 0.3,
    scroll_settle_delay: float = 0.5,
    max_scroll_no_change: int = 3,
    image_width: int = 600,
    image_download_timeout: int = 30,
    delay_jitter: float = 3.0,
    backoff_base: float = 1.0,
    backoff_max_wait: float = 60.0,
) -> CrawlResult:
    """抓取 URL（单篇文章或列表页）."""
    if output_dir is None:
        raise ValueError("output_dir is required (set in config.yaml or pass --output)")
    platform = detect_platform(url)
    browser_kwargs = dict(
        headless=headless, user_agent=user_agent, browser_channel=browser_channel,
        viewport_width=viewport_width, viewport_height=viewport_height,
        locale=locale, timezone=timezone,
    )
    extra_kwargs = dict(
        labels=labels,
        scroll_step_delay=scroll_step_delay,
        scroll_settle_delay=scroll_settle_delay,
        max_scroll_no_change=max_scroll_no_change,
        image_width=image_width,
        image_download_timeout=image_download_timeout,
        delay_jitter=delay_jitter,
        backoff_base=backoff_base,
        backoff_max_wait=backoff_max_wait,
    )
    if is_article_page(url, platform):
        return _run_async(_crawl_article(
            url, output_dir, download_images, filename=filename,
            max_concurrent=max_concurrent, max_retries=max_retries,
            cookies_file=cookies_file, **browser_kwargs, **extra_kwargs,
        ))
    elif is_list_page(url, platform):
        return _run_async(
            _crawl_list_page(
                url, output_dir,
                download_images=download_images, images_dir=images_dir,
                limit=limit, delay=delay,
                max_concurrent=max_concurrent, max_retries=max_retries,
                cookies_file=cookies_file, **browser_kwargs, **extra_kwargs,
            )
        )
    else:
        logger.warning(f"URL 类型无法识别，尝试按文章页处理: {url}")
        return _run_async(_crawl_article(
            url, output_dir, download_images, filename=filename,
            max_concurrent=max_concurrent, max_retries=max_retries,
            cookies_file=cookies_file, **browser_kwargs, **extra_kwargs,
        ))
