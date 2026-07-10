# ADR 0041: batch-fetch CLI Subcommand

ADR 0040 added an anti-pattern prohibition and a gate heuristic, but the root cause remained: the agent had to manually pipe each URL's content to CLI `--from-stdin` one at a time, which was tedious enough to motivate shortcutting. The `batch-fetch` subcommand eliminates the shortcut incentive by making the correct path the easy path.

Design:
- `cli batch-fetch --pending` lists URLs that still need source files, grouped by tier
- `cli batch-fetch --from-stdin` accepts a JSON array of `{url, content, tier?}` via stdin
- For each item, calls `Fetcher.save_piped()` to write the source file and compute metadata
- Automatically updates `collected.json` with `source_file`, `fetched_content`, `source_tier`, and `fetch_failed` fields
- The agent's workflow becomes: `exa_web_fetch_exa(urls)` → pipe JSON array → `cli batch-fetch --from-stdin` → done

Key property: the agent never touches content between exa output and source file. `batch-fetch` is a single transactional step — either the full text goes into the source file or the fetch fails. No intermediate step where the agent could summarize.

Supersedes: none. The per-URL `cli fetch --from-stdin` remains available for cases where `batch-fetch` is impractical (e.g., fetching one URL at a time during interactive sessions). But `batch-fetch` is the recommended default for Step 2.3.

Status: accepted
