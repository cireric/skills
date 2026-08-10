# ADR 0029: Gate Philosophy Shift — Auto-Downgrade and Honest Marking

## Context

A production run (2026 Agentic Coding trends, 60 sources, 70 claims) required ~100 manual metadata fixes despite all gates passing. The root cause: gates forced LLM to make source-authority judgments it systematically gets wrong (inflating Tier 3 data to `official_data`+`exact`). ADR 0028 repositioned info-collector as "research starting point", but gate enforcement still assumed "quality-gated report" semantics.

## Decision

Shift gate philosophy from "force LLM to ensure source accuracy" to "auto-downgrade suspicious metadata + honestly mark". Seven changes:

1. `precision_inflation`: all cases → WARN (auto-downgraded by `_sanitize_sections`; data_variance is also WARN — conflicting exact values per metric_type is a judgment issue, not structural)
2. `source_metadata`: BLOCKER → WARN (official reports lacking test_conditions is normal for research starting point)
3. `metric_type_homogeneity`: BLOCKER → WARN (discussing multiple benchmarks per section is normal)
4. `content_concreteness`: strict BLOCKER → unified WARN (research starting point doesn't require numbers in every section; removed `_CONCRETENESS_STRICT_GOAL_TYPES` constant)
5. `source_verification_check`: WARN → INFO (73% indirect ratio is normal for research starting point, not a problem to fix)
6. `claim_verified`: removed (field now set deterministically by `source_verification_check`, check was redundant)
7. Phase 4 (Cleanup) removed from pipeline — redundant with Phase 0 `.workdir/` check and `cli clean` command

Additionally: URL traceability checks now include "did you mean" prefix-match suggestions to accelerate manual fix of truncated/mangled URLs.

BLOCKER count reduced from 18 to 11. All removed BLOCKERs were "force LLM judgment" checks; all retained BLOCKERs are "ensure structural integrity" checks (artifact_exists, url_traceability, section_coverage, analysis_schema, ref_marker_validity, claim_source_ref_coverage, report_dangling_refs, report_orphaned_defs, report_front_matter, english_title, scope_schema).

## Consequences

- Pipeline no longer blocks on LLM's inability to correctly classify evidence types — `_sanitize_sections` auto-downgrades and gate marks as WARN
- Reports will have more WARN items but fewer manual fix cycles
- Users must still review ‡/† markers — the shift makes fabrication visible, not eliminated
- Supersedes ADR 0025's claim that `claim_verified` is the only review-phase BLOCKER — it is now removed entirely
- Pipeline terminates at `post_final` instead of `post_cleanup`; `cli clean` available for manual cleanup

## Status: accepted
