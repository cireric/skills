# ADR 0024: Deepen claim-validation cluster into ClaimValidator module

Seven claim-related checks in `artifact_checks.py` shared helpers and each independently read `analysis.json` + `collected.json`. We consolidate them into a `ClaimValidator` class that reads once and runs all 7 checks, gaining both locality and efficiency. `_sanitize_sections`, `check_quality_heuristics`, and `check_content_concreteness` are NOT migrated — they are preprocessing or quality checks, not claim-integrity checks.

- **Status**: Accepted

## Considered Options

1. **Keep 7 independent functions** — simpler interface but 7× redundant file reads and no locality for claim bugs.
2. **Merge all 16 checks into one class** — too broad; quality/concreteness checks don't share claim-specific data.

## Consequences

- One read of `analysis.json` and `collected.json` instead of 7; shared `collected_by_url` and parsed claims.
- 7 public check functions → 1 `ClaimValidator.check()` interface.
- Boundary: claim-integrity vs quality/concreteness is explicit in module split.
