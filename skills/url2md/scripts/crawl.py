#!/usr/bin/env python
"""url2md inline crawl script — invoked by the url2md skill.

Self-contained: all logic lives in the lib/ package next to this script.
No dependency on src/data_crawl or any project module.
Reads config from config.yaml in the skill directory.
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
LIB_DIR = SKILL_DIR / "lib"
CONFIG_PATH = SKILL_DIR / "config.yaml"

sys.path.insert(0, str(SKILL_DIR))


def _load_config() -> dict:
    """Load config.yaml, falling back to defaults if missing or invalid."""
    defaults = {
        "output_dir": "misc/",
        "filename": None,
        "download_images": False,
        "images_dir": None,
        "delay": 2.0,
        "max_delay": 5.0,
        "max_concurrent": 3,
        "headless": True,
        "cookies_file": None,
        "limit": None,
        "resume": False,
        "state_file": "url2md-state.json",
        "max_retries": 3,
    }

    if not CONFIG_PATH.exists():
        return defaults

    try:
        import yaml

        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (ImportError, OSError):
        return defaults

    for key, value in data.items():
        if key in defaults and value is not None:
            defaults[key] = value

    return defaults


def _preflight_check(strict: bool = False) -> list[str]:
    """Check that all required dependencies are available.

    Args:
        strict: If True, treat optional deps (aiohttp, aiofiles) as required.

    Returns a list of error messages (empty = all OK).
    """
    errors = []

    try:
        import playwright  # noqa: F401
    except ImportError:
        errors.append("playwright not installed. Run: .venv\\Scripts\\pip.exe install playwright")

    try:
        from playwright.sync_api import sync_playwright

        p = sync_playwright().start()
        try:
            p.chromium.launch(headless=True, channel="chrome").close()
        except Exception:
            errors.append(
                "Playwright browser not installed. "
                "Run: .venv\\Scripts\\python.exe -m playwright install chrome"
            )
        finally:
            p.stop()
    except Exception as exc:
        errors.append(f"Playwright browser check failed: {exc}")

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        msg = (
            "aiohttp not installed (needed for image download). "
            "Run: .venv\\Scripts\\pip.exe install aiohttp"
        )
        if strict:
            errors.append(msg)

    try:
        import aiofiles  # noqa: F401
    except ImportError:
        msg = (
            "aiofiles not installed (needed for image download). "
            "Run: .venv\\Scripts\\pip.exe install aiofiles"
        )
        if strict:
            errors.append(msg)

    try:
        import yaml  # noqa: F401
    except ImportError:
        errors.append(
            "PyYAML not installed (needed for config loading). "
            "Run: .venv\\Scripts\\pip.exe install pyyaml"
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

    config = _load_config()
    download_images = args.download_images or config["download_images"]

    errors = _preflight_check(strict=bool(download_images))
    if errors:
        print("PREFLIGHT FAIL — fix before crawling:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    from lib.api import crawl_url

    result = crawl_url(
        url=args.url,
        output_dir=args.output or config["output_dir"],
        download_images=download_images,
        limit=args.limit or config["limit"],
        delay=args.delay or config["delay"],
        filename=args.filename or config["filename"],
        images_dir=args.images_dir or config["images_dir"],
    )

    if result.success:
        if result.article_count > 1:
            print(f"已抓取 {result.article_count} 篇文章，保存到: {config['output_dir']}")
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
