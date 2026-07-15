# ADR 0060: Agent-Driven Section Ordering

| Status | Decided |
|--------|---------|
| Date   | 2026-07-15 |

## Context

ADR 0059 fixed the section-ordering bug by adding `_sort_sections()` with a three-tier priority: `order` field > `_REQUIRED_SECTION_IDS` position > id-lexicographic. It also extended `_REQUIRED_SECTION_IDS` with entries for `panoramic_understanding`, `exploratory`, and `background_check` (via `_PANORAMIC_SECTION_ORDER`).

This design has a fundamental problem: **the ordering of exploratory sections is hardcoded in code constants, but the correct ordering depends on what the research actually found.** A panoramic report on DeepSeek didn't produce `cost_economics` or `market_industry_impact` sections, yet `_PANORAMIC_SECTION_ORDER` lists them — the hardcode assumes all panoramic research covers the same 8 dimensions.

Additionally, the `_REQUIRED_SECTION_IDS` entries for exploratory goal_types serve **only** ordering, never presence-checking — `check_section_coverage` routes exploratory types through a separate path (`_EXPLORATORY_GOAL_TYPES`) that only requires "overview + ≥2 sections". The 8-id lists were dead weight for presence-checking and false precision for ordering.

The `order` field, which was ADR 0059's Tier 1, was effectively架空-ed: Tier 2's hardcode made it unnecessary, so no agent would ever set it.

## Decision

1. **Section ordering is agent-driven for exploratory goal_types.** The agent that writes `analysis_section_*.json` assigns the `order` field based on the research content. `_sort_sections` uses `order` as the primary sort key; sections without `order` fall back to id-lexicographic.

2. **`_REQUIRED_SECTION_IDS` retains its original purpose only: presence-checking for quantitative goal_types.** It is no longer used for ordering exploratory types. For quantitative types (tech_selection, etc.), it still provides a canonical ordering as Tier 2 fallback — these types have fixed section structures where the list is genuinely authoritative.

3. **Delete `_PANORAMIC_SECTION_ORDER` and remove exploratory entries from `_REQUIRED_SECTION_IDS`.** `panoramic_understanding`, `exploratory`, `background_check`, and `other` are not in `_REQUIRED_SECTION_IDS`. Their presence-checking is handled by `_EXPLORATORY_GOAL_TYPES` path; their ordering is handled by the agent's `order` fields.

4. **`_sort_sections` behavior by goal_type:**
   - **Quantitative** (has entry in `_REQUIRED_SECTION_IDS`): `order` field > `_REQUIRED_SECTION_IDS` position > id-lexicographic
   - **Exploratory** (no entry): `order` field > id-lexicographic

5. **The orchestrator must instruct subagents to set `order` fields.** Without `order`, exploratory sections default to id-lexicographic — which would place "overview" after "community_evaluation". The `order` field is no longer optional for exploratory reports; it is the **sole** mechanism for correct ordering.

6. **Preserve `order` through sanitize** and **schema validation** — unchanged from ADR 0059.

## Consequences

- **Positive**: Section ordering reflects research content, not a hardcoded assumption about what dimensions exist.
- **Positive**: `_REQUIRED_SECTION_IDS` returns to single-responsibility (presence-checking only for quantitative types).
- **Positive**: No dead constants (`_PANORAMIC_SECTION_ORDER` removed).
- **Risk**: If the orchestrator forgets to instruct subagents to set `order`, sections default to id-lexicographic — the original bug. Mitigated by: (a) the subagent-template.md documents `order` with emphasis; (b) the section plan step already assigns reading positions.
- **Neutral**: Quantitative goal_types retain Tier 2 fallback — their fixed section structures make `_REQUIRED_SECTION_IDS` ordering appropriate.

## Supersedes

ADR 0059 — replaces the three-tier hardcode-backed ordering with agent-driven ordering for exploratory types; retains `_REQUIRED_SECTION_IDS`-backed ordering for quantitative types.
