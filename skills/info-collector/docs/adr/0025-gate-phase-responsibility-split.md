# ADR 0025: Gate phase responsibility split

Each pipeline gate now checks only its own phase's concerns, and BLOCKERs are caught at the earliest possible stage. Previously, `_gate_analysis` only checked `url_traceability`, deferring other analysis-phase BLOCKERs to `_gate_review` or later; `_gate_review` ran the full gateway, meaning review loops could be blocked by analysis-phase issues that should have been caught earlier.

- **Status**: Accepted

## Decision

- **`_gate_analysis`** (analysis→review): filters `run_all` results to analysis-phase checks only — excludes `claim_verified` and `claim_source_relevance` (review-phase concerns). The specific check names are defined in code, not here — see `proceed.py`.
- **`_gate_review`** (review→review, review→final): filters to `claim_verified` and `claim_source_relevance` only. Only `claim_verified` is BLOCKER level.
- **`_gate_final`** (final→cleanup): runs `run_report_checks()`. Only BLOCKER-level failures block the transition; WARN-level failures are advisory. See ADR 0026 for which report checks are BLOCKER.

## Consequences

- Analysis-phase BLOCKERs caught at analysis→review, not later.
- Review gate no longer re-checks analysis concerns.
- `claim_verified` is the only review-phase BLOCKER that blocks the pipeline.
