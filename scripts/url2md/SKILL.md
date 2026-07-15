---
name: url2md
description: Crawl web articles to Markdown. Use when user wants to crawl, scrape, or convert a URL — especially WeChat, Zhihu, Jianshu, Bilibili, or generic article pages.
---

# URL to Markdown

CLI tool at `scripts/url2md/crawl.py`. Run directly — no LLM-driven steps needed.

> **Convention:** `venv-python` = Windows `.venv\Scripts\python.exe` · Linux/macOS `.venv/bin/python`

## Usage

```bash
venv-python scripts/url2md/crawl.py "<url>" [flags]
```

| Flag | Description |
|------|-------------|
| `--preflight` | Check dependencies only |
| `--download-images` | Download images locally |
| `--limit N` | Max articles for list page |
| `--output <dir>` | Output directory (overrides config) |
| `--filename <name>` | Custom filename (single article) |
| `--delay <sec>` | Base delay between requests |

## When user says

| User intent | Action |
|------------|--------|
| "抓这篇文章" / URL provided | Run with URL, no extra flags |
| "抓几篇" / list URL | Add `--limit N` |
| "下载图片" | Add `--download-images` |
| Ambiguous | Ask user for clarification |

## Error Recovery

| Error | Action |
|-------|--------|
| 429 / rate limit | Increase `delay` in config, retry |
| Login wall | Set `cookies_file` in config |
| Playwright crash | Run `--preflight`, check Chrome |
| Partial list fail | Set `resume: true` in config, re-run |

Config: `scripts/url2md/config.yaml`. Full reference: `scripts/url2md/reference.md`.
