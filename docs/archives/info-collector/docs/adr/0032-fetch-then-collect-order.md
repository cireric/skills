# ADR 0032: Fetch-Then-Collect Pipeline Order

Production run (2025 H1 Chinese LLM code gen, 11 sources) revealed that ALL source files contained only search-result summaries (~1500 chars each), not full article text. The agent skipped Phase 2 Step 2.3 (full-content fetch) and wrote search snippets directly into both `collected.json` and `.workdir/sources/`, then proceeded through the gate because summaries exceeded the 1000-char shallow threshold. The resulting report was assembled from second-hand summaries with 81% of claims marked source_indirect. Reversing the write order: fetch full text into `.workdir/sources/` FIRST, then derive `fetched_content` (first 200 chars) from the written source file when adding the entry to `collected.json`. This eliminates the shortcut of writing summaries as source content and ensures each URL is fetched exactly once.

Status: superseded by ADR-0039
