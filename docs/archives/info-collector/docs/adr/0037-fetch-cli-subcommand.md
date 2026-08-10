# ADR 0037: Fetch CLI Subcommand — Structured Web Fetch Pipeline

## Context

Production validation revealed that `exa_web_fetch_exa` default `maxCharacters=3000` truncates academic papers to summary-only length. The current fetch process is entirely manual — agent calls MCP tools, manually writes source files, manually computes url_hash and fetched_content. This leads to: (1) agents forgetting to set maxCharacters, (2) inconsistent file paths, (3) no automated cleaning or content-insufficient detection. The root cause is that fetch execution is ad-hoc agent behavior with no code enforcement.

## Decision

Add a `cli fetch` subcommand that standardizes the URL→source-file pipeline. Agent remains the orchestrator (chooses tools, decides when to use exa vs CLI), but mechanical steps (file writing, hash computation, cleaning, metadata) are code-enforced.

### 1. Dual-mode operation

- **Autonomous mode** (`cli fetch <url>`): CLI uses `requests`+`markdownify` → Playwright fallback chain
- **Pipe mode** (`cli fetch <url> --from-stdin`): Agent calls exa/webfetch externally, pipes content to CLI for post-processing
- Pipe mode stdin: try JSON parse first (`{content, tool_used?, actual_url?}`), fallback to plain text

### 2. Tool fallback chain (autonomous mode)

| Priority | Tool | Use case | maxCharacters |
|----------|------|----------|---------------|
| 1 | `requests` + `markdownify` | Static HTML pages | N/A |
| 2 | Playwright (system Chrome) | JS-rendered pages | N/A |
| — | exa_web_fetch_exa | Not callable by CLI (MCP-only) | Agent uses pipe mode |

### 3. FetchStrategy unchanged; new Fetcher class

`FetchStrategy` retains its declarative role (URL rewrite, tools list, retries). New `Fetcher` class orchestrates execution: reads strategy config → rewrites URL → tries tools in order → cleans → writes file → returns metadata.

### 4. Tool priority by tier (config.json)

Tier 1-2: `["exa_web_fetch_exa", "webfetch", "playwright"]` — exa first for long academic docs
Tier 3-4: `["webfetch", "exa_web_fetch_exa", "playwright"]` — webfetch first for short blog posts

### 5. Content-insufficient threshold

Fetched content < 2000 chars → trigger fallback to next tool. All tools exhausted → `fetch_failed: true`.

### 6. Conservative cleaning (webfetch/Playwright output only)

Remove: `<nav>`, `<footer>`, `<aside>`, cookie/GDPR prompts, social share buttons, breadcrumbs, comment sections, "related articles" blocks.
Preserve: LaTeX markup, figure descriptions, tables, code blocks.
Exa output: skip cleaning (already clean markdown). Pipe mode: skip cleaning (agent-controlled content).

### 7. No content summarization

Source files store full fetched content. Summarization is analysis-phase responsibility.

### 8. Playwright configuration

Soft dependency. Auto-detect system Chrome via `channel="chrome"`. Fallback to `channel="chromium"` if no system Chrome. Playwright package not installed → skip Playwright tier entirely. `--no-playwright` flag to explicitly disable.

### 9. CLI interface

```
cli fetch <url> [--tier N] [--no-playwright] [--from-stdin]
```

- `--tier`: affects retry count and tool priority. Auto-inferred from URL domain matching config.json sources. Default: 3 (conservative).
- `--no-playwright`: skip Playwright fallback
- `--from-stdin`: read fetched content from stdin instead of autonomous fetch

### 10. JSON output (stdout)

```json
{
  "url": "https://arxiv.org/abs/2503.15223",
  "actual_url": "https://ar5iv.labs.arxiv.org/html/2503.15223",
  "source_file": "sources/c2044dc13fca.md",
  "url_hash": "c2044dc13fca",
  "char_count": 42350,
  "fetched_content": "# Are \"Solved Issues\" in SWE-bench...",
  "fetch_failed": false,
  "tool_used": "exa_web_fetch_exa",
  "content_insufficient": false,
  "source_tier": 1
}
```

- `url_hash` computed from **original URL** (not rewritten URL) using existing `compute_url_hash()`
- `source_tier` auto-inferred from URL domain matching config.json; `null` if unmatched
- `fetched_content` = first 200 chars of source file (same as collected.json convention)
- Exit code: 0 = success (even if content_insufficient), 1 = all tools failed (fetch_failed)
- Idempotent: re-running overwrites existing source file

### 11. config.json additions

New top-level `fetch_defaults` block for global settings, with source-level overrides:

```json
{
  "fetch_defaults": {
    "source_dir": ".workdir/sources/",
    "max_characters": 50000,
    "shallow_threshold": 2000,
    "playwright_enabled": true,
    "playwright_channel": "chrome",
    "playwright_timeout": 30000
  }
}
```

Source-level `fetch` blocks can override `tools`, `max_characters` per source (existing pattern extended).

### 12. Retry logic

- Per FetchStrategy.retries(tier): Tier 1-2 retry each tool 2×, Tier 3-4 retry 1×
- Tool fails (exception/timeout/HTTP error) → next tool
- Tool succeeds but char_count < shallow_threshold → next tool
- All tools exhausted → fetch_failed: true, source_file: null, fetched_content: ""
- Global timeout: 60s per URL

## Consequences

- Agent workflow changes: `cli fetch` replaces manual source file writing in SKILL.md Step 2.3
- exa remains the strongest tool but requires pipe mode — SKILL.md must document the two-path workflow
- Playwright is a new optional dependency; `pip install playwright` + system Chrome needed for JS rendering fallback
- `markdownify` is a new required dependency for HTML→Markdown conversion
- config.json gains `fetch_defaults` block (development-time addition, not runtime modification)
- Existing source files and collected.json entries are unaffected (same url_hash algorithm, same file paths)
- Supersedes the informal fetch guidance in SKILL.md Step 2.3; replaces with concrete CLI command

## Status: accepted
