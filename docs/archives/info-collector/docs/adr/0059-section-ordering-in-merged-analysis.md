# ADR 0059: Section Ordering in Merged Analysis

| Status | Superseded by ADR-0060 |
|--------|------------------------|
| Date   | 2026-07-15 |

## Context

When `_merge_section_files()` merges individual `analysis_section_*.json` files into `analysis.json`, it sorts section files by filename lexicographic order (`sorted(workdir.glob("analysis_section_*.json"))`). The reporter then renders sections in the exact array order from `analysis.json`.

This produces a structural defect: "overview" sorts *after* "comparison", "methodology", and most other section ids alphabetically. In a panoramic report on DeepSeek, the actual section order was:

1. community_evaluation
2. model_product_family
3. open_source_strategy
4. **overview** (4th position)
5. reported_limitations
6. technical_architecture

An overview section placed mid-report defeats its purpose as a navigational framework for the reader.

## Decision

1. **Add optional `order` field** to section schema (`SectionDict`). Integer, lower = earlier in report. Subagents may set it explicitly; if omitted, the merge step infers position.

2. **Add `_sort_sections()` function** in `proceed.py` with three-tier priority:
   - **Tier 1**: Explicit `order` field on the section dict (sections with `order` always precede sections without)
   - **Tier 2**: Position in `_REQUIRED_SECTION_IDS[goal_type]` for the section's id
   - **Tier 3**: id-lexicographic fallback for unknown section ids

3. **Extend `_REQUIRED_SECTION_IDS`** to include exploratory goal types (`panoramic_understanding`, `exploratory`, `background_check`) with logical reading-order lists. These lists serve dual purpose: presence-checking (existing) and ordering (new). `other` is intentionally excluded — it retains the original `["overview", "details"]` fallback in `check_section_coverage` and id-lexicographic ordering in `_sort_sections`, avoiding an unintended behavioral change from fallback-optional to required. `exploratory` reuses the same list as `panoramic_understanding` (via `_PANORAMIC_SECTION_ORDER` constant) because both goal types share the same search breadth — the distinction is depth, not scope.

4. **Preserve `order` through sanitize**: Add `order` to `_SECTION_KEYS` so `_sanitize_sections` does not strip it.

5. **Schema validation**: `order` must be int if present; validated in `schemas.py`.

## Consequences

- **Positive**: Overview and other foundational sections appear first in reports, matching reader expectations.
- **Positive**: `_REQUIRED_SECTION_IDS` now covers 9 of 10 goal types; `other` retains its original fallback semantics for both presence-checking and ordering.
- **Positive**: Subagents can override default ordering via `order` field for custom sections.
- **Neutral**: The `order` field is optional and advisory — it does not gate anything. Sections without `order` are still placed correctly via `_REQUIRED_SECTION_IDS`.
- **Risk**: If `_REQUIRED_SECTION_IDS` for a goal_type does not list a section id that appears in the data, that section falls to the end (after all known ids). This is acceptable — unknown sections should come after the canonical structure.

## Supersedes

ADR 0054 (partial) — the merge function's implicit filename-lexicographic ordering contract is replaced by `_sort_sections()`. ADR 0054's URL consistency check and idempotency decisions remain unaffected.
