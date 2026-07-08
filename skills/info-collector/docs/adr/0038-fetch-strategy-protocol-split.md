# ADR 0038: FetchStrategy Protocol Split — Code Strategies Only Rewrite URLs

## Context

ADR 0037 implemented the `cli fetch` subcommand with `Fetcher` class and `FetchStrategy` Protocol. Post-implementation review identified several issues:

1. **Code strategies silently override config tools**: `ArxivStrategy.tools()` returns `["webfetch", "exa_web_fetch_exa"]` (no playwright), while config.json declares `["exa_web_fetch_exa", "webfetch", "playwright"]`. Since `get_fetch_strategy()` prioritizes code strategies, config tools are silently ignored. This means adding playwright to a source requires editing `.py` files instead of config.json — violating config-driven design.

2. **`max_characters` config field unused**: `_FETCH_DEFAULT_MAX_CHARACTERS` constant and `max_characters` in config.json are defined but no code reads them. This contradicts the "store full content" decision (ADR 0037 §7) and is YAGNI.

3. **`playwright_enabled` config field unused**: Config declares `playwright_enabled: true` but Fetcher ignores it. Only the CLI `--no-playwright` flag controls playwright behavior — no per-project config control.

4. **Shallow content discarded**: When all tools return content below the 2000-char threshold, `_try_tools()` returns `None` — even if 500 chars of real content were fetched. The agent gets `fetch_failed: true` with 0 chars, losing potentially useful partial content.

## Decision

### 1. Split Protocol: UrlRewriter + FetchStrategy

- **`UrlRewriter`** (new Protocol): single method `rewrite_url(url) → str`. Code strategies (`ArxivStrategy`, `GithubStrategy`) implement this.
- **`FetchStrategy`** (unchanged interface): `rewrite_url` + `tools` + `retries`. Fetcher consumes this.
- `get_fetch_strategy()` always returns a `FetchStrategy`. When a code strategy (UrlRewriter) exists, it composes the rewriter with tools/retries read from config.

### 2. Code strategies only implement UrlRewriter

`ArxivStrategy` and `GithubStrategy` lose their `tools()` and `retries()` methods. These are now config-driven — the single source of truth is `config.json fetch.tools`.

### 3. ComposedStrategy replaces direct code strategy returns

New `ComposedStrategy` class in `fetch_router.py`: wraps a `UrlRewriter` with config-provided `tools` and `retries`. `get_fetch_strategy()` returns this when a code strategy exists. When config has no `fetch.tools`, defaults to `["webfetch"]`.

### 4. Delete max_characters — YAGNI

Remove `_FETCH_DEFAULT_MAX_CHARACTERS` constant and `max_characters` fields from all config.json sources. The "store full content" decision (ADR 0037 §7) contradicts truncation. If needed later, the insertion point is a one-line `content[:max_characters]`.

### 5. Wire playwright_enabled config

Fetcher reads `fetch_defaults.playwright_enabled` (default `True`). Three-level priority: `--no-playwright` (CLI flag) > `playwright_enabled` (config) > `True` (default). When both `--no-playwright` is set and `playwright_enabled` is false, playwright is skipped — the more restrictive wins (OR logic: skip if either says skip).

### 6. Save best shallow content instead of discarding

When all tools return content below threshold, `_try_tools()` returns the longest result (best shallow content) instead of `None`. The resulting `FetchResult` has `content_insufficient: true` but `fetch_failed: false` — agent sees partial content and can decide whether to retry via pipe mode. Only when all tools return `None` (actual failures, not shallow content) does `fetch_failed` become `true`.

## Consequences

- Code strategies shrink: `ArxivStrategy` and `GithubStrategy` only have `rewrite_url()`
- Config is single source of truth for tools order: adding playwright to a source requires only config.json edit
- `fetch_router.py` simplifies: `ComposedStrategy` unifies code+config and config-only paths
- No more silent config override: code strategies cannot contradict config tools
- `playwright_enabled` works as per-project control
- Shallow content preserved as fallback: agent gets partial content instead of nothing
- `max_characters` cleanup: constant deleted, config fields removed

## Supersedes

- ADR 0037 §3 ("FetchStrategy unchanged") — FetchStrategy Protocol is now split into UrlRewriter + FetchStrategy
- ADR 0037 §5 ("All tools exhausted → fetch_failed: true") — now returns best shallow content with `content_insufficient: true` instead
- ADR 0037 §8 (playwright control) — adds `playwright_enabled` config control in addition to `--no-playwright`
- ADR 0037 §11 (config.json additions) — removes `max_characters` from fetch_defaults and source-level configs

## Status: accepted
