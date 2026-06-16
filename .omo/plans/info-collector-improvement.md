# Info-Collector Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve info-collector report quality (concreteness, source credibility, structured recommendations) and engineering robustness (custom exceptions, retry), with critical fixes applied from code review.

**Architecture:** 3-batch incremental improvement. Batch 1 fixes the duplicate-title rendering bug and adds concreteness + methodology depth gates. Batch 2 adds source tier labels and structured recommendation validation. Batch 3 adds custom exception classes and file operation retry.

**Tech Stack:** Python 3.10+, pytest, jieba

---

## Critical Fixes Applied (vs Original Plan)

| # | Original Plan Issue | Fix Applied |
|---|---|---|
| 1 | `_STOP_WORDS` imported from `proceed.py` drags jieba into `gateway.py` | Extract `_STOP_WORDS` to `lib/constants.py`; `_has_concrete_name` uses CJK char-run heuristic instead of jieba |
| 2 | `BLOCKER + passed=True` semantic contradiction in Tasks 2 & 9 | Use `level="WARN"` for advisory checks (consistent with `quality_heuristics`, `claim_metadata`) |
| 3 | Recommendation structure check mixed into `check_section_coverage` | Extract to independent `check_recommendation_structure` with `level="WARN"` |
| 4 | `except (ArtifactError, FileNotFoundError, json.JSONDecodeError)` dead code | Only catch `ArtifactError` where `read_json` is sole source; keep `except Exception` for complex handlers |
| 5 | Chinese vague phrase density: char-based word count inflates denominator | Use CJK segment-based word count (runs of CJK chars, not individual chars) |
| 6 | `json.JSONDecodeError` wastefully retried in `read_json` | Only retry `OSError`; raise `ArtifactError` immediately for `JSONDecodeError` |
| 7 | Missing test: gateway.py must not import jieba | Add import-invariant test |
| 8 | Missing test: `_count_words` for CJK segment counting | Add dedicated test class |

---

## Guardrails (from Metis Review)

- **G1**: Zero jieba imports in gateway.py — neither module-level nor lazy
- **G2**: `CheckResult` level semantics: `level="BLOCKER"` → `passed` must be `False`; advisory checks use `level="WARN"`
- **G3**: `proceeds()` return type is frozen: `tuple[bool, list[str]]`
- **G4**: `concrete_elements` field must NOT be added
- **G5**: `_count_sources()` and `_read_topic()` in cli.py keep `except Exception`
- **G6**: `run_all` return list: new checks appended to end, never inserted
- **G7**: No package management files (pyproject.toml, requirements.txt)
- **G8**: `json.JSONDecodeError` must not be retried — only `OSError` is transient

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest in .venv)
- **Automated tests**: TDD (RED → GREEN → REFACTOR per task)
- **Framework**: pytest

### QA Policy
Every task follows TDD. After all tasks, run full test suite:
```bash
.venv/bin/python -m pytest skills/info-collector/tests/ -v
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (foundation — no dependencies):
├── Task 1: Fix duplicate title in reporter.py [quick]
├── Task 2: Extract _STOP_WORDS to lib/constants.py [quick]
└── Task 3: Create lib/exceptions.py [quick]

Wave 2 (Batch 1 — core + docs, depends on Wave 1):
├── Task 4: Add duplicate-title WARN in check_analysis_schema (depends: 1) [quick]
├── Task 5: Add check_content_concreteness gate (depends: 2) [deep]
├── Task 6: Add check_methodology_depth gate (depends: 5) [quick]
├── Task 7: Add gateway jieba-import invariant test (depends: 2, 5) [quick]
├── Task 8: Update SKILL.md with concreteness rules (depends: 5, 6) [quick]
├── Task 9: Update GATES.md for Batch 1 (depends: 6) [quick]
└── Task 19: Write ADR 0012 (depends: 5, 6) [quick]

Wave 3 (Batch 2 — core + docs, depends on Wave 2):
├── Task 10: Add tier labels to references in reporter.py (depends: 1) [quick]
├── Task 11: Add check_source_tier_balance gate (depends: 5) [quick]
├── Task 12: Add check_recommendation_structure gate (depends: 5) [quick]
├── Task 13: Update SKILL.md with source qualifier + recommendation template (depends: 10, 11, 12) [quick]
├── Task 14: Update GATES.md for Batch 2 (depends: 11, 12) [quick]
└── Task 20: Write ADR 0013 (depends: 11, 12) [quick]

Wave 4 (Batch 3 — depends on Wave 1):
├── Task 15: Add file operation retry to utils.py (depends: 3) [quick]
├── Task 16: Update gateway.py error handling (depends: 3, 5, 11, 12) [quick]
├── Task 17: Update proceed.py error handling (depends: 3) [quick]
├── Task 18: Update cli.py main() to catch InfoCollectorError (depends: 3) [quick]
└── Task 21: Write ADR 0014 (depends: 3) [quick]

Wave FINAL (after ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay

Critical Path: Task 2 → Task 5 → Task 6 → Task 8 → F1-F4 → user okay
```

### Dependency Matrix

| Task | Blocked By | Blocks |
|------|-----------|--------|
| 1 | - | 4, 10 |
| 2 | - | 5, 7 |
| 3 | - | 15, 16, 17, 18 |
| 4 | 1 | 8 |
| 5 | 2 | 6, 7, 8, 11, 12, 16 |
| 6 | 5 | 8, 9 |
| 7 | 2, 5 | - |
| 8 | 5, 6 | - |
| 9 | 6 | - |
| 10 | 1 | 13 |
| 11 | 5 | 13, 14, 16 |
| 12 | 5 | 13, 14, 16 |
| 13 | 10, 11, 12 | - |
| 14 | 11, 12 | - |
| 15 | 3 | - |
| 16 | 3, 5, 11, 12 | - |
| 17 | 3 | - |
| 18 | 3 | - |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks → all `quick`
- **Wave 2**: 7 tasks → T4 `quick`, T5 `deep`, T6 `quick`, T7 `quick`, T8 `quick`, T9 `quick`, T19 `quick`
- **Wave 3**: 6 tasks → all `quick`
- **Wave 4**: 5 tasks → all `quick`
- **FINAL**: F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## Must Have

- [ ] Duplicate section title fix (3-layer defense: SKILL.md + gate WARN + reporter.py stripping)
- [ ] Concreteness gate (`check_content_concreteness`) with vague phrase, number, and name detection
- [ ] Methodology depth gate (`check_methodology_depth`) with min words + table presence
- [ ] Source tier labels in rendered report references (★ ratings)
- [ ] Source tier balance gate (`check_source_tier_balance`) — Tier 1+2 ratio check
- [ ] Recommendation structure gate (`check_recommendation_structure`) — table + "不推荐" for tech_selection/competitive_comparison
- [ ] Custom exception classes (InfoCollectorError, GateFailureError, ArtifactError)
- [ ] File operation retry in read_json/write_json (OSError only, not JSONDecodeError)
- [ ] `_STOP_WORDS` extracted to `lib/constants.py` (break jieba dependency chain)
- [ ] Zero jieba imports in gateway.py (invariant test)
- [ ] `run_all` returns 14 checks total
- [ ] All existing + new tests pass
- [ ] 3 ADRs written (0012, 0013, 0014) documenting spec deviations

