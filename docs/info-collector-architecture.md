# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~1,160 lines (6 modules) |
| Tests | ~2,270 lines (8 files, 151 test functions in 6 test files) |
| Config/docs | config.json + SKILL.md + 2 reference docs |
| Runtime pip deps | `jieba` (ADR 0001 exception to stdlib-only rule) |
| HTTP deps | None — search done externally by AI via exa/playwright |

---

## 2. File Listing

### Source Files

| # | Path | Purpose |
|---|---|---|
| 1 | `SKILL.md` | Skill definition: 276 lines, 5-phase workflow, CLI reference, quality values |
| 2 | `config.json` | 4-tier source config + 10 goal-type routes + output settings |
| 3 | `scripts/__init__.py` | Empty (package marker) |
| 4 | `scripts/cli.py` | CLI entry: 5 subcommands, argparse, `sys.exit` on gate fail |
| 5 | `scripts/gateway.py` | Quality gate engine: 10 checks, `CheckResult` dataclass |
| 6 | `scripts/proceed.py` | Phase transition gates, phase detection, jieba tokenization (silences jieba logging via `setLogLevel`) |
| 7 | `scripts/reporter.py` | Markdown report generator: YAML front matter, i18n, references |
| 8 | `scripts/lib/__init__.py` | Empty |
| 9 | `scripts/lib/utils.py` | `normalize_url`, `read_json`, `write_json`, `_find_project_root`, `ensure_dir` |
| 10 | `scripts/lib/source_router.py` | Pure-function routing: `get_route`, `recommend_sources`, defaults |
| 11 | `references/GATES.md` | 5-gate system reference |
| 12 | `references/REVIEW_PROMPT.md` | Review sub-agent prompt template |

### Test Files

| # | Path | Lines | Coverage |
|---|---|---|---|
| 1 | `tests/conftest.py` | 4 | Adds skill dir to `sys.path` |
| 2 | `tests/__init__.py` | 0 | Empty |
| 3 | `tests/test_cli.py` | 254 | 5 command handlers + project root detection |
| 4 | `tests/test_gateway.py` | 861 | All 10 gate checks, edge cases |
| 5 | `tests/test_proceed.py` | 432 | Phase detection + gate routing + per-direction min sources |
| 6 | `tests/test_reporter.py` | 506 | Report pipeline + i18n + test conditions + reference numbering |
| 7 | `tests/test_source_router.py` | 160 | Router functions + integration against real config.json |
| 8 | `tests/test_utils.py` | 53 | URL normalization + JSON I/O + directory creation |

---

## 3. Data Flow

```
User input (topic, goal_type, depth, audience)
       |
       v
+-------------------------------------+
|  Phase 1: Scoping (AI interview)    |
|  Output: scope.json                 |
|    - topic, goal_type, depth        |
|    - audience, scope_description    |
|    - search_directions[]            |
|    - report_language (optional)     |
+---------------+---------------------+
                |
                v
    proceed --from scope --to search   <-- Gate 1: scope.json schema validation
                |                         |-- Field existence checks
                |                         |-- Enum validation (goal_type, depth, audience)
                |                         +-- Generate search_plan.json
                v
+-------------------------------------+
|  Phase 2: Search -> Collect -> Filter|
|  Output: collected.json              |
|    - url, title, snippet            |
|    - source_tier, fetched_content   |
|  Search via exa/playwright (external)|
|  Routed by config.json tier paths   |
+---------------+---------------------+
                |
                v
    proceed --from search --to analysis  <-- Gate 2: search quality
                |                           |-- topic_coverage (BLOCKER, jieba match)
                |                           |-- tier_coverage (WARN)
                |                           |-- per_direction_min_sources (WARN)
                |                           +-- min_sources (WARN)
                v
+-------------------------------------+
|  Phase 3a: Build analysis.json       |
|    - Plan sections                   |
|    - Write content per section       |
|    - Extract claims with metadata    |
|  Schema:                             |
|    topic, goal_type, sections[]      |
|      +- id, title, content           |
|      +- claims[]                     |
|           +- text, source_urls[]     |
|           +- evidence_type           |
|           +- confidence, precision   |
|           +- metric_type (optional)  |
|           +- source_metadata (opt)   |
|           +- verified (bool)         |
+---------------+---------------------+
                |
                v
  Phase 3b: Draft (rendered analysis.json)
                |
                v
    proceed --from draft --to review   <-- Gate 3: draft completeness
                |
                v
+-------------------------------------+
|  Phase 3c: Review (optional sub-agent)|
|  Review output: review_report.md     |
|  Updates analysis.json verified field|
+---------------+---------------------+
                |
                v
    proceed --from review --to final   <-- Gate 4: full 10-check gateway
                |
                v
  Phase 3d: Final report generation
  cli.py report --quality ...          <-- reporter.py generates Markdown
                |
                v
  <output_dir>/<topic>_v<N>.md
  (YAML front matter + numbered refs + appendix)
                |
                v
    proceed --from final --to cleanup  <-- Gate 5: always passes
                |
                v
+-------------------------------------+
|  Phase 4: Cleanup                    |
|  cli.py clean -> deletes .workdir/  |
+-------------------------------------+
```

