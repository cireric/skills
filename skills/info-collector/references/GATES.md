# Gate System Reference

## Overview

5 gates at phase transitions. Every `proceed` command runs its checks and exits with status 0 (pass) or 1 (fail + fix instructions).

## Gate 1: `proceed --from scope --to search`

- Validates scope.json schema
- Required: topic, goal_type, depth, scope_description, search_directions
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

- Invokes gateway.py with 5 hard checks
- Always runs, even if user skipped subagent review
- 5 checks: artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics

## Gate 5: `proceed --from final --to cleanup`

- No structural checks
- Transitions to cleanup phase

## Quality Determination

Set during finalization after gate 4:

```
if gateway.heuristics_fired:  quality = "degraded"
elif user_skipped_review:    quality = "unreviewed"
else:                        quality = "passed"
```
