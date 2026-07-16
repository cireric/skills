---
description: Crawl a web article URL to Markdown. Supports WeChat, Zhihu, Jianshu, Bilibili, sspai and generic pages.
agent: build
---

Crawl the given URL to a Markdown file.

## Steps

1. Run: `venv-python scripts/url2md/crawl.py $ARGUMENTS`
2. Report the output file path to the user.
3. If the command fails with a Playwright or dependency error, run `venv-python scripts/url2md/crawl.py --preflight`, report the result, and stop.

## Notes

- Platforms with CDN hotlink protection (e.g. sspai) auto-download images — no `--download-images` flag needed.
- If the user encounters rate limits or login walls, tell them to edit `scripts/url2md/config.yaml` (adjust `delay`, set `cookies_file`).
