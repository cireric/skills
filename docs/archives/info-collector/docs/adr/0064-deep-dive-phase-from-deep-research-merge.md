# ADR 0064: Merge deep-research iterative deep-dive into info-collector

**Status**: Accepted

**Date**: 2026-08-03

**Supersedes**: deep-research skill (skills/deep-research/)

## Context

The `deep-research` skill was designed to provide iterative deep-dive research with dual-loop convergence, contradiction-driven discovery, and automatic convergence control. It complements `info-collector` (breadth) with depth.

However, the implementation is a hollow shell:

- **527-line orchestrator.py** is a prompt dispatcher with trivial gate checks (file existence + character count + URL substring). No quality semantics.
- **Design promises unimplemented**: dual-subagent triangulation, post-hoc verifier, calibration feedback loop, tagged migration, conflict merge rules.
- **Tests are pseudo-tests**: `test_convergence.py` and `test_inner_loop.py` assert Python assignment operations, not business logic.
- **No fetch infrastructure**: completely relies on agent self-direction. No tier routing, no source fidelity, no adaptive retry.
- **3 ADRs** (design stage) vs **63 ADRs** in info-collector (iterative production).

Meanwhile, `info-collector` already has:
- Complete fetch pipeline (Fetcher + FetchStrategy + UrlRewriter + adaptive retry + pipe mode + batch-fetch)
- Source quality gates (SearchGate, ClaimValidator, source_fidelity, tier_coverage)
- Structured claims with source_verification (source_confirmed/source_absent/source_indirect)
- Review + repair loop
- Report rendering with check system
- `depth: "deep"` already exists in scope.json but only drives min_sources (8) and single_source_ratio threshold (50%)

## Decision

Merge deep-research's iterative deep-dive capability into info-collector as a new pipeline phase (`deep_dive`), inserted between `analysis` and `review`. Only activated when `depth=deep`.

### New pipeline transitions

```
scope → search → analysis → deep_dive ⇌ search → review → final
```

- `depth: quick` / `depth: standard`: unchanged pipeline (analysis → review)
- `depth: deep`: analysis gate → deep_dive phase → iterative loop → review

### New transitions added to `_VALID_TRANSITIONS_SET`

- `("analysis", "deep_dive")` — enter deep-dive when depth=deep
- `("deep_dive", "search")` — re-search loop for additional sources
- `("deep_dive", "review")` — converged, proceed to review

### New artifact

`deep_dive_plan.json` — lists deep-dive targets with trigger_reason, search_queries, target_tiers, status, and convergence field.

### New gate module

`deep_dive_gate.py` — DeepDiveGate class with checks:
- `deep_dive_plan_exists` (BLOCKER)
- `target_completion` (BLOCKER)
- `deep_dive_source_depth` (BLOCKER)
- `deep_dive_verification` (BLOCKER)
- `convergence_declared` (WARN)
- `round_budget` (INFO)

### Convergence conditions (from deep-research design)

| Type | Condition | Priority |
|------|-----------|----------|
| Hard | round >= max_rounds (default 3) | Highest |
| Natural | All trigger conditions resolved | Medium |
| Soft | Consecutive N rounds with no new findings | Lowest |

### Trigger conditions (auto-detected from analysis.json)

- source_absent claims exist
- source_indirect ratio > 30%
- single_source ratio > 50% (depth=deep threshold)
- unresolved tensions

### Key design choices

1. **Only depth=deep activates** — quick/standard pipelines are completely unaffected
2. **Lightweight re-search loop** — deep_dive → search only validates new sources, not full SearchGate
3. **Agent updates sections** — no additional subagent management; agent reads new sources and updates analysis.json directly

## Consequences

### Positive

- deep-research's core value (iterative deepening) is preserved within a robust infrastructure
- No new fetch/search/analysis infrastructure needed — full reuse of existing modules
- `depth=deep` gains real teeth beyond just higher min_sources
- One fewer skill to maintain independently

### Negative

- info-collector gains complexity (2 new transitions, 1 new gate module, 1 new artifact)
- deep_dive phase adds latency to depth=deep pipelines
- deep-research skill's independent identity is lost

### Neutral

- deep-research skill marked as Superseded, docs/ADRs preserved as historical reference
- `depth=deep` scope.json field gains additional behavior beyond min_sources