## Must NOT Have

- [ ] jieba imports in gateway.py (neither module-level nor lazy)
- [ ] `BLOCKER + passed=True` semantic contradiction — advisory checks use `level="WARN"`
- [ ] `concrete_elements` field added to analysis.json schema
- [ ] Recommendation structure mixed into `check_section_coverage` — must be independent function
- [ ] `except (ArtifactError, FileNotFoundError, json.JSONDecodeError)` dead code — only catch `ArtifactError` where read_json is sole source
- [ ] `json.JSONDecodeError` retried in read_json/write_json — only `OSError` is transient
- [ ] Char-by-char CJK word count in concreteness checks — use segment-based counting
- [ ] Package management files (pyproject.toml, requirements.txt, setup.py)
- [ ] `_count_sources()` or `_read_topic()` exception handling narrowed (keep `except Exception`)
- [ ] `proceeds()` return type changed from `tuple[bool, list[str]]`

---

## Spec Deviations (Intentional Improvements Over Original Spec)

The plan intentionally deviates from the spec in 3 places. Each is an improvement that should be documented in the corresponding ADR.

| # | Spec Says | Plan Does Instead | Why |
|---|---|---|---|
| 1 | Word count: "count Chinese characters individually" (Section 1.2) | CJK segment-based counting (runs of CJK chars = 1 word each) | Char-by-char counting inflates denominator for Chinese, making the 10% vague phrase threshold unreachable for pure Chinese content |
| 2 | Recommendation structure check "in `check_section_coverage`" (Section 2.2) | Independent `check_recommendation_structure` function with `level="WARN"` | Single responsibility: `section_coverage` checks section existence, `recommendation_structure` checks content quality. Also avoids `BLOCKER + passed=True` semantic contradiction |
| 3 | Retry both `OSError` and `json.JSONDecodeError` in `read_json` (Section 3.2) | Only retry `OSError`; raise `ArtifactError` immediately for `json.JSONDecodeError` | `json.JSONDecodeError` is not transient — retrying wastes 1.5s on corrupted JSON |

---

## TODOs

- [ ] 1. Fix duplicate section title in reporter.py

  **What to do**:
  - Write failing test: `test_duplicate_title_stripped`, `test_subheading_preserved`, `test_non_matching_heading_preserved` in `test_reporter.py::TestSectionsToMarkdown`
  - Implement: In `sections_to_markdown`, strip `## {sec_title}` prefix from content if it matches the auto-rendered section heading
  - Keep `### ` and below sub-headings untouched
  - Keep non-matching `## ` headings (e.g., content starts with `## Different Title`)

  **Must NOT do**:
  - Do NOT strip `### ` or `# ` headings
  - Do NOT strip `## ` headings that don't match the section title
  - Do NOT modify the `## {sec_title}` auto-rendering line itself

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 4, 10
  - **Blocked By**: None

  **References**:
  - `skills/info-collector/scripts/reporter.py:137-139` — `sections_to_markdown` function: current rendering logic `parts.append(f"\n## {sec.get('title', ...)}\n")` + `parts.append(sec.get("content", ""))`
  - `skills/info-collector/tests/test_reporter.py` — existing test class `TestSectionsToMarkdown` to add new tests into

  **Acceptance Criteria**:
  - [ ] Test file updated: `skills/info-collector/tests/test_reporter.py`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_reporter.py::TestSectionsToMarkdown -v` → All PASS
  - [ ] Content starting with `## {section_title}` rendered with title appearing exactly once
  - [ ] `### ` sub-headings preserved
  - [ ] Non-matching `## ` headings preserved

  **QA Scenarios**:
  ```
  Scenario: Duplicate title stripped
    Tool: Bash (pytest)
    Preconditions: reporter.py has duplicate title bug
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_reporter.py::TestSectionsToMarkdown::test_duplicate_title_stripped -v
      2. Assert: test PASSES
    Expected Result: Title appears exactly once in rendered markdown
    Evidence: .omo/evidence/task-1-duplicate-title.pass

  Scenario: Sub-heading preserved
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_reporter.py::TestSectionsToMarkdown::test_subheading_preserved -v
      2. Assert: test PASSES
    Expected Result: ### headings are NOT stripped
    Evidence: .omo/evidence/task-1-subheading.pass
  ```

  **Commit**: YES
  - Message: `fix: strip duplicate section title in reporter.py`
  - Files: `skills/info-collector/scripts/reporter.py`, `skills/info-collector/tests/test_reporter.py`

- [ ] 2. Extract _STOP_WORDS to lib/constants.py

  **What to do**:
  - Create `skills/info-collector/scripts/lib/constants.py`
  - Move `_ENGLISH_STOP_WORDS` and `_CHINESE_STOP_WORDS` from `proceed.py` (lines 23-38) to `constants.py`
  - Update `proceed.py`: replace inline definitions with `from .lib.constants import _ENGLISH_STOP_WORDS, _CHINESE_STOP_WORDS`; keep `_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS` locally
  - This unblocks Task 5 (gateway.py can import stop words without pulling jieba)

  **Must NOT do**:
  - Do NOT move `_STOP_WORDS` (the union set) — keep it computed locally in `proceed.py`
  - Do NOT remove jieba from `proceed.py`
  - Do NOT modify any gateway.py code yet (Task 5 handles that)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 5, 7
  - **Blocked By**: None

  **References**:
  - `skills/info-collector/scripts/proceed.py:23-38` — `_ENGLISH_STOP_WORDS` and `_CHINESE_STOP_WORDS` definitions to extract
  - `skills/info-collector/scripts/proceed.py:43-51` — `_is_stop_word` uses `_STOP_WORDS` (union of both)
  - `skills/info-collector/scripts/lib/` — existing lib module pattern (utils.py, source_router.py, __init__.py)

  **Acceptance Criteria**:
  - [ ] New file: `skills/info-collector/scripts/lib/constants.py`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/ -v` → All PASS (no regressions)
  - [ ] `proceed.py` still imports and uses `_STOP_WORDS` correctly
  - [ ] `constants.py` exports `_ENGLISH_STOP_WORDS` and `_CHINESE_STOP_WORDS`

  **QA Scenarios**:
  ```
  Scenario: proceed.py still works after extraction
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_proceed.py -v
      2. Assert: All PASS
    Expected Result: No regressions in proceed module
    Evidence: .omo/evidence/task-2-proceed-regression.pass

  Scenario: constants.py importable standalone
    Tool: Bash (python -c)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -c "from scripts.lib.constants import _ENGLISH_STOP_WORDS, _CHINESE_STOP_WORDS; print(len(_ENGLISH_STOP_WORDS), len(_CHINESE_STOP_WORDS))"
      2. Assert: prints two positive numbers
    Expected Result: Both sets imported successfully
    Evidence: .omo/evidence/task-2-constants-import.pass
  ```

  **Commit**: YES
  - Message: `refactor: extract _STOP_WORDS to lib/constants.py`
  - Files: `skills/info-collector/scripts/lib/constants.py`, `skills/info-collector/scripts/proceed.py`

- [ ] 3. Create custom exception classes

  **What to do**:
  - Create `skills/info-collector/scripts/lib/exceptions.py` with 3 classes:
    - `InfoCollectorError(Exception)` — base
    - `GateFailureError(InfoCollectorError)` — with `phase` and `blockers` attributes
    - `ArtifactError(InfoCollectorError)` — with `path` and `reason` attributes
  - Create `skills/info-collector/tests/test_exceptions.py` with tests for all 3 classes
  - Do NOT integrate into existing modules yet (Tasks 15-18 handle that)

  **Must NOT do**:
  - Do NOT modify any existing file
  - Do NOT replace `sys.exit(1)` patterns
  - Do NOT add exceptions to gateway checks (CheckResult pattern stays)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 15, 16, 17, 18
  - **Blocked By**: None

  **References**:
  - `skills/info-collector/scripts/lib/` — existing lib module pattern
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 3.1 — exception class definitions

  **Acceptance Criteria**:
  - [ ] New file: `skills/info-collector/scripts/lib/exceptions.py`
  - [ ] New file: `skills/info-collector/tests/test_exceptions.py`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_exceptions.py -v` → All PASS
  - [ ] `GateFailureError("review", ["missing X"]).phase == "review"`
  - [ ] `ArtifactError("/path/to/file.json", "not found").path == "/path/to/file.json"`

  **QA Scenarios**:
  ```
  Scenario: Exception hierarchy correct
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_exceptions.py -v
      2. Assert: All PASS
    Expected Result: All exception classes work correctly
    Evidence: .omo/evidence/task-3-exceptions.pass

  Scenario: Exception attributes accessible
    Tool: Bash (python -c)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -c "from scripts.lib.exceptions import GateFailureError, ArtifactError; e1=GateFailureError('scope',['bad']); assert e1.phase=='scope'; e2=ArtifactError('/x','missing'); assert e2.reason=='missing'; print('OK')"
      2. Assert: prints "OK"
    Expected Result: All attributes accessible
    Evidence: .omo/evidence/task-3-exceptions-attrs.pass
  ```

  **Commit**: YES
  - Message: `feat: add custom exception classes`
  - Files: `skills/info-collector/scripts/lib/exceptions.py`, `skills/info-collector/tests/test_exceptions.py`