### Phase Detection (`detect_current_phase`)

| Condition | Phase |
|---|---|
| `.workdir` doesn't exist OR `.workdir` exists but no `scope.json` | `pre_scope` |
| `scope.json` exists AND `collected.json` doesn't | `post_scope` |
| `collected.json` exists AND `analysis.json` doesn't | `post_search` |
| `analysis.json` exists AND `draft/report.md` doesn't | `post_analysis` |
| `draft/report.md` exists AND `review_report.md` doesn't | `post_draft` |
| `review_report.md` exists | `post_review` |

### Valid Transitions

```
scope -> search -> analysis ~~(ungated)~~> draft -> review -> final -> cleanup
```

---

## 4. API Surface — Function Reference

### 4.1 `scripts/cli.py` — CLI Entry Point (166 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone 10-check gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > hardcoded `"zh"` |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `_detect_quality` | `() -> str` | `"passed"` if review_report.md exists, else `"unreviewed"` |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_read_topic` | `(scope_path: Path) -> str` | Read topic from scope.json, fallback `"untitled"` |
| `main` | `() -> None` | Argparse setup + dispatch |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|draft|review|final|cleanup
gateway                    # Standalone 10-check run
report [--quality Q] [--search-rounds N] [--source-count N] [--version N (default=1)] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
```

### 4.2 `scripts/gateway.py` — Quality Gate Engine (381 lines)

**Data class:**

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN"
    passed: bool
    message: str = ""
```

**10 Check Functions:**

| Function | Level | Purpose |
|---|---|---|
| `check_artifact_exists` | BLOCKER | scope.json + collected.json + analysis.json must exist |
| `check_url_traceability` | BLOCKER | All claim source_urls must normalize-match collected.json URLs |
| `check_section_coverage` | BLOCKER | Required section IDs per goal_type (lookup table) |
| `check_analysis_schema` | BLOCKER | Top-level fields + section/claim shape validation |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_precision_inflation` | BLOCKER (primary); can return WARN for third-party-estimate findings | Exact precision + wrong evidence_type (BLOCKER); third_party + exact numbers (WARN); conflicting exact values in same metric_type (BLOCKER) |
| `check_metric_type_homogeneity` | BLOCKER | No mixing different metric_types within same section level (only checks claims with evidence_type in official_data/independent_benchmark) |
| `check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `check_claim_verified` | BLOCKER | Post-review: all claims must have `verified=true` |
| `check_source_metadata` | BLOCKER | official_data/independent_benchmark claims require non-empty source_metadata.test_conditions |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]`

### 4.3 `scripts/proceed.py` — Phase Transition Gates (293 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_is_stop_word` | `(token: str) -> bool` | Filter tokens <=1 char, punctuation, or in stop-word sets |
| `_tokenize_direction` | `(direction: str) -> list[str]` | jieba segmentation + stop-word filtering |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from artifact existence |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json fields + enums |
| `_check_search_gate` | `(workdir: Path, config?) -> tuple[list[str], list[str]]` | Search quality: (blockers, warnings) |
| `_generate_search_plan` | `(workdir: Path, config?) -> None` | Write search_plan.json with direction x tier tasks |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions + runs phase-specific gates |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `gateway.run_all()` |

