# ADR 0022: Deepen search gate into SearchGate module

- **Status**: Accepted
- **Date**: 2026-06-25
- **Context**: info-collector skill

The search→analysis gate logic was scattered across six files (proceed.py, artifact_checks.py, gateway.py, lib/schemas.py, lib/source_router.py, lib/constants.py). Understanding one gate required reading all six. The module was shallow — interface surface nearly as wide as the implementation.

Collapse all search-gate validation logic into a single `SearchGate` class in `scripts/search_gate.py`. Interface: `SearchGate(workdir, config).check() → list[CheckResult]`. Internal helpers (_check_topic_coverage, _check_tier_coverage, _check_fetched_content_depth, _check_search_plan_compliance, _tokenize_direction, _is_stop_word) are private. `__init__` pre-reads scope.json, collected.json, search_plan.json to avoid repeated I/O. proceed.py retains a thin adapter `_gate_search` that calls SearchGate.check() and filters results. check_fetched_content_depth and check_search_plan_compliance are removed from artifact_checks.py and gateway.py. Tests move to test_search_gate.py.

Shared infrastructure (validate_collected, source_router, constants) stays in lib/ — SearchGate calls it but does not own it. _generate_search_plan stays in proceed.py (it is a scope-gate side-effect, not a search-gate validation). _sanitize_sections stays in proceed.py (Candidate 2 will handle it).