- [ ] 4. Add duplicate-title WARN in check_analysis_schema

  **What to do**:
  - Write failing test: `TestCheckAnalysisSchemaDuplicateTitle` in `test_gateway.py`
  - Add duplicate title detection to `check_analysis_schema`: if section content starts with `## `, collect WARN message
  - Return `CheckResult("analysis_schema", "WARN", True, "warning message")` when duplicates found — NOTE: use `level="WARN"` not `level="BLOCKER"` for advisory messages (fix from critical analysis)
  - Return `CheckResult("analysis_schema", "BLOCKER", False, ...)` for actual schema failures unchanged
  - Return `CheckResult("analysis_schema", "BLOCKER", True)` when all checks pass unchanged

  **Must NOT do**:
  - Do NOT use `level="BLOCKER"` for advisory WARN messages (the original plan's mistake)
  - Do NOT make duplicate title a BLOCKER — it's advisory only (reporter.py defensive stripping handles it)
  - Do NOT change the function's behavior for actual schema failures

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6 in same wave, but depends on Task 1)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 8
  - **Blocked By**: Task 1

  **References**:
  - `skills/info-collector/scripts/gateway.py:145-161` — `check_analysis_schema` function to modify
  - `skills/info-collector/tests/test_gateway.py` — existing gateway tests
  - Critical fix #2: `BLOCKER + passed=True` semantic contradiction — use `WARN` level instead

  **Acceptance Criteria**:
  - [ ] Test added: `TestCheckAnalysisSchemaDuplicateTitle` in `test_gateway.py`
  - [ ] Content starting with `## ` produces `level="WARN"` with message about duplicate heading (NOT `level="BLOCKER"`)
  - [ ] Actual schema failures still return `level="BLOCKER"` with `passed=False`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py -v` → All PASS

  **QA Scenarios**:
  ```
  Scenario: Duplicate heading produces WARN (not BLOCKER)
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py::TestCheckAnalysisSchemaDuplicateTitle -v
      2. Assert: All PASS
      3. Verify result.level == "WARN" (not "BLOCKER") for advisory case
    Expected Result: Advisory check uses WARN level, actual failures use BLOCKER
    Evidence: .omo/evidence/task-4-dup-title-warn.pass

  Scenario: Real schema failures still BLOCKER
    Tool: Bash (pytest)
    Steps:
      1. Run existing test for missing topic field
      2. Assert: result.level == "BLOCKER" and result.passed == False
    Expected Result: Schema failures unchanged
    Evidence: .omo/evidence/task-4-schema-blocker.pass
  ```

  **Commit**: YES
  - Message: `feat: add duplicate section title WARN in check_analysis_schema`
  - Files: `skills/info-collector/scripts/gateway.py`, `skills/info-collector/tests/test_gateway.py`

- [ ] 5. Add check_content_concreteness gate

  **What to do**:
  - Create `skills/info-collector/tests/test_content_concreteness.py` with test classes:
    - `TestVaguePhraseDetection`: no vague phrases, density exceeds threshold, density below threshold
    - `TestNumberAbsence`: tech_selection without numbers (BLOCKER), with numbers (pass), short section skip, year exclusion, version exclusion, other quantitative (WARN), exploratory (no check)
    - `TestNameAbsence`: no concrete names (BLOCKER), English name passes, backtick name passes, Chinese term passes
    - `TestMultipleIssues`: multiple sections with issues
    - `TestCountWords`: pure English, pure Chinese (CJK segments, NOT chars), mixed, empty, CJK punctuation only
  - Add concreteness constants to `gateway.py`: `_VAGUE_PHRASES_ZH`, `_VAGUE_PHRASES_EN`, `_VAGUE_DENSITY_THRESHOLD`, `_CONCRETENESS_STRICT_GOAL_TYPES`, `_YEAR_PATTERN`
  - Add `_count_words` helper to `gateway.py` using **CJK segment-based** counting:
    - English: split by whitespace
    - Chinese: count runs of consecutive CJK characters (each run = 1 word), NOT individual characters
    - Mixed: sum both
  - Add `_has_valid_number` helper: detect numbers excluding years (2000-2099), versions (v4.5), list items
  - Add `_has_concrete_name` helper: detect English proper nouns (mid-sentence capitalized), backtick identifiers, CJK technical terms (2+ char runs of CJK characters, filtered by `_CHINESE_STOP_WORDS` from `lib/constants.py`). **NO jieba import** — use simple CJK char-run heuristic instead.
  - Add `check_content_concreteness(workdir, goal_type)` function
  - Update `run_all` to append `check_content_concreteness(workdir, goal_type)` at end
  - Update `TestRunAll` assertion: 10 → 11 (Task 5 adds concreteness; Tasks 6/11/12 will increment to 12/13/14 respectively)

  **Must NOT do**:
  - Do NOT import jieba in gateway.py (Guardrail G1)
  - Do NOT import `_STOP_WORDS` from proceed.py (triggers jieba)
  - Do NOT import `_STOP_WORDS` directly — import `_CHINESE_STOP_WORDS` from `lib.constants` only
  - Do NOT add `concrete_elements` field (Guardrail G4)
  - Do NOT use char-by-char CJK word count (Critical fix #5)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
  - Reason: Multiple interrelated helper functions with nuanced CJK/English detection logic

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 6, 7, 8, 11, 12, 16
  - **Blocked By**: Task 2

  **References**:
  - `skills/info-collector/scripts/gateway.py:14-20` — `_QUANTITATIVE_GOAL_TYPES` set to use for goal_type branching
  - `skills/info-collector/scripts/gateway.py:369-381` — `run_all` function to append new check
  - `skills/info-collector/scripts/lib/constants.py` — `_CHINESE_STOP_WORDS` to import (NOT from proceed.py)
  - `skills/info-collector/scripts/proceed.py:43-51` — `_is_stop_word` logic to understand stop word filtering pattern
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 1.2 — concreteness check spec
  - Critical fix #1: no jieba in gateway.py
  - Critical fix #2: WARN level for advisory checks
  - Critical fix #5: CJK segment-based word counting

  **Acceptance Criteria**:
  - [ ] New file: `skills/info-collector/tests/test_content_concreteness.py`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_content_concreteness.py -v` → All PASS
  - [ ] `_count_words("性能优秀功能强大")` returns count based on CJK segments (NOT 6 per-char)
  - [ ] `_has_concrete_name("微服务架构...")` works without jieba (uses CJK char-run heuristic + stop words from constants.py)
  - [ ] `check_content_concreteness` uses `level="WARN"` for advisory cases, `level="BLOCKER"` only for tech_selection/competitive_comparison number/name absence
  - [ ] `run_all` includes `check_content_concreteness`

  **QA Scenarios**:
  ```
  Scenario: Concreteness gate catches vague tech_selection
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_content_concreteness.py -v
      2. Assert: All PASS
    Expected Result: Vague phrases detected, numbers/names absence flagged
    Evidence: .omo/evidence/task-5-concreteness.pass

  Scenario: No jieba import in gateway.py
    Tool: Bash (python -c)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -c "import scripts.gateway; import sys; assert 'jieba' not in sys.modules, 'jieba found in gateway imports'; print('OK')"
      2. Assert: prints "OK"
    Expected Result: gateway.py does NOT trigger jieba loading
    Evidence: .omo/evidence/task-5-no-jieba.pass

  Scenario: CJK segment word count correct
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_content_concreteness.py::TestCountWords -v
      2. Assert: All PASS
    Expected Result: Chinese text counted by segments, not individual chars
    Evidence: .omo/evidence/task-5-cjk-words.pass
  ```

  **Commit**: YES
  - Message: `feat: add check_content_concreteness gate (vague phrases, number/name absence)`
  - Files: `skills/info-collector/scripts/gateway.py`, `skills/info-collector/tests/test_content_concreteness.py`, `skills/info-collector/tests/test_gateway.py`

