---
name: url2md
description: Crawl web articles to Markdown. Use when user wants to crawl, scrape, or convert a URL — especially WeChat, Zhihu, Jianshu, Bilibili, or generic article pages.
---

# URL to Markdown Crawler

Self-contained — all code lives in this skill directory. Zero project imports.

## Steps

### 1. Preflight

Run dependency check:

```bash
.venv\Scripts\python.exe .opencode\skills\url2md\scripts\crawl.py --preflight
```

**Done when:** `PREFLIGHT OK` printed. If FAIL, install missing deps from the output and re-run.

### 2. Infer parameters

| User intent | `url` | Flags |
|------------|-------|-------|
| "抓这篇文章" / URL provided | required | none (use config defaults) |
| "抓几篇" / list URL | required | `--limit 5` |
| "下载图片" | required | `--download-images` |
| Ambiguous ("抓所有文章") | required | **Ask user:** how many? download images? |

**Done when:** URL confirmed, all flags decided.

### 3. Crawl

```bash
.venv\Scripts\python.exe .opencode\skills\url2md\scripts\crawl.py "<url>" [flags]
```

**Done when:** script exits 0 and file path(s) printed.

### 4. Report

Tell user the output:

- Single: `已保存到: <path>`
- List: `已抓取 N 篇文章，保存到: <dir>`

**Done when:** user informed of file location.

## Branches

- **Article page** → crawl single, return one path
- **List page** → crawl batch with delay, return multiple paths
- **Unknown type** → attempt as article page (fallback)

## Config

Defaults in `config.yaml`. CLI flags override config. Full config schema and CLI flags: see `reference.md`.

## Error Recovery

| Error | Action |
|-------|--------|
| 429 / rate limit | Increase `delay` in config, retry |
| Login wall | Set `cookies_file` in config |
| Playwright crash | `--preflight`, reinstall browser |
| Partial list fail | Set `resume: true` in config, re-run |

Full dependency list, config schema, CLI flags, and API details: see `reference.md`.
