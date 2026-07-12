# ADR 0046: search_directions as fallback reference + coverage gap WARN

ADR 0042 removed search_plan.json and unpinned search_directions from gate enforcement. However, search_directions still exists in scope.json and serves a useful purpose as a fallback reference when agent's free search is insufficient. The current gap: no check verifies that scope-defined directions have corresponding analysis sections, allowing coverage gaps (T2 had 6 directions but only 5 sections).

1. search_directions positioning: from "gate-enforced" to "fallback reference". Agent searches freely first; when free search yields no results or gate BLOCKERs fire, agent consults search_directions + config.json source lists as fallback search guidance.
2. Add `check_direction_coverage` WARN check: read scope.json search_directions, check if analysis.json section id/title covers each direction. Uncovered directions emit WARN with suggestion to add corresponding section. Does not block pipeline.
3. SKILL.md Phase 2 guidance: agent should use search_directions as fallback, not primary search plan.

Supersedes: none (complements ADR 0042, which removed gate enforcement but did not address the fallback/coverage-gap role).

Status: accepted
