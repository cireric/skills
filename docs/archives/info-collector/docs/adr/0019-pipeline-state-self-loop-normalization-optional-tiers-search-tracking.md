# ADR 0019: Pipeline State File, Review Self-Loop, Number Normalization, Optional Tiers, Search Tracking

- **Status**: Accepted
- **Date**: 2026-06-18
- **Context**: info-collector skill

## Context

2026-06-18 deep research retrospective identified 12 problems. Four low-complexity items were fixed in ADR 0018. This ADR addresses the four medium-complexity items.

## Decisions

### 1. Explicit Pipeline State File

- `.workdir/pipeline_state.json` records `current_phase` after each successful gate
- `detect_current_phase()` reads state file first, falls back to artifact presence detection
- `reset` command deletes state file and re-derives phase from remaining artifacts
- Corrupt/invalid state file → fallback to artifact detection (no crash)

**Why not state-only**: Artifact detection is the proven mechanism (ADR 0016). State file is an override, not a replacement, for backward compatibility.

### 2. Review Self-Loop Gate

- `proceed --from review --to review` is now a valid transition
- Runs the same gateway checks as `review→final`
- Eliminates the need for `reset --phase review` → `proceed --from analysis --to review` after fixing analysis.json
- The old reset path still works as a fallback

**Why not auto-detect**: The agent explicitly chooses to re-validate after fixes. Implicit re-validation could mask errors.

### 3. Number Normalization in Precision Check

- `_number_found_in_source()` replaced with `_normalize_numbers()` approach
- Handles: `$9.8B` ↔ `9.8 billion`, `45-70%` ↔ `45%` and `70%`, comma-separated `10,847` ↔ `10847`
- Short-source WARN (<200 chars) removed entirely — the precision auto-fix in `_sanitize_sections()` (ADR 0018) handles the `exact→range` downgrade at write time

**Why remove WARN rather than downgrade**: ADR 0018's auto-fix makes this runtime WARN redundant. Removing it reduces noise without losing coverage.

### 4. Optional Tier Routes

- `config.json` route schema extended: `"optional_tiers": [2]` (defaults to `[]`)
- `get_route()` and `recommend_sources()` return `optional_tiers`
- `_check_search_gate`: required tiers → WARN, optional tiers → INFO (stderr, non-blocking)
- panoramic_understanding route changed from `[4, 2, 1]` to `"path": [4, 3, 1], "optional_tiers": [2]`

**Why Tier 3 required**: Technology-trend topics have best coverage in industry blogs (Tier 3), not documentation (Tier 2). Making Tier 3 required and Tier 2 optional reflects reality.

### 5. Search Plan Execution Tracking

- `search_plan.json` task schema extended: `status` (pending/completed/skipped), `collected_count` (int)
- `references/search-strategy.md` provides tier-based search order template
- SKILL.md Phase 2 references the strategy template

**Why not enforce completion**: Agent autonomy in search is valuable. Tracking provides visibility without blocking.

## Alternatives Considered

1. **State-only detection (no artifact fallback)**: Breaks backward compatibility. If state file is deleted, pipeline is stuck.
2. **Auto-reset in proceeds()**: Would hide the phase transition from the agent, reducing transparency.
3. **Embedding-based number matching**: Violates stdlib-only constraint (ADR 0012 precedent).
4. **Tier 2 as always-required**: Empirically fails for technology-trend topics where GitHub/MDN/Wikipedia don't carry primary analysis.

## Consequences

- Review→fix→re-validate cycle reduced from 3 steps to 1 step
- Precision inflation WARN noise reduced (auto-fix + better matching + removed redundant WARN)
- panoramic_understanding route now requires Tier 3 (was missing), Tier 2 optional (was spuriously required)
- Search plan tracking provides coverage visibility without blocking
