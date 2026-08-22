# url2md

Crawl web articles to Markdown — a deterministic CLI (no LLM steps). Supports WeChat, Zhihu (columns + Q&A), Jianshu, Bilibili columns and generic pages. Driven by the `/url2md` slash command, or run directly.

> **Convention:** `venv-python` = the venv Python for the current platform — Windows: `.venv\Scripts\python.exe` · Linux/macOS: `.venv/bin/python` (per AGENTS.md). Substitute your platform's path when running commands literally.

## Usage

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

> Linux/macOS: replace `.venv\Scripts\python.exe` with `.venv/bin/python`.

## Supported Platforms

| Platform | Article Page | List Page |
|----------|--------------|-----------|
| 微信公众号 | ✅ | ✅ |
| 知乎（专栏 + 问答） | ✅ | ✅ |
| 简书 | ✅ | ✅ |
| Bilibili专栏 | ✅ | ✅ |
| 通用网页 | ✅ | ❌ |

### Zhihu Q&A notes

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

## Config

Defaults in `config.yaml` (in `scripts/url2md/`). CLI flags override config. Full schema:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_dir` | str | `"misc/"` | Output directory |
| `filename` | str\|null | null | Custom filename (single article only) |
| `download_images` | bool | false | Download images locally |
| `images_dir` | str\|null | null | Image save directory (null = `<output_dir>/images/`) |
| `delay` | float | 2.0 | Base delay between requests (seconds) |
| `max_concurrent` | int | 3 | Max concurrent image downloads |
| `headless` | bool | true | Run browser in headless mode |
| `cookies_file` | str\|null | null | Path to cookies JSON for login-required sites |
| `limit` | int\|null | null | Max articles per list page (null = all) |
| `max_retries` | int | 3 | Per-image retry count |

## Dependencies

Install into the project venv (Windows `.venv\Scripts\python.exe -m pip install …`, Linux/macOS `.venv/bin/python -m pip install …`).

| Package | Required for | Install |
|---------|-------------|---------|
| `playwright` | All crawls | `pip install playwright` |
| System Chrome | All crawls | Install Google Chrome, or `python -m playwright install chromium` |
| `pyyaml` | Config loading | `pip install pyyaml` |
| `aiohttp` | Image download only | `pip install aiohttp` |
| `aiofiles` | Image download only | `pip install aiofiles` |

`aiohttp`/`aiofiles` are only enforced by preflight when `download_images: true`.

## Programmatic API

For scenarios where the CLI is insufficient:

```python
import sys; sys.path.insert(0, "scripts/url2md")
from lib import crawl_url, CrawlResult

result: CrawlResult = crawl_url(
    url="https://mp.weixin.qq.com/s/xxx",
    output_dir="misc/",
    download_images=False,
    limit=10,
    delay=2.0,
)
```

`CrawlResult` fields: `success: bool`, `files: List[str]`, `error: Optional[str]`, `article_count: int`. Script stdout prints a human-readable summary, then a JSON array of file paths.

## Directory Layout

```
scripts/url2md/
├── crawl.py              ← CLI entry point
├── config.yaml           ← Preset configuration
├── platforms.yaml        ← Per-platform overrides
├── README.md             ← This file
├── lib/                  ← Self-contained crawl library
│   ├── __init__.py       ← Public API exports
│   ├── api.py            ← crawl_url(), CrawlResult
│   ├── browser.py        ← BrowserManager (Playwright)
│   ├── selectors.py      ← Platform detection & CSS selectors
│   ├── extractor.py      ← Article/list extraction, HTML→Markdown
│   ├── downloader.py     ← Image download with retry/dedup
│   └── utils.py          ← Delay, filename, state, asyncio config
└── tests/                ← pytest suite
```
