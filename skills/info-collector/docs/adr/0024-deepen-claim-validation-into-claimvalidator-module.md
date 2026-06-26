# ADR 0024: Deepen claim-validation cluster into ClaimValidator module

## Status

Accepted

## Context

Seven claim-related checks lived as peer functions in `artifact_checks.py`: `check_claim_metadata`, `check_precision_inflation`, `check_claim_verified`, `check_source_metadata`, `check_metric_type_homogeneity`, `check_claim_dedup`, `check_claim_source_relevance`. They shared helpers (`_normalize_numbers`, `_number_found_in_source`, `_source_text`, `_check_data_variance`) that were public by convention. Each check independently read `analysis.json` and `collected.json`, building `collected_by_url` from scratch each time.

The checks all run at the same pipeline stage (review gate) and operate on the same data. A `ClaimValidator` class that reads artifacts once and runs all checks provides both locality (claim bugs in one module) and efficiency (one read, shared parsed data).

`_sanitize_sections` in `proceed.py` was NOT migrated — it's a preprocessing/auto-fix function (fixes AI subagent output before validation), not a validation check.

`check_quality_heuristics` and `check_content_concreteness` were NOT migrated — they are quality/concreteness checks, not claim-integrity checks.

## Decision

Create `scripts/claim_validator.py` with a `ClaimValidator` class:
- `__init__(workdir, goal_type)` — reads `analysis.json` + `collected.json` once, builds shared data structures
- `check() → list[CheckResult]` — runs all 7 claim checks, returns flat results

Shared helpers (`_normalize_numbers`, `_number_found_in_source`, `_source_text`, `_check_data_variance`, `_PRECISE_NUMBER_PATTERN`) become module-private in `claim_validator.py`.

`run_all` in `artifact_checks.py` calls `ClaimValidator(workdir, goal_type).check()` instead of 7 individual functions.

## Consequences

- One read of `analysis.json` and `collected.json` instead of 7
- Shared `collected_by_url` and parsed claims list instead of per-check construction
- 7 public check functions → 1 `ClaimValidator.check()` interface
- Tests follow the module: `test_claim_validator.py` tests through the public `check()` interface
