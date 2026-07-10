# ADR 0042: Remove search_plan, unpin search_directions, repurpose config as repair toolbook

## Context

T2 (RISC-V China) run showed info-collector collected only 20/60 expected sources (33% completion), with zh search zero output and search_plan.json never updated by agent (all tasks still `pending`). Meanwhile, the research skill (no plan, no gate) produced 45 sources with broader topic coverage (automotive, software ecosystem, standards).

Two root causes identified:
1. **search_plan is a half constraint** — not enforced (SKILL.md says "建议参考但不强制遵守"), yet it consumes agent cognitive load (read plan, align tasks, update status). It neither guides effectively nor gets out of the way.
2. **search_directions lock the search horizon** — Phase 1 defines 3 directions, but cannot anticipate topics discovered during search (e.g., automotive chips, software ecosystem). topic_coverage gate only checks preset directions, not discovered ones. This narrows the search to Phase 1's foresight.

## Decision

1. **Remove search_plan.json** entirely. No auto-generation, no task tracking, no status/collected_count fields.
2. **Unpin search_directions from gate** — directions discussed during Phase 1 interview remain in conversation context as implicit guidance, but are not written to scope.json as gate-enforced fields and are not checked by topic_coverage. Agent searches freely, guided by interview context but not constrained by it.
3. **Lightweight search gate** with 3 BLOCKER checks only:
   - `tier_coverage` (BLOCKER): each tier in the goal_type's route has ≥1 source
   - `min_sources` (BLOCKER): total collected sources ≥ depth-based threshold (quick=3, standard=5, deep=8)
   - `source_fidelity` (BLOCKER): existing check unchanged
4. **config.json role shift**: from "pre-search plan template" to "post-search repair toolbook". When a BLOCKER fires, gate queries config.json for the missing dimension's source list and emits concrete repair hints (e.g., "tier 2 零覆盖 → try site:github.com RISC-V China, site:en.wikipedia.org RISC-V").
5. **scope.json change**: search_directions field removed. scope_description retains the user's intent description as implicit guidance.

## Consequences

- Agent has full search freedom; no cognitive load from plan compliance or direction locking
- Gate acts as passive floor: agent searches freely, gate ensures minimum tier diversity and source count
- config.json sources are only consulted when agent's free search is insufficient (repair scenario)
- Phase 1 interview directions persist in conversation context — agent naturally gravitates toward them, but can also discover and pursue new directions mid-search
- Removes: search_plan.json, topic_coverage, search_plan_compliance, tier_task_completion, domain_concentration, covered_directions field, per-task min_sources/status/collected_count
- Supersedes: ADR 0001 (topic_coverage token matching), ADR 0033 (search_plan_compliance BLOCKER), ADR 0034 (reverse-compute collected_count), ADR 0010 (depth drives per-direction min-sources — now simplified to single min_sources threshold), ADR 0017 (covered_directions and gate improvements)

## Status: accepted
