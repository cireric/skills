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

- Validates analysis.json has topic, goal_type, and non-empty sections
- **url_traceability (BLOCKER)**: all claim source_urls must exist in collected.json
- **Agent MUST ask user**: "启动独立审查？"

## Gate 4: `proceed --from review --to final`

- Invokes gateway.py with 15 checks
- Always runs, even if user skipped subagent review
- 15 checks: artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, metric_type_homogeneity, claim_metadata (applies to all goal_types), claim_verified (includes verified ratio < 60% WARN), source_metadata, content_concreteness, methodology_depth, recommendation_structure, source_tier_balance, claim_dedup (WARN if same claim text appears in multiple sections)

## Gate 5: `proceed --from final --to cleanup`

- No structural checks
- **Note**: This gate skips phase detection — it passes regardless of the current detected phase. This allows cleanup to run at any point, but also means accidental invocation won't produce a phase-mismatch error.
- Transitions to cleanup phase

## Quality Determination

Set during finalization after gate 4:

```
if gateway.heuristics_fired:  quality = "degraded"
elif user_skipped_review:    quality = "unreviewed"
else:                        quality = "passed"
```