- [ ] 6. Add check_methodology_depth gate

  **What to do**:
  - Write failing test: `TestCheckMethodologyDepth` in `test_gateway.py`
  - Add `_METHODOLOGY_MIN_WORDS = 150` constant
  - Add `check_methodology_depth(workdir, goal_type)` using `_count_words` from Task 5
  - Checks: methodology section < 150 words → WARN; no Markdown table → WARN
  - Only applies to `_QUANTITATIVE_GOAL_TYPES`
  - Update `run_all` to append `check_methodology_depth(workdir, goal_type)`
  - Update `TestRunAll` count: 11 → 12 (Task 6 adds methodology_depth)

  **Must NOT do**:
  - Do NOT make methodology checks BLOCKER (spec says WARN only)
  - Do NOT duplicate `_count_words` — use the one added in Task 5

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 5 for `_count_words`)
  - **Parallel Group**: Wave 2 (sequential after Task 5)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Task 5

  **References**:
  - `skills/info-collector/scripts/gateway.py` — `_count_words` function added by Task 5
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 1.3 — methodology depth spec

  **Acceptance Criteria**:
  - [ ] Test added: `TestCheckMethodologyDepth` in `test_gateway.py`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py::TestCheckMethodologyDepth -v` → All PASS
  - [ ] Non-quantitative goal types skip the check
  - [ ] Methodology < 150 words → WARN with message about word count
  - [ ] Methodology with no table → WARN with message about missing table

  **QA Scenarios**:
  ```
  Scenario: Short methodology warns
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py::TestCheckMethodologyDepth::test_methodology_too_short_warns -v
      2. Assert: PASS, result.level == "WARN"
    Expected Result: Short methodology section flagged
    Evidence: .omo/evidence/task-6-methodology-short.pass
  ```

  **Commit**: YES
  - Message: `feat: add check_methodology_depth gate`
  - Files: `skills/info-collector/scripts/gateway.py`, `skills/info-collector/tests/test_gateway.py`

- [ ] 7. Add gateway jieba-import invariant test

  **What to do**:
  - Create `skills/info-collector/tests/test_gateway_import.py`
  - Add test that verifies `import scripts.gateway` does NOT trigger jieba module loading
  - **CRITICAL**: The test MUST run in a subprocess to avoid false positives from pytest's shared process. If `test_proceed.py` runs first and loads jieba, the invariant check would always pass.
  - Implementation: use `subprocess.run([sys.executable, "-c", "import scripts.gateway; import sys; assert 'jieba' not in sys.modules"]])` and check exit code == 0

  **Must NOT do**:
  - Do NOT modify any source files (pure test addition)
  - Do NOT check `'jieba' not in sys.modules` in the main pytest process (false positive risk)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 6 in Wave 2, after Task 5 is done)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 5

  **References**:
  - `skills/info-collector/scripts/gateway.py` — verify no jieba import
  - `skills/info-collector/scripts/lib/constants.py` — verify stop words come from here, not proceed.py
  - Guardrail G1: zero jieba imports in gateway.py

  **Acceptance Criteria**:
  - [ ] New file: `skills/info-collector/tests/test_gateway_import.py`
  - [ ] Test asserts `'jieba' not in sys.modules` after importing gateway
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway_import.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: jieba not loaded by gateway import
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway_import.py -v
      2. Assert: PASS
    Expected Result: jieba module not in sys.modules after gateway import
    Evidence: .omo/evidence/task-7-no-jieba.pass
  ```

  **Commit**: YES
  - Message: `test: add gateway jieba-import invariant`
  - Files: `skills/info-collector/tests/test_gateway_import.py`

