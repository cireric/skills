# ADR 0026: Upgrade F1/F2/9 report checks from WARN to BLOCKER

Three report-level checks — dangling refs (F1), orphaned defs (F2), and front matter (9) — were WARN level, meaning `_gate_final` would never block on them. These indicate broken cross-references or missing metadata, not stylistic issues. We upgrade them to BLOCKER rather than changing `_gate_final` to filter WARN-level failures, because the correct fix is to raise severity of the checks that genuinely matter.

- **Status**: Accepted

## Considered Options

1. **Change `_gate_final` to ignore WARN** — would weaken all report checks as a side effect.
2. **Upgrade only the checks that matter** (chosen) — targeted, preserves advisory nature of the other 7 checks.

## Consequences

- Dangling refs, orphaned defs, and missing front matter now block the final→cleanup transition (not review→final, which uses `_gate_review`).
- The other 7 report checks (refs_visibility, table_delimiters, heading_levels, duplicate_headings, unclosed_code_blocks, empty_sections, overlong_lines) remain advisory WARN.
