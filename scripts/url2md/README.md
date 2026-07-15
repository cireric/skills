# url2md

Crawl web articles to Markdown. Supports WeChat, Zhihu, Jianshu, Bilibili columns and generic pages.

## Quick Start

```bash
# Preflight check
.venv\Scripts\python.exe scripts/url2md/crawl.py --preflight

# Crawl a single article
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://mp.weixin.qq.com/s/xxx"

# Crawl with image download
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://mp.weixin.qq.com/s/xxx" --download-images

# Crawl a list page (limit to 5 articles)
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://mp.weixin.qq.com/mp/profile_ext" --limit 5

# Custom output directory
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://zhuanlan.zhihu.com/p/xxx" --output docs/articles/
```

> Linux/macOS: replace `.venv\Scripts\python.exe` with `.venv/bin/python`

## CLI Flags

| Flag | Type | Description |
|------|------|-------------|
| `url` | positional | Article or list page URL (required) |
| `--output` | str | Output directory (overrides config) |
| `--filename` | str | Custom filename (single article only) |
| `--download-images` | flag | Download images locally |
| `--images-dir` | str | Image save directory |
| `--limit` | int | Max articles for list page |
| `--delay` | float | Base delay between requests (seconds) |
| `--preflight` | flag | Run dependency check only |

## Dependencies

| Package | Required for | Install |
|---------|-------------|---------|
| `playwright` | All crawls | `pip install playwright` |
| System Chrome | All crawls | Install Google Chrome, or `python -m playwright install chromium` |
| `pyyaml` | Config loading | `pip install pyyaml` |
| `aiohttp` | Image download only | `pip install aiohttp` |
| `aiofiles` | Image download only | `pip install aiofiles` |

## Config

Defaults in `config.yaml`. CLI flags override config. Full schema: see `reference.md`.