- [ ] 8. Update SKILL.md with concreteness rules and title constraint

  **What to do**:
  - Add to 3a Step 2: "No top-level headings in content" — content must not start with `# ` or `## `, use `### ` and below
  - Add concreteness self-check to 3a Step 2: verify numbers with context, specific names, tables for comparisons, source annotations adjacent to claims
  - Add anti-patterns: content starting with `## Section Title`, pronouns instead of names, separating sources from claims
  - Add Step 3.5: "Run concreteness check" after assembling analysis.json — run `python scripts/cli.py gateway`, fix BLOCKERs before proceeding to 3b
  - Update Gate 4 check list in 3d section: add `content_concreteness`, `methodology_depth`

  **Must NOT do**:
  - Do NOT add `concrete_elements` field to analysis.json schema
  - Do NOT change existing valid workflow steps

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5, 6, 7, 9)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 6

  **References**:
  - `skills/info-collector/SKILL.md` — full skill definition to modify
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 1.4 — SKILL.md changes

  **Acceptance Criteria**:
  - [ ] SKILL.md contains "No top-level headings in content" rule
  - [ ] SKILL.md contains concreteness self-check list
  - [ ] SKILL.md contains Step 3.5 gateway check
  - [ ] SKILL.md Gate 4 list includes `content_concreteness`, `methodology_depth`

  **QA Scenarios**:
  ```
  Scenario: SKILL.md updated correctly
    Tool: Bash (grep)
    Steps:
      1. grep -c "concreteness" skills/info-collector/SKILL.md — should be > 0
      2. grep -c "content_concreteness" skills/info-collector/SKILL.md — should be > 0
      3. grep -c "methodology_depth" skills/info-collector/SKILL.md — should be > 0
    Expected Result: All new terms present in SKILL.md
    Evidence: .omo/evidence/task-8-skillmd.pass
  ```

  **Commit**: YES
  - Message: `docs: add concreteness rules and title constraint to SKILL.md`
  - Files: `skills/info-collector/SKILL.md`

- [ ] 9. Update GATES.md reference for Batch 1

  **What to do**:
  - Update Gate 4 check list: `10 checks` → `12 checks` + add `content_concreteness`, `methodology_depth`

  **Must NOT do**:
  - Do NOT update to final 14 count yet (Batch 2 adds more)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5, 6, 7, 8)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Task 6

  **References**:
  - `skills/info-collector/references/GATES.md:26-29` — Gate 4 check list

  **Acceptance Criteria**:
  - [ ] GATES.md Gate 4 lists 12 checks including `content_concreteness`, `methodology_depth`

  **QA Scenarios**:
  ```
  Scenario: GATES.md updated
    Tool: Bash (grep)
    Steps:
      1. grep "content_concreteness" skills/info-collector/references/GATES.md — should match
    Expected Result: New check names present
    Evidence: .omo/evidence/task-9-gatesmd.pass
  ```

  **Commit**: YES
  - Message: `docs: update GATES.md with Batch 1 checks`
  - Files: `skills/info-collector/references/GATES.md`

- [ ] 10. Add tier labels to references in reporter.py

  **What to do**:
  - Write failing test: `TestRenderReferencesWithTier` in `test_reporter.py`
  - Add `_TIER_LABELS` dict mapping tier 1-4 to star ratings + tier names
  - Modify `_render_references`: append tier label to each reference line
  - Handle missing `source_tier` gracefully (no label shown)

  **Must NOT do**:
  - Do NOT change reference format for entries without tier info
  - Do NOT add tier labels to claim citations in body text (that's SKILL.md guidance, not code)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 11, 12, 13, 14)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Task 1

  **References**:
  - `skills/info-collector/scripts/reporter.py:45-59` — `_render_references` function
  - `skills/info-collector/config.json:2-39` — source tier definitions for label names

  **Acceptance Criteria**:
  - [ ] Tier labels appear in rendered references: `★★★☆ Tier 1`, `★★☆☆ Tier 2`, etc.
  - [ ] Entries without `source_tier` show no label
  - [ ] Existing tests unaffected

  **QA Scenarios**:
  ```
  Scenario: Tier labels rendered correctly
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_reporter.py::TestRenderReferencesWithTier -v
      2. Assert: All PASS
    Expected Result: Tier labels in reference output
    Evidence: .omo/evidence/task-10-tier-labels.pass
  ```

  **Commit**: YES
  - Message: `feat: add source tier labels to references in rendered reports`
  - Files: `skills/info-collector/scripts/reporter.py`, `skills/info-collector/tests/test_reporter.py`

- [ ] 11. Add check_source_tier_balance gate

  **What to do**:
  - Write failing test: `TestCheckSourceTierBalance` in `test_gateway.py`
  - Add `_TIER_BALANCE_THRESHOLD = 0.30` constant
  - Add `check_source_tier_balance(workdir, goal_type)`: WARN if Tier 1+2 ratio < 30% among referenced URLs for quantitative goal types
  - Skip for non-quantitative goal types
  - Update `run_all` to append at end
  - Update `TestRunAll` count: 12 → 13 (Task 11 adds source_tier_balance)

  **Must NOT do**:
  - Do NOT make this a BLOCKER (spec says WARN)
  - Do NOT count unreferenced sources (only URLs referenced by claims)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 12, 13, 14)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 13, 14, 16
  - **Blocked By**: Task 5

  **References**:
  - `skills/info-collector/scripts/gateway.py:14-20` — `_QUANTITATIVE_GOAL_TYPES`
  - `skills/info-collector/scripts/lib/utils.py:9-19` — `normalize_url` for URL comparison
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 2.1 — tier balance spec

  **Acceptance Criteria**:
  - [ ] Good balance (Tier 1+2 > 30%) → passes
  - [ ] Poor balance (all Tier 3-4) → WARN with message
  - [ ] Non-quantitative → skip

  **QA Scenarios**:
  ```
  Scenario: Tier balance check works
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py::TestCheckSourceTierBalance -v
      2. Assert: All PASS
    Expected Result: Balance check correctly flags low Tier 1+2 ratios
    Evidence: .omo/evidence/task-11-tier-balance.pass
  ```

  **Commit**: YES
  - Message: `feat: add check_source_tier_balance gate`
  - Files: `skills/info-collector/scripts/gateway.py`, `skills/info-collector/tests/test_gateway.py`

