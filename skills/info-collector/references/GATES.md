# Gate System Reference

## Overview

4 gates at phase transitions. Every `proceed` command runs its checks and exits with status 0 (pass) or 1 (fail + fix instructions).

## Gate 1: `proceed --from scope --to search`

- Validates scope.json schema
- Required: topic, goal_type, depth, audience, scope_description, search_directions
- BLOCKER on missing fields

## Gate 2: `proceed --from search --to analysis`

- Validates collected.json exists with >= 1 source
- **topic_coverage (BLOCKER)**: search_directions in scope.json must be covered by collected entries. Downgraded to WARN when directions contain CJK characters (tokenization limitations).
- **min_sources (WARN)**: >= 2 unique sources (configurable per goal_type)
- **tier_coverage (WARN)**: route tiers should have at least one source each
- **per_direction_min_sources (WARN)**: each direction should have >= depth-based minimum sources

## Gate 3: `proceed --from analysis --to review`

- Runs `run_all` filtered to analysis-phase checks only (excludes `claim_verified` and `claim_source_relevance`, which are review-phase concerns)
- Schema validation + 14 analysis-phase BLOCKER checks: url_traceability, section_coverage, content_concreteness, claim_metadata, precision_inflation, metric_type_homogeneity, source_metadata, methodology_depth, recommendation_structure, source_tier_balance, claim_dedup, quality_heuristics, analysis_schema, artifact_exists
- Analysis-phase BLOCKERs are caught here, not deferred to later gates (ADR 0025)
- Also runs `source_verification_check` (WARN only, never BLOCKER) — computes three-level source_verification classification and writes `verified` on each claim deterministically
- **Agent MUST ask user**: "启动独立审查？"

## Gate 4: `proceed --from review --to final`

Review gate is advisory-only. Runs `run_all()` but never blocks — `claim_verified`
is now WARN level and `claim_source_relevance` has been replaced by `source_verification_check`
in the analysis phase. The `verified` field is set deterministically by
`source_verification_check()` code, not by the review subagent.

## Gate 5: `proceed --from final --to cleanup`

- Runs `run_report_checks()` (10 report checks)
- Only BLOCKER-level failures block the transition; WARN-level are advisory
- 3 BLOCKER checks: dangling refs (F1), orphaned defs (F2), front matter (9) — upgraded per ADR 0026
- 7 WARN checks: refs_visibility, table_delimiters, heading_levels, duplicate_headings, unclosed_code_blocks, empty_sections, overlong_lines
- **Note**: This gate skips phase detection — it passes regardless of the current detected phase. This allows cleanup to run at any point, but also means accidental invocation won't produce a phase-mismatch error.
- Transitions to cleanup phase

## Review Status Determination

Set during finalization after gate 4:

```
if gateway.heuristics_fired:  review_status = "degraded"
elif user_skipped_review:    review_status = "unreviewed"
else:                        review_status = "passed"
```
