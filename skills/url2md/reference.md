# url2md Reference

Disclosed reference for the url2md skill. Agent loads this on demand — not needed on every run.

## Skill Directory Layout

```
.opencode/skills/url2md/
├── SKILL.md              ← Steps and branches
├── config.yaml           ← Preset configuration
├── reference.md          ← This file
├── scripts/
│   └── crawl.py          ← CLI entry point
└── lib/                  ← Self-contained crawl library
    ├── __init__.py       ← Public API exports
    ├── api.py            ← crawl_url(), CrawlResult
    ├── browser.py        ← BrowserManager (Playwright)
    ├── selectors.py      ← Platform detection & CSS selectors
    ├── extractor.py      ← Article/list extraction, HTML→Markdown
    ├── downloader.py     ← Image download with retry/dedup
    └── utils.py          ← Delay, filename, state, asyncio config
```

## Supported Platforms

| Platform | Article Page | List Page |
|----------|--------------|-----------|
| 微信公众号 | ✅ | ✅ |
| 知乎专栏 | ✅ | ✅ |
| 简书 | ✅ | ✅ |
| Bilibili专栏 | ✅ | ✅ |
| 通用网页 | ✅ | ❌ |

## Dependencies

| Package | Required for | Install |
|---------|-------------|---------|
| `playwright` | All crawls | `.venv\Scripts\pip.exe install playwright` |
| Playwright browser | All crawls | `.venv\Scripts\python.exe -m playwright install chrome` |
| `aiohttp` | Image download only | `.venv\Scripts\pip.exe install aiohttp` |
| `aiofiles` | Image download only | `.venv\Scripts\pip.exe install aiofiles` |
| `pyyaml` | Config loading | `.venv\Scripts\pip.exe install pyyaml` |

`aiohttp`/`aiofiles` are only enforced by preflight when `download_images: true`.

## Config Schema

File: `config.yaml` (next to SKILL.md). Missing file → built-in defaults used.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_dir` | str | `"misc/"` | Output directory |
| `filename` | str\|null | null | Custom filename (single article only) |
| `download_images` | bool | false | Download images locally |
| `images_dir` | str\|null | null | Image save directory (null = `<output_dir>/images/`) |
| `delay` | float | 2.0 | Base delay between requests (seconds) |
| `max_delay` | float | 5.0 | Max delay cap (seconds) |
| `max_concurrent` | int | 3 | Max concurrent image downloads |
| `headless` | bool | true | Run browser in headless mode |
| `cookies_file` | str\|null | null | Path to cookies JSON for login-required sites |
| `limit` | int\|null | null | Max articles per list page (null = all) |
| `resume` | bool | false | Enable checkpoint resume for list crawls |
| `state_file` | str | `"url2md-state.json"` | State file path for resume |
| `max_retries` | int | 3 | Per-image retry count |

## CLI Flags

| Flag | Type | Description |
|------|------|-------------|
| `url` | positional | Article or list page URL (required) |
| `--output` | str | Output directory (overrides config) |
| `--filename` | str | Custom filename (single article only) |
| `--download-images` | flag | Download images locally |
| `--images-dir` | str | Image save directory |
| `--limit` | int | Max articles for list page |
| `--delay` | float | Base delay (seconds) |
| `--preflight` | flag | Run dependency check only |

## Return Value

```python
@dataclass
class CrawlResult:
    success: bool           # Whether crawl succeeded
    files: List[str]        # Generated file paths
    error: Optional[str]    # Error message if failed
    article_count: int      # Number of articles crawled
```

Script output: human-readable summary on stdout, then JSON array of file paths.

## Programmatic API

For scenarios where the CLI script is insufficient:

```python
import sys; sys.path.insert(0, ".opencode/skills/url2md")
from lib import crawl_url, CrawlResult

result: CrawlResult = crawl_url(
    url="https://mp.weixin.qq.com/s/xxx",
    output_dir="misc/",
    download_images=False,
    limit=10,
    delay=2.0,
)
```