- [ ] 12. Add check_recommendation_structure gate

  **What to do**:
  - Write failing test: `TestCheckRecommendationStructure` in `test_gateway.py` (NEW test class, NOT in TestCheckSectionCoverage)
  - Add `check_recommendation_structure(workdir, goal_type)` as an independent function
  - Only applies to `tech_selection` and `competitive_comparison`
  - Checks: recommendation section has Markdown table + "不推荐"/"not recommended"
  - Returns `CheckResult("recommendation_structure", "WARN", True/False, message)` — NOTE: `level="WARN"` (critical fix #3)
  - Skip if no recommendation section (not an error — section_coverage handles existence)
  - Skip for other goal types
  - Update `run_all` to append at end
  - Update `TestRunAll` count to 14 (final count)

  **Must NOT do**:
  - Do NOT mix this into `check_section_coverage` (critical fix #3)
  - Do NOT use `level="BLOCKER"` (this is advisory, use `level="WARN"`)
  - Do NOT flag missing recommendation section (that's `check_section_coverage`'s job)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11, 13, 14)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 13, 14, 16
  - **Blocked By**: Task 5

  **References**:
  - `skills/info-collector/scripts/gateway.py:82-126` — `check_section_coverage` (do NOT modify this)
  - `skills/info-collector/scripts/gateway.py:82-89` — `_REQUIRED_SECTION_IDS` for understanding tech_selection section requirements
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 2.2 — recommendation structure spec

  **Acceptance Criteria**:
  - [ ] New test class: `TestCheckRecommendationStructure` in `test_gateway.py`
  - [ ] tech_selection recommendation without table → `level="WARN"` (NOT `level="BLOCKER"`)
  - [ ] tech_selection recommendation without "不推荐" → `level="WARN"`
  - [ ] recommendation with proper structure → passes
  - [ ] exploratory goal type → skip
  - [ ] No recommendation section → skip (not flagged as error)
  - [ ] `run_all` returns 14 checks total
  - [ ] `TestRunAll` asserts `len(results) == 14`

  **QA Scenarios**:
  ```
  Scenario: Recommendation structure check independent
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py::TestCheckRecommendationStructure -v
      2. Assert: All PASS
    Expected Result: Independent function with WARN level
    Evidence: .omo/evidence/task-12-rec-structure.pass
  ```

  **Commit**: YES
  - Message: `feat: add check_recommendation_structure gate`
  - Files: `skills/info-collector/scripts/gateway.py`, `skills/info-collector/tests/test_gateway.py`

- [ ] 13. Update SKILL.md with source qualifier and recommendation template

  **What to do**:
  - Add to 3b section: "Tier-aware source citations" — Tier 3-4 sources need qualifiers in body text
  - Add recommendation structure template for `tech_selection`/`competitive_comparison`: 推荐矩阵 table, 关键决策因素 list, 不推荐场景 section

  **Must NOT do**:
  - Do NOT change the analysis.json schema
  - Do NOT add code changes (pure documentation update)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11, 12, 14)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Tasks 10, 11, 12

  **References**:
  - `skills/info-collector/SKILL.md` — existing 3b section
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 2.1-2.2 — SKILL.md changes

  **Acceptance Criteria**:
  - [ ] SKILL.md contains tier-aware source citations guidance
  - [ ] SKILL.md contains recommendation structure template with 推荐矩阵, 不推荐场景

  **QA Scenarios**:
  ```
  Scenario: SKILL.md updated for Batch 2
    Tool: Bash (grep)
    Steps:
      1. grep "Tier-aware" skills/info-collector/SKILL.md — should match
      2. grep "不推荐场景" skills/info-collector/SKILL.md — should match
    Expected Result: New guidance present
    Evidence: .omo/evidence/task-13-skillmd-b2.pass
  ```

  **Commit**: YES
  - Message: `docs: add source qualifier and recommendation template to SKILL.md`
  - Files: `skills/info-collector/SKILL.md`

- [ ] 14. Update GATES.md for Batch 2

  **What to do**:
  - Update Gate 4 check list: `12 checks` → `14 checks` + add `source_tier_balance`, `recommendation_structure`

  **Must NOT do**:
  - Do NOT change Gate 1-3 content

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10, 11, 12, 13)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Tasks 11, 12

  **References**:
  - `skills/info-collector/references/GATES.md:26-29` — Gate 4 section

  **Acceptance Criteria**:
  - [ ] GATES.md Gate 4 lists 14 checks including `source_tier_balance`, `recommendation_structure`

  **QA Scenarios**:
  ```
  Scenario: GATES.md updated for Batch 2
    Tool: Bash (grep)
    Steps:
      1. grep "source_tier_balance" skills/info-collector/references/GATES.md — should match
      2. grep "recommendation_structure" skills/info-collector/references/GATES.md — should match
    Expected Result: New check names present
    Evidence: .omo/evidence/task-14-gatesmd-b2.pass
  ```

  **Commit**: YES
  - Message: `docs: update GATES.md for Batch 2`
  - Files: `skills/info-collector/references/GATES.md`