**Depth -> Min Sources Per Direction:** `quick=1`, `standard=3`, `deep=5`

### 4.4 `scripts/reporter.py` — Report Generator (193 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_build_reference_map` | `(analysis: dict, collected: list) -> dict[str, int]` | Build `{normalized_url -> ref_number}` by first-occurrence order |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix |
| `build_front_matter` | `(topic, goal_type, scope, quality, search_rounds, source_count, version, audience?, report_language?) -> str` | YAML front matter block (8-12 fields) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `_build_claim_ref` | `(claim, reference_map) -> str` | Build `[N]` reference number from normalized URL |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body |
| `generate_report` | `(analysis_path, scope_path, quality, search_rounds, source_count, version, report_language?) -> str` | Main entry: reads files, builds front matter + body |

**i18n Labels (8 pairs):** Sources/数据来源, References/参考文献, Test Conditions/测试环境, Claim/声明, Conditions/条件, Date/日期, Source Type/来源类型, Methodology/方法论

### 4.5 `scripts/lib/source_router.py` — Source Routing (83 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_get_config` | `(config?) -> dict` | Return injected config or load from disk |
| `get_route` | `(goal_type, config?) -> dict` | Return route dict (entry_tier, path); unknown -> "other" |
| `recommend_sources` | `(goal_type, config?) -> dict` | Structured output with recommended/all sources |
| `get_default_min_sources` | `(goal_type, config?) -> int` | Lookup from goal_type_defaults, fallback 2 |
| `get_default_depth` | `(goal_type, config?) -> str` | Priority: goal_type_defaults > config.default_depth > "standard" |

### 4.6 `scripts/lib/utils.py` — Utilities (44 lines)

| Function | Signature | Purpose |
|---|---|---|
| `normalize_url` | `(url: str) -> str` | Lowercase, strip www, sort query params, strip fragment, strip trailing slash |
| `read_json` | `(path: Path) -> Any` | `json.load()` with UTF-8 |
| `write_json` | `(data, path: Path) -> None` | `json.dump()` with UTF-8, indent=2, ensure_ascii=False; auto-mkdir |
| `_find_project_root` | `() -> Path` | Walk up from CWD to find `.git` directory; fallback to CWD |
| `ensure_dir` | `(path: Path) -> Path` | `mkdir(parents=True, exist_ok=True)` + return path |

---

## 5. Configuration — `config.json`

### Source Tiers (4 tiers)

| Tier | Name | Sources |
|---|---|---|
| 1 | Academic/Standards | arXiv, Google Scholar, PubMed, CNKI, W3C, IETF, ISO |
| 2 | Docs/Open Source | GitHub, MDN, Wikipedia |
| 3 | Industry/Expert Blogs | Medium, IEEE Spectrum, MIT Tech Review |
| 4 | Community/UGC | Reddit, Stack Overflow, Zhihu |

### Goal Type Routes (10 types)

| Goal Type | Entry Tier | Path |
|---|---|---|
| exploratory | 4 | [4, 2] |
| panoramic_understanding | 4 | [4, 2, 1] |
| tech_selection | 2 | [2, 1] |
| feasibility_assessment | 2 | [2, 1] |
| competitive_comparison | 4 | [4, 3] |
| academic_research | 1 | [1] |
| fact_check | 1 | [1, 2, 4] |
| background_check | 3 | [3, 4, 1] |
| market_analysis | 3 | [3, 1] |
| other | 3 | [3, 2, 1] |

### Other Settings

