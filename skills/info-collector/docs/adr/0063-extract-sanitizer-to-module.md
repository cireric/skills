# ADR 0063: Extract Section Sanitizer to sanitizer.py

| Status | Decided |
|--------|---------|
| Date   | 2026-07-15 |

## Context

`_sanitize_sections` in `proceed.py` was a 77-line function that auto-fixes subagent output before schema validation: field renaming (`section_id` → `id`, `text` → `summary`, `source_urls` → `sources`), enum aliasing (`evidence_type`, `source_type`), invalid value downgrades (`confidence`, `precision`), precision inflation correction, key whitelisting, and URL traceability filtering.

It was called from two places: `_gate_analysis` in `proceed.py` and `re_merge_after_fix` in `repair_loop.py`. Its validation constants (`_EVIDENCE_TYPE_ALIASES`, `_SOURCE_TYPE_ALIASES`, etc.) were imported from `lib/constants.py`, but its field whitelist constants (`_SECTION_KEYS`, `_CLAIM_KEYS`) were defined locally in `proceed.py`.

The auto-fix logic overlapped with `ClaimValidator`'s `_check_precision_inflation` — the sanitizer auto-downgrades `exact` → `range` for non-official evidence types, then the validator warns "auto-downgraded by sanitize". Rules for the same fields were split across two modules with no clear ownership boundary.

## Decision

1. **Extract `_sanitize_sections` to `scripts/sanitizer.py` as `sanitize_sections`.** The module owns all auto-fix logic that runs before schema validation. It is the single authority for field renaming, enum aliasing, value downgrades, precision inflation correction, key whitelisting, and URL traceability filtering.

2. **Move `_SECTION_KEYS` and `_CLAIM_KEYS` to `lib/constants.py`.** These are validation/whitelist constants, consistent with `_VALID_EVIDENCE_TYPES`, `_EVIDENCE_TYPE_ALIASES`, etc. already in `lib/constants.py`.

3. **Rename `_sanitize_sections` → `sanitize_sections`.** Cross-module call site = public interface. Consistent with `read_artifact` (ADR 0061) and `re_merge_after_fix` (ADR 0062).

4. **`ClaimValidator`'s `_check_precision_inflation` remains a defense-in-depth WARN.** The sanitizer auto-fixes the condition; the validator confirms it ran. No overlap in responsibility: sanitizer owns auto-fix, validator owns warnings.

## Consequences

- **Positive**: Auto-fix logic in one module — locality for maintainers. Changing precision rules requires editing one file, not two.
- **Positive**: `proceed.py` shrinks by ~80 lines; sanitization is clearly separated from gate dispatch.
- **Positive**: `_SECTION_KEYS` and `_CLAIM_KEYS` in `lib/constants.py` are discoverable alongside related validation constants.
- **Neutral**: `repair_loop.py` now imports `sanitize_sections` from `sanitizer.py` instead of from `proceed.py` — cleaner dependency direction.
