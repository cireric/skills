# ADR 0062: Extract Repair Loop to repair_loop.py

| Status | Decided |
|--------|---------|
| Date   | 2026-07-15 |

## Context

The repair loop — the cycle of (detect issue → apply fix → re-validate) — is a first-class domain concept in CONTEXT.md, yet it had no dedicated module. Its implementation was scattered across `proceed.py` in three functions (`check_fix_report`, `determine_review_status`, `_re_merge_after_fix`) totaling ~80 lines, plus a dispatch block in `_gate_review`.

Additionally, `cli.py` contained `_detect_review_status`, an independent review-status detection mechanism that parses `review_report.md` with regex, diverging from `determine_review_status` which reads structured JSON artifacts (`fix_report.json`, `lightweight_review_result.json`). The two paths could produce different results for the same workdir.

## Decision

1. **Extract `check_fix_report`, `determine_review_status`, and `re_merge_after_fix` to `scripts/repair_loop.py`.** These three functions form the repair loop's core logic. The module owns the full repair loop lifecycle: parse fix report → determine status → re-merge analysis after fixes.

2. **Rename `_re_merge_after_fix` → `re_merge_after_fix`.** It is a cross-module call site (`_gate_review` in `proceed.py` calls it), so it is effectively public. The underscore prefix was misleading.

3. **`_merge_section_files` and `_sanitize_sections` remain in `proceed.py`.** They are pipeline infrastructure, not repair loop semantics. `re_merge_after_fix` imports them from `proceed.py` via lazy import (avoiding circular dependency at module load time).

4. **`_gate_review` continues calling `check_fix_report` directly** rather than `determine_review_status`. The gate needs fine-grained data (`blocker_fixed` triggers re-merge, `warn_skipped` produces a log message); `determine_review_status` only returns "passed"/"degraded".

5. **`_detect_review_status` in `cli.py` is not unified in this extraction.** The two mechanisms (regex on Markdown vs. structured JSON parsing) serve different semantic contexts. Unification is a separate architectural decision.

6. **`__all__` lists all three public functions.**

## Consequences

- **Positive**: Repair loop logic is in one module — locality for maintainers.
- **Positive**: `proceed.py` shrinks by ~80 lines; repair loop functions are easier to find and test.
- **Positive**: `determine_review_status` is now importable from a dedicated module, making future unification with `cli.py` straightforward.
- **Neutral**: `re_merge_after_fix` has a lazy import from `proceed.py` for `_merge_section_files` and `_sanitize_sections`. This is a runtime dependency that could be refactored when those functions are extracted to their own modules (future candidates).
- **Future**: Unifying `_detect_review_status` with `determine_review_status` is a separate decision requiring careful design of fail-verdict handling.
