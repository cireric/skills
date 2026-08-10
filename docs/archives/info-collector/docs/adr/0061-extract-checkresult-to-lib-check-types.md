# ADR 0061: Extract CheckResult and read_artifact to lib/check_types

| Status | Decided |
|--------|---------|
| Date   | 2026-07-15 |

## Context

`CheckResult` (a `@dataclass`) and `_read_artifact` (a helper that reads a JSON artifact and returns `CheckResult` on failure) were defined in `artifact_checks.py`. Every check module — `search_gate.py`, `claim_validator.py`, `report_checks.py`, `proceed.py` — imported `CheckResult` from `artifact_checks.py`, creating a dependency inversion: architecturally peer modules depended on a specific check module just for a cross-cutting data structure.

Additionally, `_suggest_similar_urls` was a private function in `artifact_checks.py` imported by `proceed.py` (leaky module boundary) and duplicated inline by `claim_validator.py`.

## Decision

1. **Move `CheckResult` and `_read_artifact` to `lib/check_types.py`.** `CheckResult` is a cross-cutting type used by all check modules; it belongs in `lib/` alongside `exceptions.py` and `utils.py`, not inside a specific check module. `_read_artifact` constructs `CheckResult` and depends only on `lib/` primitives (`read_json`, `ArtifactError`), so it moves with it.

2. **Rename `_read_artifact` → `read_artifact`.** Entering `lib/` makes it a public interface; the underscore prefix would mislead. Consistent with `lib/utils.py` naming (`read_json`, `normalize_url`, etc.).

3. **Move `_suggest_similar_urls` to `lib/utils.py` as `suggest_similar_urls`.** It is a URL utility function (operates on URL strings, not on artifacts). `lib/utils.py` already contains `normalize_url` and other URL helpers. Moving it eliminates the private-to-public leak across module boundaries and enables `claim_validator.py` to use the shared function instead of inline duplication.

4. **`_count_words`, `_has_concrete_name`, `_has_valid_number` stay in `artifact_checks.py`.** These are internal helpers for `check_content_concreteness`, not cross-cutting. They will relocate when `artifact_checks.py` is split into domain-cohesive submodules (future candidate).

5. **`CheckResult.level` remains `str`.** Strengthening to `Literal` or `Enum` is a separate concern; mixing it with this extraction would expand the change scope without architectural benefit.

6. **`claim_validator.py` stays in `scripts/`.** It is a check implementation, not shared infrastructure. The circular dependency root cause (`CheckResult` in `artifact_checks.py`) is resolved; the runtime dependency via `run_all()`'s lazy import is retained.

## Consequences

- **Positive**: Peer check modules (`search_gate.py`, `claim_validator.py`, `report_checks.py`) no longer depend on `artifact_checks.py` for `CheckResult`. Dependency direction is now `scripts/ → lib/`, not `scripts/ → scripts/`.
- **Positive**: `proceed.py` no longer imports a private function from `artifact_checks.py`.
- **Positive**: `claim_validator.py` can import `suggest_similar_urls` from `lib/utils.py` instead of duplicating the logic inline.
- **Neutral**: All call sites updated; no behavioral change.
- **Future**: This extraction is a prerequisite for splitting `artifact_checks.py` into domain-cohesive submodules and introducing phase-attribute check filtering.
