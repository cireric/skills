# ADR 0039: Search-First Then Batch-Fetch Pipeline

Production runs consistently showed agents skipping full-content fetch (Step 2.3) and writing search snippets as source content, even with ADR 0032's fetch-then-collect order. Root cause: the old flow interleaved search and fetch per-URL (search URL → fetch → add to collected.json → next URL), creating high friction — agents alternated between `exa_web_search` and `fetch CLI` per URL, and when `requests`/`Playwright` failed on JS-heavy sites, the Path B fallback (exa + pipe) required manually piping large text, which agents frequently skipped.

New flow separates discovery from fetching into two distinct steps:

1. **Step 2.2 (Search + build collected.json)**: Use `exa_web_search` for discovery only. Build collected.json with `source_file: null` and `fetched_content: ""`. No fetch CLI calls. Gate does not run yet.
2. **Step 2.3 (Batch fetch)**: Fetch all URLs by tier priority (Tier 1→2→3→4). Tier 1-2 skip Path A entirely and go straight to Path B (exa). Tier 3-4 try Path A first, fall back to Path B. After each fetch, update collected.json entries with `source_file` and `fetched_content`.
3. **Step 2.4 (Gate)**: Run gate only after all fetches complete.

Key changes from ADR 0032:
- ADR 0032 required "source file must exist before adding to collected.json" — this is relaxed to allow `source_file: null` during Step 2.2, with backfill in Step 2.3
- Tier 1-2 skip Path A (requests/Playwright) entirely — these tools almost never succeed on JS-rendered academic/tech sites, wasting time and tokens
- Batch fetching enables parallel `exa_web_fetch_exa` calls (4-6 URLs per batch), reducing total round-trips
- Gate logic unchanged — source_fidelity still BLOCKER at >30% shallow/missing files

This supersedes ADR 0032's "fetch before collect" strict ordering in favor of a two-phase approach within Phase 2.

Status: accepted