- `output_dir`: `"./reports/"`
- `default_report_language`: `"zh"`
- `default_depth`: `"standard"`
- `goal_type_defaults`: exploratory (depth=quick, min_sources=1), fact_check (depth=quick, min_sources=1)

---

## 6. Quality Gate Detail

### Gate 1: Scope -> Search

- **scope.json schema validation**: 6 required fields (topic, goal_type, depth, audience, scope_description, search_directions)
- **Enum validation**: goal_type in 10 values, depth in {quick, standard, deep}, audience in {CTO, engineer, researcher, general}
- **Generates**: `search_plan.json` with direction x tier search tasks

### Gate 2: Search -> Analysis

| Check | Level | Logic |
|---|---|---|
| topic_coverage | BLOCKER | Every search_direction token must match >=1 collected entry (jieba segmentation) |
| tier_coverage | WARN | All tiers in goal_type route must have >=1 source in collected.json |
| per_direction_min_sources | WARN | Depth-driven: quick=1, standard=3, deep=5 per direction |
| min_sources | WARN | Total collected entries >= goal_type default (fallback 2) |

### Gate 3: Draft -> Review

- analysis.json is readable and has `topic` + `goal_type` keys
- analysis.json `sections` is non-empty
- `draft/report.md` exists

Note: This is a lightweight structural check, not full schema validation. Individual claim fields are not validated at this gate.

### Gate 4: Review -> Final

Full 10-check gateway run (see section 4.2). Only BLOCKER-level failures block this transition; WARN-level failures are reported but do not prevent proceeding. Notable checks:

- **precision_inflation**: Detects exact-precision claims with wrong evidence types (BLOCKER), third-party estimates with precise numbers (WARN), conflicting exact values within same metric_type (BLOCKER)
- **metric_type_homogeneity**: No mixing metric_types within a section for official_data/independent_benchmark claims (ensures clean benchmark tables)
- **claim_verified**: All claims must have `verified=true` post-review

### Gate 5: Final -> Cleanup

Always passes — no structural checks.

### Quality Values

| Value | Condition |
|---|---|
| `passed` | Review sub-agent ran + all gates passed |
| `degraded` | Set manually via `--quality degraded` CLI flag; never auto-assigned |
| `unreviewed` | User skipped review sub-agent + gates clean |

---

## 7. Data Model Schemas

### scope.json

```json
{
  "topic": "string (required)",
  "goal_type": "enum (10 values, required)",
  "depth": "quick | standard | deep (required)",
  "audience": "CTO | engineer | researcher | general (required)",
  "scope_description": "string (required)",
  "search_directions": ["string (non-empty list)"],
  "report_language": "string (optional)"
}
```

### collected.json

```json
[
  {
    "url": "string",
    "title": "string",
    "snippet": "string",
    "source_tier": "int (1-4)",
    "fetched_content": "string"
  }
]
```

### analysis.json

```json
{
  "topic": "string (required)",
  "goal_type": "string (required)",
  "sections": [
    {
      "id": "string",
      "title": "string",
      "content": "string",
      "claims": [
        {
          "text": "string (required)",
          "source_urls": ["string (required, non-empty)"],
          "evidence_type": "official_data | independent_benchmark | third_party_estimate | qualitative_trend | expert_opinion (WARN if >50% missing in quantitative types)",
          "confidence": "high | medium | low (WARN if >50% missing in quantitative types)",
          "precision": "exact | range | qualitative (WARN if >50% missing in quantitative types)",
          "metric_type": "swe_bench_verified | swe_bench_pro | terminal_bench | pr_merge_rate | refactoring_safety | custom (optional, validated only if present)",
          "source_metadata": {
            "test_conditions": "string (required for official_data/independent_benchmark claims)"
          },
          "verified": "bool (required post-review)"
        }
      ]
    }
  ]
}
```

### search_plan.json

```json
{
  "goal_type": "string",
  "depth": "string",
  "route": [...],
  "tasks": [
    {
      "direction": "string",
      "tier": "int",
      "query_language": "en | zh",
      "site_queries": ["string"],
      "min_sources": "int"
    }
  ]
}
```

