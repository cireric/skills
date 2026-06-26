# ADR 0023: Remove gateway.py re-export layer

## Status

Accepted

## Context

`scripts/gateway.py` was a pure re-export module: it imported everything from `artifact_checks.py` and `report_checks.py` and re-exported them under a single namespace. After Candidate 1 (ADR 0022) removed the search-gate checks from `artifact_checks.py`, the only consumers of `gateway.py` were test files. No production code imported from it.

A pure re-export layer with zero production callers is shallow — it adds a file and an import hop without concentrating complexity. The deletion test confirms: deleting it just moves imports to the real modules.

## Decision

Delete `gateway.py`. Update all test imports to reference `artifact_checks` or `report_checks` directly. Delete `test_gateway_import.py` (it tested gateway.py's import invariants, which no longer exist).

## Consequences

- All callers now import from the module that actually defines the symbol — one less indirection hop.
- `CheckResult` is imported from `artifact_checks` (where it's defined), not from `report_checks` (which merely re-imports it).
- The CLI subcommand `gateway` and the function `get_gateway_results` remain in `proceed.py` — they're about the *concept* of gateway checks, not the deleted file.