- [ ] 15. Add file operation retry to utils.py

  **What to do**:
  - Write failing test: `TestReadJsonRetry`, `TestWriteJsonRetry` in `test_utils.py`
  - Update `read_json`: add `retries=2, delay=0.5` params; retry on `OSError` only; raise `ArtifactError` on final failure; raise `ArtifactError` immediately for `json.JSONDecodeError` (NOT retried — Guardrail G8)
  - Update `write_json`: add `retries=2, delay=0.5` params; retry on `OSError` only; raise `ArtifactError` on final failure
  - Add `from .exceptions import ArtifactError` import
  - Add `import time` for delay

  **Must NOT do**:
  - Do NOT retry `json.JSONDecodeError` — it's not transient (Guardrail G8 / Metis E7)
  - Do NOT add exponential backoff — local filesystem, predictable timing
  - Do NOT change function signatures for callers (default params maintain backward compatibility)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 16, 17, 18)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `skills/info-collector/scripts/lib/utils.py:22-30` — `read_json` and `write_json` to modify
  - `skills/info-collector/scripts/lib/exceptions.py` — `ArtifactError` class from Task 3
  - `docs/superpowers/specs/2026-06-15-info-collector-improvement-design.md` Section 3.2 — retry spec
  - Guardrail G8: `json.JSONDecodeError` must not be retried
  - Metis E7: retrying JSONDecodeError wastes 1.5s on non-transient error

  **Acceptance Criteria**:
  - [ ] `read_json` retries on `OSError`, raises `ArtifactError` after exhausting retries
  - [ ] `read_json` raises `ArtifactError` immediately for `json.JSONDecodeError` (no retry)
  - [ ] `write_json` retries on `OSError`, raises `ArtifactError` after exhausting retries
  - [ ] Default params maintain backward compatibility: `read_json(path)` still works
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_utils.py -v` → All PASS

  **QA Scenarios**:
  ```
  Scenario: Retry recovers from transient OSError
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_utils.py::TestReadJsonRetry::test_retries_on_oserror -v
      2. Assert: PASS (recovered after 1 transient failure)
    Expected Result: read_json succeeds after retry
    Evidence: .omo/evidence/task-15-retry-recover.pass

  Scenario: ArtifactError raised after retries exhausted
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_utils.py::TestReadJsonRetry::test_raises_artifact_error_after_retries -v
      2. Assert: PASS (ArtifactError raised)
    Expected Result: Final failure raises ArtifactError
    Evidence: .omo/evidence/task-15-retry-exhaust.pass
  ```

  **Commit**: YES
  - Message: `feat: add file operation retry to utils.py`
  - Files: `skills/info-collector/scripts/lib/utils.py`, `skills/info-collector/tests/test_utils.py`

- [ ] 16. Update gateway.py error handling

  **What to do**:
  - Add `from .lib.exceptions import ArtifactError` import
  - For each `except Exception as e` block that wraps `read_json` call(s) (where `read_json` is the sole exception source, even if called multiple times):
    - Change to `except ArtifactError as e`
  - For blocks with complex post-read logic beyond `read_json` calls:
    - Keep `except Exception as e` as defensive fallback per AGENTS.md "错误可见" principle
  - Specifically for `check_source_tier_balance` (reads 2 files + cross-references URLs): keep `except Exception`
  - List of changes:
    - `check_url_traceability`: `except Exception` → `except ArtifactError` (calls read_json twice, but both are sole exception sources)
    - `check_section_coverage`: `except Exception` → `except ArtifactError`
    - `check_analysis_schema`: `except Exception` → `except ArtifactError`
    - `check_quality_heuristics`: `except Exception` → `except ArtifactError`
    - `check_precision_inflation`: `except Exception` → `except ArtifactError`
    - `check_claim_metadata`: `except Exception` → `except ArtifactError`
    - `check_claim_verified`: `except Exception` → `except ArtifactError`
    - `check_source_metadata`: `except Exception` → `except ArtifactError`
    - `check_metric_type_homogeneity`: `except Exception` → `except ArtifactError`
    - `check_content_concreteness`: `except Exception` → `except ArtifactError`
    - `check_methodology_depth`: `except Exception` → `except ArtifactError`
    - `check_source_tier_balance`: KEEP `except Exception` (reads 2 files + cross-references)

  **Must NOT do**:
  - Do NOT catch `(ArtifactError, FileNotFoundError, json.JSONDecodeError)` — the latter two are dead code after `read_json` change (critical fix #4)
  - Do NOT narrow `check_source_tier_balance`'s catch — it has complex logic beyond single `read_json`
  - Do NOT change any CheckResult patterns

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15, 17, 18)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Tasks 3, 5, 11, 12

  **References**:
  - `skills/info-collector/scripts/gateway.py` — all `except Exception` blocks
  - `skills/info-collector/scripts/lib/exceptions.py` — `ArtifactError` class
  - Critical fix #4: no dead code in exception handlers

  **Acceptance Criteria**:
  - [ ] Single-read_json handlers use `except ArtifactError as e`
  - [ ] Complex handlers keep `except Exception as e`
  - [ ] New test: `TestArtifactErrorHandling` in `test_gateway.py` — monkeypatch `read_json` to raise `ArtifactError`, verify it's caught and converted to appropriate `CheckResult`
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_gateway.py -v` → All PASS
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/ -v` → All PASS

  **QA Scenarios**:
  ```
  Scenario: Full test suite passes after error handling update
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/ -v
      2. Assert: All PASS
    Expected Result: No regressions from error handling changes
    Evidence: .omo/evidence/task-16-gateway-errors.pass
  ```

  **Commit**: YES
  - Message: `refactor: narrow exception handling in gateway.py`
  - Files: `skills/info-collector/scripts/gateway.py`

- [ ] 17. Update proceed.py error handling

  **What to do**:
  - Add `from .lib.exceptions import ArtifactError` import
  - `_check_scope_schema`: `except Exception` → `except ArtifactError`
  - `_check_search_gate`: `except Exception` → `except ArtifactError`
  - `_get_goal_type`: `except Exception` → `except ArtifactError` (note: returns "other" on error, consistent with current behavior)

  **Must NOT do**:
  - Do NOT change `proceeds()` return type (Guardrail G3)
  - Do NOT raise exceptions from `proceeds()` — it returns `tuple[bool, list[str]]`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15, 17, 18)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `skills/info-collector/scripts/proceed.py:97-131` — `_check_scope_schema`
  - `skills/info-collector/scripts/proceed.py:133-190` — `_check_search_gate`
  - `skills/info-collector/scripts/proceed.py:227-232` — `_get_goal_type`

  **Acceptance Criteria**:
  - [ ] Error handlers narrowed to `ArtifactError`
  - [ ] New test: `TestProceedArtifactErrorHandling` in `test_proceed.py` — monkeypatch `read_json` to raise `ArtifactError`, verify `_check_scope_schema` and `_check_search_gate` handle it correctly
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_proceed.py -v` → All PASS

  **QA Scenarios**:
  ```
  Scenario: proceed tests pass after error handling update
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_proceed.py -v
      2. Assert: All PASS
    Expected Result: No regressions
    Evidence: .omo/evidence/task-17-proceed-errors.pass
  ```

  **Commit**: YES
  - Message: `refactor: narrow exception handling in proceed.py`
  - Files: `skills/info-collector/scripts/proceed.py`

- [ ] 18. Update cli.py main() to catch InfoCollectorError

  **What to do**:
  - Add `from .lib.exceptions import InfoCollectorError` import
  - Wrap `args.func(args)` in try/except: catch `InfoCollectorError`, print to stderr, `sys.exit(1)`
  - Write test: verify `main()` catches `InfoCollectorError` and exits with code 1

  **Must NOT do**:
  - Do NOT replace existing `sys.exit(1)` calls in subcommands with exceptions
  - Do NOT change `proceeds()` to raise `GateFailureError` (Guardrail G3)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15, 16, 17)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `skills/info-collector/scripts/cli.py:161-162` — `main()` dispatch to wrap
  - `skills/info-collector/scripts/lib/exceptions.py` — `InfoCollectorError` class
  - `skills/info-collector/tests/test_cli.py` — existing CLI tests

  **Acceptance Criteria**:
  - [ ] `InfoCollectorError` caught in `main()`, prints to stderr, exits 1
  - [ ] `cd skills/info-collector && .venv/bin/python -m pytest tests/test_cli.py -v` → All PASS

  **QA Scenarios**:
  ```
  Scenario: InfoCollectorError caught by main
    Tool: Bash (pytest)
    Steps:
      1. Run: cd skills/info-collector && .venv/bin/python -m pytest tests/test_cli.py -v
      2. Assert: All PASS
    Expected Result: Exception caught gracefully
    Evidence: .omo/evidence/task-18-cli-error.pass
  ```

  **Commit**: YES
  - Message: `feat: catch InfoCollectorError in cli.py main()`
  - Files: `skills/info-collector/scripts/cli.py`, `skills/info-collector/tests/test_cli.py`