---

## 8. Constants Reference

### gateway.py

```python
_QUANTITATIVE_GOAL_TYPES = frozenset({
    "tech_selection", "competitive_comparison", "feasibility_assessment",
    "market_analysis", "academic_research",
})
_VALID_EVIDENCE_TYPES = frozenset({
    "official_data", "independent_benchmark", "third_party_estimate",
    "qualitative_trend", "expert_opinion",
})
_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})
_VALID_METRIC_TYPES = frozenset({
    "swe_bench_verified", "swe_bench_pro", "terminal_bench",
    "pr_merge_rate", "refactoring_safety", "custom",
})
_EXPLORATORY_GOAL_TYPES = frozenset({
    "exploratory", "panoramic_understanding", "background_check", "other",
})
_REQUIRED_SECTION_IDS = {
    "tech_selection": ["overview", "comparison", "recommendation", "methodology"],
    "feasibility_assessment": ["overview", "analysis", "conclusion", "methodology"],
    "fact_check": ["claims", "evidence", "conclusion"],
    "competitive_comparison": ["overview", "comparison", "positioning", "methodology"],
    "academic_research": ["abstract", "findings", "references", "methodology"],
    "market_analysis": ["overview", "data", "trends", "conclusion", "methodology"],
}
_MIN_SOURCES = 2
_SINGLE_SOURCE_RATIO = 0.5
_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)(\d{1,3}(?:,\d{3})*|\d+)(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?(?!\w)"
)
```

### proceed.py

```python
_ENGLISH_STOP_WORDS = frozenset({...})    # 37 words
_CHINESE_STOP_WORDS = frozenset({...})    # 59 characters
_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS
_DEPTH_MIN_SOURCES_PER_DIRECTION = {"quick": 1, "standard": 3, "deep": 5}
# Note: goal_type, depth, audience valid values are inline tuples in _check_scope_schema(), not named constants
_VALID_TRANSITIONS = {
    "scope": "search", "search": "analysis",
    "draft": "review", "review": "final", "final": "cleanup",
}
```

---

## 9. Import Dependency Graph

```
cli.py -----> lib.utils (_find_project_root, read_json)
      |-----> proceed.py (lazy import, circular-avoidance)
      |-----> reporter.py (lazy import)
      |-----> lib.source_router (recommend_sources, lazy import)

proceed.py -> lib.utils (ensure_dir, read_json, write_json)
           -> lib.source_router (get_default_min_sources, get_route, recommend_sources)
           -> gateway.py (run_all, CheckResult)
           -> cli.py (_find_project_root, unused import)

gateway.py -> lib.utils (normalize_url, read_json)

reporter.py -> lib.utils (normalize_url, read_json)

source_router.py -> (no internal imports)

utils.py -> (no internal imports)
```

**External deps:** `jieba` (proceed.py only), `argparse` (cli.py), `dataclasses` (gateway.py), `re` (gateway.py only; proceed.py imports but never uses), `urllib.parse` (utils.py)

---

## 10. Error Handling Patterns

