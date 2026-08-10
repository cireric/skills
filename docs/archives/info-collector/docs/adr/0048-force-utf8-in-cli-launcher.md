# ADR 0048: force UTF-8 mode in the CLI launcher

## Context

The DeepSeek retrospective (§1.2) hit a hard `UnicodeEncodeError` on Windows:
`sys.stdin.read()` decodes UTF-8 as cp936, producing surrogate characters
(`\udc94`) that `path.write_text(..., encoding="utf-8")` then rejects. The
report's own mitigation was "write it in the docs" — but documentation is not
robustness: the next run still fails until someone reads the note and sets
`$env:PYTHONUTF8='1'` by hand. That is exactly the "depends on human bailout"
fragility the retrospective criticizes.

## Decision

`scripts/__main__.py` sets `os.environ["PYTHONUTF8"] = "1"` at import time, before
any stdin/stdout/file IO occurs. The CLI is UTF-8-safe out of the box on Windows,
with no agent memory or doc-reading required.

## Consequences

- Scope: process-local env var; only affects how this CLI decodes/encodes text.
  Correct behavior for a CJK-heavy research skill.
- Backwards compatible on Linux/macOS (UTF-8 is already the default there).
- Documents may still mention it, but the code no longer depends on the note.

## Status: accepted
