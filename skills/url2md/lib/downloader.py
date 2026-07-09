"""图片下载器 - 支持重试机制、Content-Type 检测、图片去重."""

import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from .utils import exponential_backoff, sanitize_filename

logger = logging.getLogger(__name__)

HTTP_OK = 200
HTTP_SERVER_ERROR_MIN = 500
HTTP_SERVER_ERROR_MAX = 600

try:
    import aiofiles
    import aiohttp
except ImportError:
    aiohttp = None
    aiofiles = None

_IMAGE_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
}


def _get_ext_from_content_type(content_type: str | None) -> str | None:
    """从 Content-Type 响应头获取文件扩展名."""
    if not content_type:
        return None
    content_type = content_type.lower().split(";")[0].strip()
    return _IMAGE_CONTENT_TYPES.get(content_type)


_EXT_FROM_PATH = {
    ".png": "png",
    ".gif": "gif",
    ".webp": "webp",
    ".svg": "svg",
    ".bmp": "bmp",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".jpeg": "jpg",
    ".jpg": "jpg",
}


def _get_ext_from_url(path: str) -> str:
    _, ext = os.path.splitext(path.lower())
    return _EXT_FROM_PATH.get(ext, "jpg")


async def _process_image_response(
    response,
    url: str,
    save_path: str,
) -> bool:
    """处理 HTTP 响应并保存图片文件."""
    if response.status != HTTP_OK:
        if HTTP_SERVER_ERROR_MIN <= response.status < HTTP_SERVER_ERROR_MAX:
            raise RuntimeError(f"Server error {response.status}")
        logger.warning(f"下载图片失败 {url}: HTTP {response.status}")
        return False
    content = await response.read()
    content_type = response.headers.get("Content-Type")
    ext_from_ct = _get_ext_from_content_type(content_type)
    if ext_from_ct and not save_path.lower().endswith(f".{ext_from_ct}"):
        base_path = os.path.splitext(save_path)[0]
        save_path = f"{base_path}.{ext_from_ct}"
    if aiofiles:
        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)
    else:
        with open(save_path, "wb") as f:
            f.write(content)
    return True


async def download_single_image(
    url: str,
    save_path: str,
    timeout: int = 30,
    session: "aiohttp.ClientSession | None" = None,
    referer: str | None = None,
    max_retries: int = 3,
) -> bool:
    """下载单张图片（支持重试）."""
    if aiohttp is None:
        raise ImportError("aiohttp not installed. Run: venv-pip install aiohttp aiofiles")
    headers = {}
    if referer:
        headers["Referer"] = referer
    for attempt in range(max_retries + 1):
        try:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            if session:
                response = await session.get(
                    url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers
                )
                async with response:
                    return await _process_image_response(response, url, save_path)
            else:
                async with (
                    aiohttp.ClientSession() as sess,
                    sess.get(
                        url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers
                    ) as response,
                ):
                    return await _process_image_response(response, url, save_path)
        except Exception as e:
            if aiohttp and isinstance(e, aiohttp.ClientError):
                logger.warning(f"下载图片失败 {url} (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    wait_time = exponential_backoff(attempt)
                    logger.info(f"{wait_time:.1f} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"下载图片失败，已重试 {max_retries} 次: {url}")
                    return False
            else:
                logger.error(f"下载图片时发生未预期错误 {url}: {e}")
                return False
    return False


async def download_images(
    image_urls: list[str],
    output_dir: str,
    article_title: str = "",
    max_concurrent: int = 3,
    referer: str | None = None,
    max_retries: int = 3,
    timeout: int = 30,
) -> dict[str, str]:
    """批量下载图片（支持去重）."""
    if not image_urls:
        return {}
    if article_title:
        subdir = sanitize_filename(article_title)
        output_dir = os.path.join(output_dir, subdir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    seen_urls: set[str] = set()
    unique_urls = []
    for url in image_urls:
        normalized_url = url.split("?")[0].split("#")[0]
        if normalized_url not in seen_urls:
            seen_urls.add(normalized_url)
            unique_urls.append(url)
    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_semaphore(url: str, index: int, session):
        async with semaphore:
            parsed = urlparse(url)
            path = parsed.path.lower()
            ext = _get_ext_from_url(path)
            filename = f"img_{index:03d}.{ext}"
            save_path = os.path.join(output_dir, filename)
            success = await download_single_image(
                url, save_path, timeout=timeout, session=session, referer=referer, max_retries=max_retries
            )
            if success:
                return url, save_path
            return url, None

    if aiohttp is None:
        logger.error("aiohttp not installed, cannot download images")
        return {}
    async with aiohttp.ClientSession() as session:
        tasks = [download_with_semaphore(url, i + 1, session) for i, url in enumerate(unique_urls)]
        download_results = await asyncio.gather(*tasks)
    for url, local_path in download_results:
        if local_path:
            results[url] = local_path
    return results