- [ ] 19. Write ADR 0012: Concreteness gate and CJK word counting

  **What to do**:
  - Create `docs/adr/0012-concreteness-gate-and-cjk-word-counting.md`
  - Document the decision to add `check_content_concreteness` and `check_methodology_depth` gates
  - Document the spec deviation: CJK segment-based word counting instead of char-by-char (Spec Deviation #1)
  - Document why: char-by-char inflates denominator for Chinese, making 10% threshold unreachable

  **Must NOT do**:
  - Do NOT modify any source files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 6

  **References**:
  - `docs/adr/` — existing ADR directory with 0011-ADR naming convention
  - Spec Deviation #1 in plan header

  **Acceptance Criteria**:
  - [ ] New file: `docs/adr/0012-concreteness-gate-and-cjk-word-counting.md`
  - [ ] ADR documents the word counting decision and rationale

  **QA Scenarios**:
  ```
  Scenario: ADR file exists
    Tool: Bash (ls)
    Steps:
      1. ls docs/adr/0012-concreteness-gate-and-cjk-word-counting.md
      2. Assert: file exists
    Expected Result: ADR created
    Evidence: .omo/evidence/task-19-adr.pass
  ```

  **Commit**: YES
  - Message: `docs: add ADR 0012 concreteness gate and CJK word counting`
  - Files: `docs/adr/0012-concreteness-gate-and-cjk-word-counting.md`

- [ ] 20. Write ADR 0013: Source credibility labeling and recommendation structure

  **What to do**:
  - Create `docs/adr/0013-source-credibility-and-recommendation-structure.md`
  - Document the decision to add tier labels and `check_source_tier_balance` gate
  - Document the spec deviation: independent `check_recommendation_structure` instead of embedding in `check_section_coverage` (Spec Deviation #2)
  - Document why: single responsibility + avoid `BLOCKER + passed=True` semantic contradiction

  **Must NOT do**:
  - Do NOT modify any source files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 14)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Tasks 11, 12

  **References**:
  - `docs/adr/` — existing ADR directory
  - Spec Deviation #2 in plan header

  **Acceptance Criteria**:
  - [ ] New file: `docs/adr/0013-source-credibility-and-recommendation-structure.md`
  - [ ] ADR documents the recommendation structure independence decision

  **QA Scenarios**:
  ```
  Scenario: ADR file exists
    Tool: Bash (ls)
    Steps:
      1. ls docs/adr/0013-source-credibility-and-recommendation-structure.md
      2. Assert: file exists
    Expected Result: ADR created
    Evidence: .omo/evidence/task-20-adr.pass
  ```

  **Commit**: YES
  - Message: `docs: add ADR 0013 source credibility and recommendation structure`
  - Files: `docs/adr/0013-source-credibility-and-recommendation-structure.md`

- [ ] 21. Write ADR 0014: Custom exceptions and file operation retry

  **What to do**:
  - Create `docs/adr/0014-custom-exceptions-and-file-operation-retry.md`
  - Document the decision to add custom exception classes and retry logic
  - Document the spec deviation: only retry `OSError`, not `json.JSONDecodeError` (Spec Deviation #3)
  - Document why: `json.JSONDecodeError` is not transient, retrying wastes 1.5s

  **Must NOT do**:
  - Do NOT modify any source files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15, 16, 17, 18)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `docs/adr/` — existing ADR directory
  - Spec Deviation #3 in plan header

  **Acceptance Criteria**:
  - [ ] New file: `docs/adr/0014-custom-exceptions-and-file-operation-retry.md`
  - [ ] ADR documents the retry scope decision

  **QA Scenarios**:
  ```
  Scenario: ADR file exists
    Tool: Bash (ls)
    Steps:
      1. ls docs/adr/0014-custom-exceptions-and-file-operation-retry.md
      2. Assert: file exists
    Expected Result: ADR created
    Evidence: .omo/evidence/task-21-adr.pass
  ```

  **Commit**: YES
  - Message: `docs: add ADR 0014 custom exceptions and file operation retry`
  - Files: `docs/adr/0014-custom-exceptions-and-file-operation-retry.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `cd skills/info-collector && .venv/bin/python -m pytest tests/ -v`. Review all changed files for: type suppression, empty catches, debug logging, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run every `proceed` gate transition with valid/invalid inputs. Verify `gateway` command output format. Verify `report` command generates correct Markdown. Verify `source` command returns expected tiers. Save to `.omo/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Task | Message | Files |
|------|---------|-------|
| 1 | `fix: strip duplicate section title in reporter.py` | reporter.py, test_reporter.py |
| 2 | `refactor: extract _STOP_WORDS to lib/constants.py` | constants.py, proceed.py |
| 3 | `feat: add custom exception classes` | exceptions.py, test_exceptions.py |
| 4 | `feat: add duplicate section title WARN in check_analysis_schema` | gateway.py, test_gateway.py |
| 5 | `feat: add check_content_concreteness gate` | gateway.py, test_content_concreteness.py, test_gateway.py |
| 6 | `feat: add check_methodology_depth gate` | gateway.py, test_gateway.py |
| 7 | `test: add gateway jieba-import invariant` | test_gateway_import.py |
| 8 | `docs: add concreteness rules and title constraint to SKILL.md` | SKILL.md |
| 9 | `docs: update GATES.md with Batch 1 checks` | GATES.md |
| 10 | `feat: add source tier labels to references in rendered reports` | reporter.py, test_reporter.py |
| 11 | `feat: add check_source_tier_balance gate` | gateway.py, test_gateway.py |
| 12 | `feat: add check_recommendation_structure gate` | gateway.py, test_gateway.py |
| 13 | `docs: add source qualifier and recommendation template to SKILL.md` | SKILL.md |
| 14 | `docs: update GATES.md for Batch 2` | GATES.md |
| 15 | `feat: add file operation retry to utils.py` | utils.py, test_utils.py |
| 16 | `refactor: narrow exception handling in gateway.py` | gateway.py |
| 17 | `refactor: narrow exception handling in proceed.py` | proceed.py |
| 18 | `feat: catch InfoCollectorError in cli.py main()` | cli.py, test_cli.py |
| 19 | `docs: add ADR 0012 concreteness gate and CJK word counting` | 0012-concreteness-gate-and-cjk-word-counting.md |
| 20 | `docs: add ADR 0013 source credibility and recommendation structure` | 0013-source-credibility-and-recommendation-structure.md |
| 21 | `docs: add ADR 0014 custom exceptions and file operation retry` | 0014-custom-exceptions-and-file-operation-retry.md |

---

## Success Criteria

### Verification Commands
```bash
cd skills/info-collector && .venv/bin/python -m pytest tests/ -v  # All PASS, 0 failures
.venv/bin/python -c "import scripts.gateway; import sys; assert 'jieba' not in sys.modules"  # No jieba loaded
.venv/bin/python -m pytest tests/test_gateway.py -k "run_all" -v  # 14 checks in run_all
```

### Final Checklist
- [ ] All "Must Have" present (concreteness gate, methodology depth, tier labels, tier balance, recommendation structure, custom exceptions, retry, 3 ADRs)
- [ ] All "Must NOT Have" absent (jieba in gateway.py, BLOCKER+passed=True, concrete_elements field, package management files)
- [ ] All tests pass
- [ ] `run_all` returns 14 checks

---

## Review Trail

| Phase | Agent | Result | Date | Notes |
|---|---|---|---|---|
| Gap Analysis | Metis | 6 categories, 8 guardrails, 8 edge cases | 2026-06-16 | Identified spec deviations, ADR gap, jieba-invariant false-positive risk |
| Interview Check | Oracle Phase 1 | GO (5/5) | 2026-06-16 | Core objective unambiguous, scope explicit, TDD decided, no outstanding questions |
| Plan Compliance | Oracle Phase 2 | NO-GO → GO (after fixes) | 2026-06-16 | Fixed: missing Must Have/Must NOT Have sections, waves below 3-task minimum (merged) |
| High Accuracy | Momus | OKAY | 2026-06-16 | All file references verified, line numbers match, plan structure confirmed |
| Readiness Check | Oracle Phase 3 | GO (4.5/5) | 2026-06-16 | Minor doc clarity fixes applied (run_all count progression, Task 16 parallelization typo) |
| Full Audit | Oracle (user-requested) | APPROVE_WITH_CONDITIONS → all 6 conditions fixed | 2026-06-16 | Conditions: ADRs added (T19-21), spec deviations documented, url_traceability principle updated, import json removed, jieba-invariant subprocess, exception narrowing tests added |

**Plan Status: FROZEN** — All review conditions met. No further edits unless user explicitly requests.
