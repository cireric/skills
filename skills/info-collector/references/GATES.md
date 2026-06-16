# Gate System Reference

## Overview

5 gates at phase transitions. Every `proceed` command runs its checks and exits with status 0 (pass) or 1 (fail + fix instructions).

## Gate 1: `proceed --from scope --to search`

- Validates scope.json schema
- Required: topic, goal_type, depth, audience, scope_description, search_directions
- BLOCKER on missing fields

## Gate 2: `proceed --from search --to analysis`

- Validates collected.json exists with >= 1 source
- **topic_coverage (BLOCKER)**: search_directions in scope.json must be covered by collected entries
- **min_sources (WARN)**: >= 2 unique sources (configurable per goal_type)

## Gate 3: `proceed --from draft --to review`

- Validates analysis.json schema (topic, goal_type, sections[].id/title/content/claims[].text/source_urls)
- Validates draft/report.md exists non-empty
- **Agent MUST ask user**: "启动独立审查？"

## Gate 4: `proceed --from review --to final`

- Invokes gateway.py with 14 checks
- Always runs, even if user skipped subagent review
- 14 checks: artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, metric_type_homogeneity, claim_metadata, claim_verified, source_metadata, content_concreteness (verifies claims cite specific data/figures rather than vague generalities), methodology_depth (validates that research methodology and limitations are documented), source_tier_balance (WARN if Tier 1+2 ratio < 30% for quantitative goal types), recommendation_structure (WARN if tech_selection/competitive_comparison recommendation lacks table or "不推荐")

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
