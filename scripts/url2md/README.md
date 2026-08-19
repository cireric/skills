# url2md

Crawl web articles to Markdown. Supports WeChat, Zhihu (columns + Q&A), Jianshu, Bilibili columns and generic pages.

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

# Crawl ONE zhihu answer (only that answer, not the related ones on the page)
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://www.zhihu.com/question/QID/answer/AID"

# Crawl the top-N answers of a question (sort param + --limit)
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://www.zhihu.com/question/QID?sort=vote_count" --limit 3

# Crawl several explicit answers in one run
.venv\Scripts\python.exe scripts/url2md/crawl.py "https://www.zhihu.com/question/QID/answer/A1" "https://www.zhihu.com/question/QID/answer/A2"
```

> Linux/macOS: replace `.venv\Scripts\python.exe` with `.venv/bin/python`

Zhihu Q&A notes:

- Answer pages only extract the target answer (first `.RichContent-inner`), ignoring other answers rendered below.
- Question pages (list mode) extract answers from the page's `js-initialData` — only answers loaded in the first screen batch (logged-out: ~3; logged-in: more). More answers need login cookies (`cookies_file` in `config.yaml`).
- Answer files are named `{question_title}-{answer_id}.md` to avoid collisions when crawling several answers of one question. `--filename` overrides this.

## CLI Flags

| Flag | Type | Description |
|------|------|-------------|
| `url` | positional, one or more | Article, list page, or multiple URLs |
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