1. **Gate-based error handling**: Almost all errors are terminal via `sys.exit(1)`. No graceful degradation on BLOCKER.
2. **JSON parse errors**: `read_json()` propagates `FileNotFoundError` / `json.JSONDecodeError` up to gate functions, which wrap them in `CheckResult` or error strings.
3. **Defensive fallbacks**: `_count_sources()` and `_read_topic()` use `try/except Exception` to return safe defaults (0 or `"untitled"`).
4. **WARN vs BLOCKER**: Two-tier severity. `proceeds()` prints WARN to stderr but continues; BLOCKER stops the gate and returns error list.
5. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` prefixes.
6. **Stateless phase detection**: `detect_current_phase()` is pure — derives state from file existence, no mutable state.

---

## 11. Test Coverage Summary

| Module | Coverage | Notable | Gaps |
|---|---|---|---|
| `cli.py` | Good | All 5 commands tested; project root detection (3 cases) | `cmd_report` with incomplete scope.json; `cmd_gateway` only tests pass path |
| `gateway.py` | Comprehensive | All 10 checks with edge cases; precision_inflation has 8 test cases; section_coverage tests 5 goal_types + 4 exploratory scenarios | None |
| `proceed.py` | Comprehensive | Phase detection (6 states); 5 gate transitions; Chinese search directions (jieba); per-direction min sources (3 depths); tier coverage | `_generate_search_plan` output shape not tested |
| `reporter.py` | Comprehensive | Reference map dedup; test conditions table (6 cases); i18n labels (zh/en/fallback); full pipeline; `report_language` priority | Empty analysis.json not tested |
| `source_router.py` | Good | Route resolution; unknown goal_type fallback; min sources; depth priority; integration against real config.json | None |
| `utils.py` | Good | URL normalization (8 cases); JSON read/write round-trip; directory creation | Write permission errors not tested |

**Test patterns**: `tmp_path` for file isolation, `unittest.mock.patch` to override `WORKDIR` and `sys.exit`, `argparse.Namespace` constructed directly (no subprocess), ADR references in test comments.

---

## 12. Code Style Patterns

| Aspect | Convention |
|---|---|
| Type hints | `from __future__ import annotations` everywhere; all signatures typed; `typing.cast` for JSON-loaded data |
| Imports | stdlib first, then project-internal; relative imports (`from .module import`); lazy imports for circular-avoidance |
| Docstrings | `"""one-line"""` style; concise; some private functions lack docstrings |
| Naming | `snake_case` functions/vars, `PascalCase` classes/tests, `UPPER_CASE` module constants, `_` prefix for private |
| Side effects | No global mutable state; all state in JSON files; print to stdout/stderr; `sys.exit(n)` for CLI exit codes |
| Config injection | Functions accept `config: dict | None` parameter for testability |
| Async | None — all code is synchronous |

---

## 13. Known Issues and Gaps

1. **jieba vs stdlib-only rule**: AGENTS.md says "No package manager: stdlib only", but jieba is a runtime pip dependency (documented exception per ADR 0001).
2. **No schema library**: Validation is manual (`field not in dict` checks). No Pydantic/dataclasses for schema enforcement — fragile if schemas evolve.
3. **Test gaps**: `cmd_gateway` only tests pass path; `_generate_search_plan` output shape untested; `cmd_report` incomplete scope.json untested.
4. **No concurrency**: All operations synchronous and sequential. SKILL.md says "parallel" section writing but code doesn't implement it.
5. **No timeout or retry**: File operations have no retry. Gates succeed or fail immediately.
6. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
7. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
8. **Silent exception swallowing**: `_count_sources()` and `_read_topic()` use `except Exception` fallbacks.
9. **No custom exceptions**: Zero `Exception` subclasses in the codebase.
10. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` removes everything.

---

## 14. ADR Index

| ADR | Title | Key Decision |
|---|---|---|
| 0001 | Topic coverage token matching | Use jieba for Chinese search direction tokenization |
| 0002 | Exploratory loose section coverage | Exploratory types only need overview + 1 other section |
| 0003 | Project root path resolution | Walk up from CWD to find `.git` |
| 0004 | Metric type field and homogeneity gate | Add metric_type field + same-section homogeneity check |
| 0005 | Claim verified field and review prompt | Add `verified` bool + review sub-agent prompt |
| 0006 | Data variance handling | Precision inflation gate for exact-value mismatches |
| 0007 | Tier coverage gate | WARN if any tier in route has zero sources |
| 0008 | Source metadata required and defensive rendering | Official/benchmark claims need test_conditions; skip empty fields in render |
| 0009 | Remove cross-session iteration | No iteration counter across sessions |
| 0010 | Depth drives per-direction min sources | quick=1, standard=3, deep=5 per search direction |
| 0011 | Auto-generate search plan | Generate search_plan.json with direction x tier tasks |
