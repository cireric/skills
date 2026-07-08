# ADR 0038: FetchStrategy Protocol Split — Code Strategies Only Rewrite URLs

## Context

ADR 0037 introduced the Fetcher class and CLI fetch subcommand. During implementation, a critical inconsistency was discovered: code strategies (`ArxivStrategy`, `GithubStrategy`) hardcode `tools()` return values that diverge from config.json `fetch.tools`. Since `get_fetch_strategy()` prioritizes code strategies over config, the config tools are silently ignored. This means:

1. ArxivStrategy returns `["webfetch", "exa_web_fetch_exa"]` — no playwright fallback, despite config declaring `["exa_web_fetch_exa", "webfetch", "playwright"]`
2. GithubStrategy has the same problem
3. Adding new tools (e.g., playwright) requires editing `.py` files instead of config.json — violating config-driven design

Additionally, two config fields were unused: `max_characters` (no code reads it) and `playwright_enabled` (Fetcher ignores it). And `_try_tools()` discards shallow content when all tools return below threshold, losing potentially useful partial content.

## Decision

### 1. Split FetchStrategy Protocol into UrlRewriter + FetchStrategy

- **`UrlRewriter`** (new Protocol): single method `rewrite_url(url) → str`. Code strategies implement this.
- **`FetchStrategy`** (unchanged interface): `rewrite_url` + `tools` + `retries`. Fetcher consumes this.
- `get_fetch_strategy()` always returns a `FetchStrategy`. When a code strategy exists, it wraps the UrlRewriter with tools/retries read from config.

### 2. Code strategies only implement UrlRewriter

`ArxivStrategy` and `GithubStrategy` implement `UrlRewriter`, not `FetchStrategy`. Their `tools()` and `retries()` methods are removed — these are now config-driven.

### 3. get_fetch_strategy() composes from code strategy + config

Priority: code UrlRewriter (if exists) + config tools/retries → ConfigRewriteStrategy (url_rewrite rules + config tools) → DefaultStrategy.

When a code strategy exists but config has no `fetch.tools`, fall back to `["webfetch"]` (same as DefaultStrategy).

### 4. Delete max_characters — YAGNI

Remove `_FETCH_DEFAULT_MAX_CHARACTERS` constant and `max_characters` fields from config.json. The "store full content" decision (Q6) contradicts truncation. If needed later, the insertion point is trivial.

### 5. Wire playwright_enabled config

Fetcher reads `fetch_defaults.playwright_enabled` (default `True`). Priority: `--no-playwright` (CLI flag) > `playwright_enabled` (config) > `True` (default).

### 6. Save best shallow content instead of discarding

When all tools return content below threshold, `_try_tools()` returns the longest result instead of `None`. The FetchResult has `content_insufficient: true` but `fetch_failed: false` — agent can see partial content and decide whether to retry via pipe mode.

## Consequences

- **Code strategies shrink**: ArxivStrategy loses `tools()` and `retries()`, only `rewrite_url()` remains
- **Config is single source of truth for tools order**: Adding playwright to a source only requires config.json edit
- **fetch_router.py simplifies**: No more dual-path logic for code strategy vs config tools
- **No more silent config override**: Code strategies can no longer contradict config
- **playwright_enabled works**: Per-project control without CLI flag repetition
- **Shallow content preserved**: Agent gets partial content as fallback instead of nothing

## Supersedes

- ADR 0037 §3 ("FetchStrategy unchanged") — FetchStrategy Protocol is now split
