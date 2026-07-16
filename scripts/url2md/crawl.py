#!/usr/bin/env python
"""url2md CLI — crawl web articles to Markdown.

Self-contained: all logic lives in the lib/ package next to this script.
Reads config from config.yaml in the same directory.
"""

import argparse
import json
import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "lib"
CONFIG_PATH = SCRIPT_DIR / "config.yaml"

sys.path.insert(0, str(SCRIPT_DIR))


def _venv_python() -> str:
    if sys.platform == "win32":
        return ".venv\\Scripts\\python.exe"
    return ".venv/bin/python"


def _venv_pip() -> str:
    if sys.platform == "win32":
        return ".venv\\Scripts\\pip.exe"
    return ".venv/bin/pip"


def _load_config() -> dict:
    """Load config.yaml. Raises FileNotFoundError if config is missing."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}. "
            f"Create it from the skill directory template."
        )

    import yaml

    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def _find_system_chrome() -> str | None:
    """Return path to system Chrome if found, else None."""
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
            ),
            os.path.expandvars(
                r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
            ),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser(
                "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ),
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _preflight_check(strict: bool = False) -> list[str]:
    """Check that all required dependencies are available.

    Args:
        strict: If True, treat optional deps (aiohttp, aiofiles) as required.

    Returns a list of error messages (empty = all OK).
    """
    errors = []

    if not CONFIG_PATH.exists():
        errors.append(
            f"Config file not found: {CONFIG_PATH}. "
            f"Create it from the skill directory template."
        )

    try:
        import playwright  # noqa: F401
    except ImportError:
        errors.append(f"playwright not installed. Run: {_venv_pip()} install playwright")

    chrome_path = _find_system_chrome()
    if chrome_path is None:
        errors.append(
            "System Chrome not found. "
            f"Install Google Chrome, or run: {_venv_python()} -m playwright install chromium"
        )

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        msg = (
            "aiohttp not installed (needed for image download). "
            f"Run: {_venv_pip()} install aiohttp"
        )
        if strict:
            errors.append(msg)

    try:
        import aiofiles  # noqa: F401
    except ImportError:
        msg = (
            "aiofiles not installed (needed for image download). "
            f"Run: {_venv_pip()} install aiofiles"
        )
        if strict:
            errors.append(msg)

    try:
        import yaml  # noqa: F401
    except ImportError:
        errors.append(
            "PyYAML not installed (needed for config loading). "
            f"Run: {_venv_pip()} install pyyaml"
        )

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="url2md crawl script")
    parser.add_argument("url", nargs="?", help="Article or list page URL")
    parser.add_argument("--output", help="Output directory (overrides config)")
    parser.add_argument("--filename", help="Custom filename (single article only)")
    parser.add_argument("--download-images", action="store_true", help="Download images")
    parser.add_argument("--images-dir", help="Image save directory")
    parser.add_argument("--limit", type=int, help="Max articles for list page")
    parser.add_argument("--delay", type=float, help="Base delay (seconds)")
    parser.add_argument("--preflight", action="store_true", help="Run dependency check only")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.preflight:
        errors = _preflight_check()
        if errors:
            print("PREFLIGHT FAIL")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print("PREFLIGHT OK")
        return

    if not args.url:
        parser.error("url is required when not running --preflight")

    try:
        config = _load_config()
    except FileNotFoundError as e:
        print(f"配置错误: {e}")
        sys.exit(1)

    download_images = args.download_images if args.download_images else None

    errors = _preflight_check(strict=bool(download_images))
    if errors:
        print("PREFLIGHT FAIL — fix before crawling:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    from lib.api import crawl_url

    result = crawl_url(
        url=args.url,
        output_dir=args.output or config.get("output_dir"),
        download_images=download_images,
        limit=args.limit if args.limit is not None else config.get("limit"),
        delay=args.delay if args.delay is not None else config.get("delay", 2.0),
        filename=args.filename or config.get("filename"),
        images_dir=args.images_dir or config.get("images_dir"),
        headless=config.get("headless", True),
        max_concurrent=config.get("max_concurrent", 3),
        max_retries=config.get("max_retries", 3),
        cookies_file=config.get("cookies_file"),
        user_agent=config.get("user_agent"),
        browser_channel=config.get("browser_channel", "chrome"),
        viewport_width=config.get("viewport_width", 1920),
        viewport_height=config.get("viewport_height", 1080),
        locale=config.get("locale", "zh-CN"),
        timezone=config.get("timezone", "Asia/Shanghai"),
        labels=config.get("labels"),
        scroll_step_delay=config.get("scroll_step_delay", 0.3),
        scroll_settle_delay=config.get("scroll_settle_delay", 0.5),
        max_scroll_no_change=config.get("max_scroll_no_change", 3),
        image_width=config.get("image_width", 600),
        image_download_timeout=config.get("image_download_timeout", 30),
        delay_jitter=config.get("delay_jitter", 3.0),
        backoff_base=config.get("backoff_base", 1.0),
        backoff_max_wait=config.get("backoff_max_wait", 60.0),
    )

    if result.success:
        if result.article_count > 1:
            print(f"已抓取 {result.article_count} 篇文章，保存到: {args.output or config.get('output_dir', 'misc/')}")
        else:
            for f in result.files:
                print(f"已保存到: {f}")
    else:
        print(f"抓取失败: {result.error}")
        sys.exit(1)

    if result.files:
        print(json.dumps(result.files, ensure_ascii=False))


if __name__ == "__main__":
    main()
