# ADR 0027: PR-001 Info-Collector Optimization Design Decisions

Six architectural and process decisions from the PR-001 grilling session, all derived from the same design tree. Referenced by ADR 0005 (verified field execution strengthening).

## 1. `{{ref:URL}}` reference markers replace hardcoded numbering

analysis.json content must use `{{ref:URL}}` markers (URL matching collected.json) instead of hardcoded `[N]` numbers. reporter.py owns sole numbering authority via `_resolve_ref_markers()`. No backward compatibility path for old `[N]` format — old format analysis.json will not render correctly, this is intentional to eliminate the known bug of dual numbering systems. `_build_reference_map()` merged with `_resolve_ref_markers()` (single-pass: resolve markers + build ref_map simultaneously).

## 2. claim.source_urls must be a subset of content `{{ref:URL}}` markers

No Phase B supplementation — claim.source_urls in a section must all appear as `{{ref:URL}}` markers in that section's content. Enforced by new gate check `claim_source_ref_coverage` (analysis-phase BLOCKER). This eliminates orphaned references that would otherwise trigger `report_orphaned_defs`.

## 3. `verified` field retained with strengthened execution

Considered removing `verified` (方案 C) because AI-verifying-AI is unreliable, but retained it — even imperfect verification is better than none. Execution strengthened: (a) per-claim verification with mandatory verification summary in review_report.md, (b) replaceAll/batch operations on `verified` prohibited. The review subagent writes a structured verification summary per claim: section, claim text, source URL, and confirmation detail.

## 4. config.json source entries include `language` field

Each source in config.json gains an optional `language` field (default "en"). Chinese sources (CNKI, Zhihu) explicitly marked `"zh"`. This replaces hardcoded `CHINESE_DOMAINS` / `.cn` suffix matching in `_generate_search_plan()` — task splitting is now driven by per-source language, not per-tier guessing. New sources added per tier: ACL Anthology, Semantic Scholar (Tier 1); Hugging Face, PyPI, ReadTheDocs (Tier 2); Substack, Towards Data Science, The New Stack (Tier 3); Hacker News, Dev.to (Tier 4). All new sources: language="en".

## 5. Review subagent failure: user choice, not auto-degradation

When subagent fails, ask user three options: (1) retry subagent (max 2 retries), (2) degrade to inline review (quality=degraded), (3) skip review (quality=unreviewed). Each retry failure re-asks. `review_fallback.log` records timestamp, attempt number, specific error message, and user's choice. The `degraded` quality label retains single semantics: review independence lost (same LLM wrote claims and verified them).

## 6. Route adjustments for four goal_types

competitive_comparison: entry_tier 4→2, path [4,3]→[2,3,4,1]. market_analysis: path [3,1]→[3,1,2]. background_check: path [3,4,1]→[3,4,2,1]. panoramic_understanding unchanged (optional_tiers already includes Tier 2). Path[0] always equals entry_tier per existing convention.

### Status: accepted

### Superseded by

- **Decision 3** (`verified` field retained with strengthened execution) is superseded by [ADR 0028](./0028-repositioning-to-research-starting-point.md). `verified` is now mapped deterministically from `source_verification` by `source_verification_check()` code, not set by the review subagent. The review subagent no longer performs claim-by-claim verification.

### Consequences

- Old analysis.json files (using `[N]` citations) will break — no migration path. Manual handling if needed.
- `_resolve_ref_markers()` + `_build_reference_map()` merged into single-pass; `sections_to_markdown()` becomes two-pass (first resolve markers + build ref_map, then render claims/sources/references).
- Gate analysis whitelist adds `ref_marker_validity` and `claim_source_ref_coverage` (2 new BLOCKERs).
- OPT-3 checklist item 1 must explicitly state `test_conditions` must be non-empty string, not just `source_metadata` must exist.
- OPT-3 checklist is the AI-readable version of gate rules; gate code is single source of truth.
