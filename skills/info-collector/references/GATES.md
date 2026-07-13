# Gate System Reference

## Overview

4 gates at phase transitions. Every `proceed` command runs its checks and exits with status 0 (pass) or 1 (fail + fix instructions).

## Gate 1: `proceed --from scope --to search`

- Validates scope.json schema
- Required: topic, goal_type, depth, audience, scope_description, search_directions
- BLOCKER on missing fields

## Gate 2: `proceed --from search --to analysis`

- **collected_exists (BLOCKER)**: collected.json must exist with >= 1 entry
- **collected_schema (BLOCKER)**: each entry needs url/title/snippet; `direction` if present must be a non-empty string (ADR 0052)
- **min_sources (BLOCKER)**: depth-based minimum collected entries (quick=3, standard=5, deep=8)
- **tier_coverage (BLOCKER for required tiers, INFO for optional tiers)**: route tiers must each have >= 1 source (ADR 0042; panoramic Tier 2 now required per ADR 0049)
- **source_fidelity (BLOCKER)**: source files present with sufficient depth (full content, not just snippets)
- **direction_tagging (BLOCKER, only when scope.search_directions is non-empty)**: every collected entry must carry a `direction` field (ADR 0052)
- **direction_coverage (BLOCKER, only when scope.search_directions is non-empty)**: every declared direction must have >= 1 collected entry tagged to it (ADR 0052)

> Note: `topic_coverage` was removed (ADR 0042); breadth is enforced via `direction_*` checks (user-declared contract) + `facet_coverage` (WARN safety net at analysis, ADR 0050), not a preset topic list.

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

## Gate 5: pipeline termination (no `final→cleanup` transition)

The pipeline terminates at `post_final`. There is **no `final→cleanup` transition** — `_VALID_TRANSITIONS_SET` does not contain `("final", "cleanup")` (ADR 0029 removed the cleanup phase). `proceed --from final --to cleanup` returns `Invalid transition`. Report checks (`run_report_checks`, 3 BLOCKER + 7 WARN per ADR 0026) run at the `final` gate (`proceed --from review --to final`).

To remove the intermediate `.workdir/` directory, use the standalone command `python -m scripts.cli clean` — this is a manual utility, not a pipeline phase.

## Review Status Determination

Set during finalization after gate 4:

```
if gateway.heuristics_fired:  review_status = "degraded"
else:                        review_status = "passed"
```
