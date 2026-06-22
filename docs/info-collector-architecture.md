# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~2,394 lines (11 modules) |
| Tests | ~4,753 lines (15 files, 443 test functions) |
| Config/docs | config.json + SKILL.md + 5 reference docs |
| Runtime pip deps | None (jieba removed; ADR 0001 superseded by ADR 0012) |
| HTTP deps | None — search done externally by AI via exa/playwright |

---

## 2. File Listing

### Source Files

| # | Path | Lines | Purpose |
|---|---|---|---|
| 1 | `SKILL.md` | 171 | Skill definition: 4-phase workflow + Setup Wizard, CLI reference, quality values |
| 2 | `config.json` | — | 4-tier source config + 10 goal-type routes + output settings |
| 3 | `scripts/__init__.py` | 0 | Empty (package marker) |
| 4 | `scripts/__main__.py` | 6 | `python -m scripts` entry |
| 5 | `scripts/cli.py` | 200 | CLI entry: 6 subcommands, argparse, `sys.exit` on gate fail; catches `InfoCollectorError` |
| 6 | `scripts/gateway.py` | 48 | Re-export facade: re-exports all check functions from `artifact_checks` + `report_checks` |
| 7 | `scripts/artifact_checks.py` | 759 | Artifact-level quality gate checks: 18 check functions, `CheckResult` dataclass, `_read_artifact` helper |
| 8 | `scripts/report_checks.py` | 251 | Report-level quality gate checks: 10 check functions on generated .md file |
| 9 | `scripts/proceed.py` | 417 | Phase transition gates, phase detection, `_sanitize_sections`, search plan generation |
| 10 | `scripts/reporter.py` | 188 | Markdown report generator: YAML front matter, i18n, references, tier star labels |
| 11 | `scripts/lib/__init__.py` | 0 | Empty |
| 12 | `scripts/lib/constants.py` | 142 | Centralized constants: enumerations, thresholds, artifact filenames, pipeline config, labels |
| 13 | `scripts/lib/exceptions.py` | 22 | Custom exception hierarchy: `InfoCollectorError`, `GateFailureError`, `ArtifactError`; `ValidationError` dataclass |
| 14 | `scripts/lib/utils.py` | 93 | `normalize_url`, `read_json`/`write_json` (with retry), `find_project_root`, `config_path`, `tokenize_cjk_aware`, `build_collected_by_url`, `ensure_dir` |
| 15 | `scripts/lib/source_router.py` | 73 | Pure-function routing: `get_route`, `recommend_sources`, defaults |
| 16 | `scripts/lib/schemas.py` | 195 | Centralized schema validation: TypedDict definitions + `validate_scope`, `validate_analysis`, `validate_collected` (ADR 0015) |
| 17 | `references/GATES.md` | — | 5-gate system reference |
| 18 | `references/REVIEW_PROMPT.md` | — | Review sub-agent prompt template |
| 19 | `references/cli-reference.md` | — | CLI commands reference |
| 20 | `references/subagent-template.md` | — | Subagent delegation template with JSON schema embedding |
| 21 | `references/writing-guide.md` | — | Writing guide for analysis.json content quality |

### Test Files

| # | Path | Lines | Tests | Coverage |
|---|---|---|---|---|
| 1 | `tests/conftest.py` | 3 | — | Adds skill dir to `sys.path` |
| 2 | `tests/__init__.py` | 0 | — | Empty |
| 3 | `tests/test_cli.py` | 432 | 30 | All 6 commands + project root detection + `_build_report_filename` + `_detect_quality` verdict parsing + `InfoCollectorError` catch in main |
| 4 | `tests/test_gateway.py` | 1,439 | 96 | All 18 artifact checks, edge cases, `CheckResult`, `run_all`; precision_inflation; claim_verified with unverifiable + ratio |
| 5 | `tests/test_gateway_import.py` | 36 | 1 | Gateway import guard (jieba not imported at module level) |
| 6 | `tests/test_report_gateway.py` | 435 | 44 | All 10 report checks + `run_report_checks` aggregator |
| 7 | `tests/test_content_concreteness.py` | 322 | 29 | `_count_words`, vague phrase detection, number/name presence, CJK specifics |
| 8 | `tests/test_exceptions.py` | 38 | 13 | Exception hierarchy + `ValidationError` dataclass: equality, fields |
| 9 | `tests/test_proceed.py` | 697 | 54 | Phase detection (state file + artifact fallback) + gate routing + per-direction min sources + CJK coverage + `covered_directions` + `_sanitize_sections` + review self-loop |
| 10 | `tests/test_reporter.py` | 597 | 42 | Report pipeline + i18n + test conditions + reference numbering + tier labels |
| 11 | `tests/test_reporter_postprocess.py` | 77 | 18 | `_post_process`, bare URL fix, reference section detection |
| 12 | `tests/test_source_router.py` | 175 | 21 | Router functions + optional tiers + integration against real config.json |
| 13 | `tests/test_utils.py` | 100 | 17 | URL normalization + JSON I/O with retry + directory creation |
| 14 | `tests/test_reset.py` | 102 | 10 | Reset subcommand: scope/search/analysis/review reset, phase detection after reset, invalid phase |
| 15 | `tests/test_schemas.py` | 303 | 68 | Schema validation: scope, analysis, collected; english_title requirement; covered_directions; ValidationError equality |

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
|    - english_title (optional)       |
+---------------+---------------------+
                |
                v
    proceed --from scope --to search   <-- Gate 1: scope.json schema validation
                |                         |-- Field existence + type checks (via schemas.py)
                |                         |-- Enum validation (goal_type, depth, audience)
                |                         +-- Generate search_plan.json
                v
+-------------------------------------+
|  Phase 2: Search -> Collect -> Filter|
|  Output: collected.json              |
|    - url, title, snippet            |
|    - source_tier, fetched_content   |
|    - covered_directions[] (optional)|
|  Search via exa/playwright (external)|
|  Routed by config.json tier paths   |
+---------------+---------------------+
                |
                v
    proceed --from search --to analysis  <-- Gate 2: search quality
                |                           |-- topic_coverage (BLOCKER for non-CJK, WARN for CJK)
                |                           |   + covered_directions override (ADR 0017)
                |                           |-- tier_coverage (WARN)
                |                           |-- per_direction_min_sources (WARN)
                |                           |-- search_plan_compliance (WARN)
                |                           +-- min_sources (WARN)
                v
+-------------------------------------+
|  Phase 3a: Build analysis.json       |
|    - Plan sections                   |
|    - Write content per section       |
|    - Extract claims with metadata    |
|    - _sanitize_sections() normalizes |
|      subagent output (ADR 0017)     |
|  Schema:                             |
|    topic, goal_type, sections[]      |
|      +- id, title, content           |
|      +- claims[]                     |
|           +- text, source_urls[]     |
|           +- evidence_type           |
|           +- confidence, precision   |
|           +- metric_type (optional)  |
|           +- source_metadata (opt)   |
|           +- verified (bool|"unverifiable") |
+---------------+---------------------+
                |
                v
    proceed --from analysis --to review  <-- Gate 3: schema + URL traceability
                |                           |-- _sanitize_sections() normalizes output
                |                           |-- validate_analysis() schema check
                |                           +-- URL traceability via gateway.run_all
                v
+-------------------------------------+
|  Phase 3b: Review (optional sub-agent)|
|  Review output: review_report.md     |
|  Updates analysis.json verified field|
|  Overall Verdict: **pass** /         |
|    **pass_with_issues** / **fail**   |
+---------------+---------------------+
                |
                v
    proceed --from review --to final   <-- Gate 4: 18-check artifact gateway (BLOCKERs only)
                v
+-------------------------------------+
|  Phase 3c: Final report generation  |
|  cli.py report --quality ...         |
|    <-- reporter.py generates Markdown|
|  _detect_quality() parses verdict:   |
|    **pass** → "passed"               |
|    **pass_with_issues** → "degraded" |
|    **fail** → sys.exit(1)            |
|  Output: <output_dir>/<title>.md     |
|    (YAML front matter + numbered refs|
|     + appendix + tier star labels)   |
|    Filename collision → _YYYY-MM-DD  |
+---------------+---------------------+
                |
                v
+-------------------------------------+
|  Phase 3d: Report rendering         |
|  verification                        |
|  Step 1: AI sanity check —          |
|    verify citations clickable,       |
|    ref URLs clickable, no trailing   |
|    artifacts, internal anchors work  |
|  Step 2: proceed --from final       |
|    --to cleanup (10 report checks:  |
|    dangling refs, orphaned defs,     |
|    refs visibility, table delimiters,|
|    front matter, heading levels,     |
|    duplicate headings, unclosed code |
|    blocks, empty sections, overlong  |
|    lines)                             |
|  If any fail → fix .md → re-run     |
+---------------+---------------------+
                |
                v
                |
                v
+-------------------------------------+
|  Phase 4: Cleanup                    |
|  cli.py clean -> deletes .workdir/  |
+-------------------------------------+
```

### Phase Detection (`detect_current_phase`)

Phase is determined by first checking `pipeline_state.json` (explicit state file), then falling back to artifact presence detection.

| Priority | Condition | Phase |
|---|---|---|
| 1 | `pipeline_state.json` exists with valid `current_phase` | Value from state file |
| 2 | `.workdir` doesn't exist OR no `scope.json` | `pre_scope` |
| 3 | `scope.json` exists AND `collected.json` doesn't | `post_scope` |
| 4 | `collected.json` exists AND `analysis.json` doesn't | `post_search` |
| 5 | `analysis.json` exists AND `review_report.md` doesn't | `post_analysis` |
| 6 | `review_report.md` exists | `post_review` |

Invalid or corrupt state file → falls back to artifact detection (ADR 0019).

### Valid Transitions

```
scope -> search -> analysis -> review -> final -> cleanup
                                |
                                +-> review  (self-loop: re-validate after fixes)
```

Transition set is `_VALID_TRANSITIONS_SET` (set of tuples), defined in `lib/constants.py`.

---

## 4. API Surface — Function Reference

### 4.1 `scripts/cli.py` — CLI Entry Point (200 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone 18-check gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > `"en"` |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `cmd_reset` | `(args: Namespace) -> None` | Reset pipeline to a given phase by deleting target and subsequent artifacts (ADR 0016) |
| `_detect_quality` | `() -> str` | Parse `## Overall Verdict` in review_report.md: `**pass**` → "passed", `**pass_with_issues**` → "degraded", `**fail**` → sys.exit(1), unparseable → "degraded" (ADR 0017) |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_build_report_filename` | `(scope_data: dict, output_path: Path) -> Path` | Build safe ASCII report filename; prefers `english_title` over `topic`; appends `_YYYY-MM-DD` on collision |
| `main` | `() -> None` | Argparse setup + dispatch; catches `InfoCollectorError` at top level |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|review|final|cleanup
gateway                    # Standalone 18-check run
report [--quality Q] [--search-rounds N] [--source-count N] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
reset --phase <X>          # X: scope|search|analysis|review — delete target + subsequent artifacts
```

**Module-level constants:**

| Name | Description |
|---|---|
| `WORKDIR` | `find_project_root() / ".workdir"` |
| `_CONFIG_PATH` | `config_path()` — delegates to `lib.utils.config_path()` |

### 4.2 `scripts/gateway.py` — Re-export Facade (48 lines)

Thin backward-compatibility layer. All check functions live in `artifact_checks.py` and `report_checks.py`. `gateway.py` re-exports them so existing `from scripts.gateway import ...` still works.

**Re-exports from `artifact_checks`:** `CheckResult`, `run_all`, 18 check functions, 5 private helpers

**Re-exports from `report_checks`:** `run_report_checks`, 10 report check functions

> New code should import from the specific module directly.

### 4.3 `scripts/artifact_checks.py` — Artifact-Level Quality Gate Checks (759 lines)

**Data class:**

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN"
    passed: bool
    message: str = ""
```

**18 Check Functions:**

| Function | Level | Purpose |
|---|---|---|
| `check_artifact_exists` | BLOCKER | scope.json + collected.json + analysis.json must exist |
| `check_url_traceability` | BLOCKER | All claim source_urls must normalize-match collected.json URLs |
| `check_section_coverage` | BLOCKER | Required section IDs per goal_type (lookup table) |
| `check_analysis_schema` | BLOCKER/WARN | Delegates to `validate_analysis()` from schemas.py; warns on duplicate `## ` headings |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `check_precision_inflation` | BLOCKER + WARN | Exact precision + wrong evidence_type (BLOCKER); third_party + unverified precise numbers (WARN); conflicting exact values in same metric_type (BLOCKER) |
| `check_metric_type_homogeneity` | BLOCKER | No mixing different metric_types within same section level (only checks claims with evidence_type in official_data/independent_benchmark) |
| `check_claim_verified` | BLOCKER + WARN | verified=False = BLOCKER; verified="unverifiable" = WARN; ratio < 60% = WARN; skipped if no review_report.md |
| `check_source_metadata` | BLOCKER | official_data/independent_benchmark claims require non-empty source_metadata.test_conditions |
| `check_content_concreteness` | BLOCKER/WARN (depends on goal_type) | Quantitative types: vague phrase density >10% (WARN); missing numbers/names in strict types (BLOCKER), others (WARN) |
| `check_methodology_depth` | WARN | Quantitative types: methodology section <150 words or lacks Markdown table |
| `check_recommendation_structure` | WARN | tech_selection/competitive_comparison: recommendation section lacks comparison table or "not recommended" |
| `check_source_tier_balance` | WARN | Quantitative types: Tier 1+2 source ratio <30% among referenced URLs |
| `check_claim_dedup` | WARN | Same claim text appears in multiple sections |
| `check_fetched_content_depth` | WARN | Check if fetched_content is stub-length or below tier minimum |
| `check_search_plan_compliance` | WARN | Flag if search_plan.json tasks are still pending (plan not followed) |
| `check_claim_source_relevance` | WARN | Flag claims whose source text doesn't contain the claim's key numbers/names |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]`

**Private helpers:** `_read_artifact`, `_source_text`, `_normalize_numbers`, `_number_found_in_source`, `_check_data_variance`, `_count_words`, `_has_valid_number`, `_has_concrete_name`

### 4.4 `scripts/report_checks.py` — Report-Level Quality Gate Checks (251 lines)

All functions operate on the generated `.md` report file.

| Function | Purpose |
|---|---|
| `check_report_dangling_refs` | In-text [N] has no matching definition in References |
| `check_report_orphaned_defs` | Reference definition [N]: not cited in text |
| `check_report_refs_visibility` | References use visible format, not hidden `[N]: URL` definitions |
| `check_report_table_delimiters` | Markdown tables have correct `|---|` delimiter rows |
| `check_report_front_matter` | YAML front matter exists and is well-formed |
| `check_report_heading_levels` | No heading level skips (e.g., `##` → `####`) |
| `check_report_duplicate_headings` | No duplicate heading text at same level |
| `check_report_unclosed_code_blocks` | All fenced code blocks are properly closed |
| `check_report_empty_sections` | No sections with empty content |
| `check_report_overlong_lines` | No lines exceeding 500 characters |

**Aggregator:** `run_report_checks(report_path) -> list[CheckResult]`

**Private helpers:** `_strip_front_matter`, `_find_references_section`

### 4.5 `scripts/proceed.py` — Phase Transition Gates (417 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_is_stop_word` | `(token: str) -> bool` | Filter tokens <=1 char, punctuation, or in stop-word sets |
| `_tokenize_direction` | `(direction: str) -> list[str]` | CJK-aware segmentation via `tokenize_cjk_aware` + stop-word filtering |
| `_sanitize_sections` | `(analysis: dict, collected_urls: set[str] \| None = None) -> dict` | Normalize subagent output: `section_id` → `id`, `sources` → `source_urls`, strip non-schema keys, default `claims` to `[]`; auto-fix URL traceability if `collected_urls` provided (ADR 0017) |
| `write_phase_state` | `(workdir: Path, phase: str) -> None` | Write current phase to `pipeline_state.json`; warns on failure instead of silent pass |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from `pipeline_state.json` first, then artifact presence fallback (ADR 0019) |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json via `schemas.validate_scope()` |
| `_has_cjk_tokens` | `(directions: list[str]) -> bool` | Check if any search direction contains CJK characters |
| `_check_tier_coverage` | `(collected, goal_type, config?) -> list[str]` | Check if collected sources cover each tier in the route |
| `_check_topic_coverage` | `(collected, scope, needed) -> tuple[list[str], list[str]]` | Token-based direction coverage; returns (blockers, warnings) |
| `_check_search_plan_inline` | `(workdir: Path) -> list[str]` | Delegates to `check_search_plan_compliance` from artifact_checks |
| `_check_search_gate` | `(workdir: Path, config?) -> tuple[list[str], list[str]]` | Search quality: (blockers, warnings); CJK directions downgrade topic_coverage to WARN; `covered_directions` override; schema validation |
| `_generate_search_plan` | `(workdir: Path, config?) -> None` | Write search_plan.json with direction x tier tasks |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `_find_report_path` | `(workdir: Path) -> Path \| None` | Find latest .md report in configured output directory |
| `_gate_scope` | `(workdir, config?) -> list[str]` | Scope gate: schema check + search plan generation |
| `_gate_search` | `(workdir, config?) -> list[str]` | Search gate: topic/tier/source checks |
| `_gate_analysis` | `(workdir) -> list[str]` | Analysis gate: sanitize + schema + URL traceability |
| `_gate_review` | `(workdir) -> list[str]` | Review gate: full artifact gateway (BLOCKERs only) |
| `_gate_final` | `(workdir) -> list[str]` | Final gate: report checks via `run_report_checks` |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions via `_VALID_TRANSITIONS_SET` + runs phase-specific gates via dispatch table |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `gateway.run_all()` |

**Depth -> Min Sources Per Direction:** `quick=1`, `standard=3`, `deep=5`

**Module-level constants:**

| Name | Value |
|---|---|
| `_STOP_WORDS` | `_ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS` |
| `_SECTION_KEYS` | `frozenset({"id", "title", "content", "claims"})` |
| `_CLAIM_KEYS` | `frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified"})` |

### 4.6 `scripts/reporter.py` — Report Generator (188 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_build_reference_map` | `(analysis: dict, collected: list[dict]) -> dict[str, int]` | Build `{normalized_url -> ref_number}` by first-occurrence order |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix with tier star labels (★★★☆) |
| `_clean_url` | `(url: str) -> str` | Clean URL for display |
| `_post_process` | `(markdown: str) -> str` | Fix bare URLs in body (not in reference section); delegate reference section detection to `_find_references_section` |
| `build_front_matter` | `(topic, goal_type, scope, quality, search_rounds, source_count, audience?, report_language?) -> str` | YAML front matter block (8-12 fields) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `_build_claim_ref` | `(claim, reference_map) -> str` | Build `[N]` reference number from normalized URL |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body; exploratory types use compact mode (claims omitted) |
| `generate_report` | `(analysis_path, scope_path, quality, search_rounds, source_count, report_language?) -> str` | Main entry: reads files, builds front matter + body |

**i18n Labels (8 pairs):** Sources/数据来源, References/参考文献, Test Conditions/测试环境, Claim/声明, Conditions/条件, Date/日期, Source Type/来源类型, Methodology/方法论

**Tier Star Labels:** Tier 1 → ★★★☆, Tier 2 → ★★☆☆, Tier 3 → ★☆☆☆, Tier 4 → ☆☆☆☆

### 4.7 `scripts/lib/source_router.py` — Source Routing (73 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_get_config` | `(config?) -> dict` | Return injected config or load from disk via `config_path()` |
| `get_route` | `(goal_type, config?) -> dict` | Return route dict (entry_tier, path, optional_tiers); unknown -> "other" |
| `recommend_sources` | `(goal_type, config?) -> dict` | Structured output with recommended/all sources (includes optional_tiers) |
| `get_default_min_sources` | `(goal_type, config?) -> int` | Lookup from goal_type_defaults, fallback 2 |
| `get_default_depth` | `(goal_type, config?) -> str` | Priority: goal_type_defaults > config.default_depth > "standard" |

### 4.8 `scripts/lib/utils.py` — Utilities (93 lines)

| Function | Signature | Purpose |
|---|---|---|
| `normalize_url` | `(url: str) -> str` | Lowercase, strip www, sort query params, strip fragment, strip trailing slash |
| `read_json` | `(path: Path, retries: int = 2, delay: float = 0.5) -> Any` | `json.load()` with UTF-8; retries on OSError; raises `ArtifactError` on JSONDecodeError or exhausted retries |
| `write_json` | `(data, path: Path, retries: int = 2, delay: float = 0.5) -> None` | `json.dump()` with UTF-8, indent=2, ensure_ascii=False; auto-mkdir; retries on OSError; raises `ArtifactError` on exhausted retries |
| `config_path` | `() -> Path` | Returns absolute path to `config.json` in skill root directory |
| `find_project_root` | `() -> Path` | Walk up from CWD to find `.git` directory; fallback to CWD |
| `ensure_dir` | `(path: Path) -> Path` | `mkdir(parents=True, exist_ok=True)` + return path |
| `tokenize_cjk_aware` | `(text: str, *, lowercase: bool = False) -> list[str]` | CJK-aware tokenization: splits on whitespace/CJK boundaries, CJK runs become single tokens. Does NOT filter stop words |
| `build_collected_by_url` | `(collected: list[dict]) -> dict[str, dict]` | Build `{normalized_url: entry}` lookup dict from collected list |

### 4.9 `scripts/lib/constants.py` — Centralized Constants (142 lines)

Single source of truth for all enumerations, thresholds, and classification sets.

| Category | Constants |
|---|---|
| Stop words | `_ENGLISH_STOP_WORDS` (37), `_CHINESE_STOP_WORDS` (49) |
| Enumerations | `_VALID_GOAL_TYPES` (10), `_VALID_DEPTHS` (3), `_VALID_AUDIENCES` (4), `_VALID_METRIC_TYPES` (6), `_VALID_EVIDENCE_TYPES` (5), `_VALID_CONFIDENCE` (3), `_VALID_PRECISION` (3) |
| Cross-constraints | `_NON_EXACT_EVIDENCE_TYPES` |
| Goal-type classifications | `_QUANTITATIVE_GOAL_TYPES` (5), `_EXPLORATORY_GOAL_TYPES` (4), `_CONCRETENESS_STRICT_GOAL_TYPES` (2) |
| Thresholds | `_VAGUE_DENSITY_THRESHOLD` (0.10), `_TIER_BALANCE_THRESHOLD` (0.30), `_METHODOLOGY_MIN_WORDS` (150), `_MIN_SOURCES` (2), `_FETCHED_CONTENT_MIN_LENGTH` (200), `_FETCHED_CONTENT_STUB_RATIO_BLOCKER` (0.30), `_FETCHED_CONTENT_MIN_BY_TIER` ({1:1000, 2:800, 3:600, 4:400}), `_DEPTH_MIN_SOURCES_PER_DIRECTION` (quick=1/standard=3/deep=5), `_COVERAGE_THRESHOLD` (0.5), `_OVERLONG_LINE_THRESHOLD` (500), `_SINGLE_SOURCE_RATIO` (0.5) |
| Vague phrases | `_VAGUE_PHRASES_ZH` (12), `_VAGUE_PHRASES_EN` (10) |
| Required sections | `_REQUIRED_SECTION_IDS` (6 goal types) |
| Artifact filenames | `ARTIFACT_SCOPE`, `ARTIFACT_COLLECTED`, `ARTIFACT_ANALYSIS`, `ARTIFACT_SEARCH_PLAN`, `ARTIFACT_PIPELINE_STATE`, `ARTIFACT_REVIEW_REPORT`, `ARTIFACT_CONFIG` |
| Pipeline config | `_VALID_TRANSITIONS_SET` (6 transitions incl. review→review), `_PHASE_ARTIFACTS` (4 phases) |
| Display labels | `_TIER_LABELS` (4 tiers), `_LABELS` (8 key × 2 languages) |

### 4.10 `scripts/lib/exceptions.py` — Custom Exceptions + ValidationError (22 lines)

| Class | Base | Attributes | Purpose |
|---|---|---|---|
| `InfoCollectorError` | `Exception` | — | Base exception for all info-collector errors |
| `GateFailureError` | `InfoCollectorError` | `phase: str`, `blockers: list[str]` | Gate check failed with BLOCKER-level issues |
| `ArtifactError` | `InfoCollectorError` | `path: str`, `reason: str` | Artifact file missing, unreadable, or schema-invalid |
| `ValidationError` | `@dataclass` (not Exception) | `field: str`, `message: str` | Schema validation error carrier (ADR 0015) |

### 4.11 `scripts/lib/schemas.py` — Centralized Schema Validation (195 lines)

**TypedDict definitions:**

| Name | Fields |
|---|---|
| `ScopeDict` | topic, goal_type, depth, audience, scope_description, search_directions, report_language, english_title |
| `ClaimDict` | text, source_urls, evidence_type, confidence, precision, metric_type, source_metadata, verified |
| `SectionDict` | id, title, content, claims (list[ClaimDict]) |
| `AnalysisDict` | topic, goal_type, sections (list[SectionDict]) |
| `CollectedEntryDict` | url, title, snippet, source_tier, fetched_content, covered_directions |

**Public functions:**

| Function | Signature | Purpose |
|---|---|---|
| `validate_scope` | `(data: dict) -> list[ValidationError]` | Validate scope.json structure, enums, types, english_title requirement for non-ASCII topic |
| `validate_analysis` | `(data: dict) -> list[ValidationError]` | Validate analysis.json structure, sections, claims |
| `validate_collected` | `(data: list) -> list[ValidationError]` | Validate collected.json entries, covered_directions (max 3, subset of search_directions) |

**Private helpers:** `_err`, `_validate_sections`, `_validate_claims`, `_has_non_ascii`, `_check_english_title_required`

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

| Goal Type | Entry Tier | Path | Optional Tiers |
|---|---|---|---|
| exploratory | 4 | [4, 2] | — |
| panoramic_understanding | 4 | [4, 3, 1] | [2] |
| tech_selection | 2 | [2, 1] | — |
| feasibility_assessment | 2 | [2, 1] | — |
| competitive_comparison | 4 | [4, 3] | — |
| academic_research | 1 | [1] | — |
| fact_check | 1 | [1, 2, 4] | — |
| background_check | 3 | [3, 4, 1] | — |
| market_analysis | 3 | [3, 1] | — |
| other | 3 | [3, 2, 1] | — |

### Other Settings

- `output_dir`: `"./reports/"`
- `default_report_language`: `"zh"`
- `default_depth`: `"standard"`
- `goal_type_defaults`: exploratory (depth=quick, min_sources=1), fact_check (depth=quick, min_sources=1)

---

## 6. Quality Gate Detail

### Gate 1: Scope -> Search

- **scope.json schema validation** via `schemas.validate_scope()`: 6 required fields (topic, goal_type, depth, audience, scope_description, search_directions)
- **Enum validation**: goal_type in 10 values, depth in {quick, standard, deep}, audience in {CTO, engineer, researcher, general}
- **english_title**: required (BLOCKER) when topic contains non-ASCII characters
- **Generates**: `search_plan.json` with direction x tier search tasks

### Gate 2: Search -> Analysis

| Check | Level | Logic |
|---|---|---|
| topic_coverage | BLOCKER (non-CJK) / WARN (CJK) | Two-pass: (1) entries with `covered_directions` override token matching; (2) remaining entries use `tokenize_cjk_aware` token matching. CJK-heavy directions downgrade to WARN |
| tier_coverage | WARN | All required tiers in goal_type route must have >=1 source in collected.json; optional tiers produce INFO only |
| per_direction_min_sources | WARN | Depth-driven: quick=1, standard=3, deep=5 per direction |
| search_plan_compliance | WARN | Pending tasks in search_plan.json (delegates to `check_search_plan_compliance`) |
| min_sources | WARN | Total collected entries >= goal_type default (fallback 2) |
| schema validation | BLOCKER | `schemas.validate_collected()` validates entry structure + covered_directions constraints |

### Gate 3: Analysis -> Review

- `_sanitize_sections()` normalizes subagent output: `section_id` → `id`, `sources` → `source_urls`, strips non-schema keys, defaults `claims` to `[]`; auto-fixes URL traceability if `collected_urls` provided
- `schemas.validate_analysis()` validates structure
- URL traceability: extracted from `gateway.run_all()` results — the `url_traceability` check result is used directly (no separate `_check_url_traceability` function)

### Gate 4: Review -> Final

Full 18-check artifact gateway (BLOCKER-level only). The report has not yet been generated at this point, so report checks cannot run here. Only BLOCKER-level failures block this transition.

**Artifact checks** (via `run_all`):

- **precision_inflation**: Exact-precision claims with wrong evidence types (BLOCKER), third-party estimates with unverified precise numbers (WARN), conflicting exact values within same metric_type (BLOCKER)
- **metric_type_homogeneity**: No mixing metric_types within a section for official_data/independent_benchmark claims
- **claim_verified**: verified=False = BLOCKER; verified="unverifiable" = WARN; ratio < 60% = WARN
- **content_concreteness**: Vague phrase density >10% (WARN); missing numbers/names in strict goal types (BLOCKER)
- **methodology_depth**: Methodology section <150 words or lacks Markdown table (WARN)
- **recommendation_structure**: tech_selection/competitive_comparison recommendation section lacks comparison table or "not recommended" (WARN)
- **source_tier_balance**: Tier 1+2 source ratio <30% among referenced URLs (WARN)
- **claim_dedup**: Same claim text appears in multiple sections (WARN)
- **fetched_content_depth**: fetched_content stub-length or below tier minimum (WARN)
- **search_plan_compliance**: search_plan.json tasks still pending (WARN)
- **claim_source_relevance**: Claim numbers/names not found in source text (WARN)

**Report checks** (via `run_report_checks`):

- Dangling refs, orphaned definitions, refs visibility, table delimiters, front matter, heading levels, duplicate headings, unclosed code blocks, empty sections, overlong lines

### Gate 5: Final -> Cleanup

10-check report gateway on the generated `.md` file. Can fail if report has issues (dangling refs, empty sections, etc.) or if no report file is found.

### Quality Values

| Value | Condition |
|---|---|
| `passed` | `review_report.md` has `## Overall Verdict` with `**pass**` |
| `degraded` | Auto-assigned when verdict is `**pass_with_issues**` or unparseable; also settable via `--quality degraded` |
| `unreviewed` | `review_report.md` does not exist |

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
  "report_language": "string (optional)",
  "english_title": "string (optional, required when topic contains non-ASCII)"
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
    "fetched_content": "string",
    "covered_directions": ["string (optional, max 3, subset of search_directions)"]
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
          "verified": "bool | \"unverifiable\" (required post-review; \"unverifiable\" produces WARN)"
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
      "min_sources": "int",
      "status": "pending | completed | skipped",
      "collected_count": "int"
    }
  ]
}
```

### pipeline_state.json

```json
{
  "current_phase": "pre_scope | post_scope | post_search | post_analysis | post_review"
}
```

---

## 8. Constants Reference

### lib/constants.py — Single Source of Truth

All constants previously scattered across `gateway.py`, `proceed.py`, `reporter.py` are now centralized here. Only module-local constants (regex patterns, schema field whitelists) remain in their respective modules.

```python
# Stop words
_ENGLISH_STOP_WORDS = frozenset({...})    # 37 words
_CHINESE_STOP_WORDS = frozenset({...})    # 49 characters

# Enumerations
_VALID_GOAL_TYPES = frozenset({...})      # 10 types
_VALID_DEPTHS = frozenset({"quick", "standard", "deep"})
_VALID_AUDIENCES = frozenset({"CTO", "engineer", "researcher", "general"})
_VALID_METRIC_TYPES = frozenset({...})     # 6 types
_VALID_EVIDENCE_TYPES = frozenset({...})   # 5 types
_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})
_NON_EXACT_EVIDENCE_TYPES = frozenset({"third_party_estimate", "qualitative_trend", "expert_opinion"})

# Goal-type classifications
_QUANTITATIVE_GOAL_TYPES = frozenset({...})  # 5 types
_EXPLORATORY_GOAL_TYPES = frozenset({...})   # 4 types
_CONCRETENESS_STRICT_GOAL_TYPES = frozenset({"tech_selection", "competitive_comparison"})

# Thresholds
_VAGUE_DENSITY_THRESHOLD = 0.10
_TIER_BALANCE_THRESHOLD = 0.30
_METHODOLOGY_MIN_WORDS = 150
_MIN_SOURCES = 2
_FETCHED_CONTENT_MIN_LENGTH = 200
_FETCHED_CONTENT_STUB_RATIO_BLOCKER = 0.30
_FETCHED_CONTENT_MIN_BY_TIER = {1: 1000, 2: 800, 3: 600, 4: 400}
_DEPTH_MIN_SOURCES_PER_DIRECTION = {"quick": 1, "standard": 3, "deep": 5}
_COVERAGE_THRESHOLD = 0.5
_OVERLONG_LINE_THRESHOLD = 500
_SINGLE_SOURCE_RATIO = 0.5

# Vague phrases
_VAGUE_PHRASES_ZH = frozenset({...})      # 12 phrases
_VAGUE_PHRASES_EN = frozenset({...})      # 10 phrases

# Required section IDs
_REQUIRED_SECTION_IDS = {...}              # 6 goal types

# Artifact filenames (public, no underscore prefix)
ARTIFACT_SCOPE = "scope.json"
ARTIFACT_COLLECTED = "collected.json"
ARTIFACT_ANALYSIS = "analysis.json"
ARTIFACT_SEARCH_PLAN = "search_plan.json"
ARTIFACT_PIPELINE_STATE = "pipeline_state.json"
ARTIFACT_REVIEW_REPORT = "review_report.md"
ARTIFACT_CONFIG = "config.json"

# Pipeline configuration
_VALID_TRANSITIONS_SET = {
    ("scope", "search"), ("search", "analysis"), ("analysis", "review"),
    ("review", "final"), ("review", "review"), ("final", "cleanup"),
}
_PHASE_ARTIFACTS = {...}                  # 4 phases

# Display labels
_TIER_LABELS = {...}                      # 4 tiers
_LABELS = {...}                           # 8 key × 2 languages
```

### artifact_checks.py — Module-local constants

```python
_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')
_PRECISE_NUMBER_PATTERN = re.compile(...)
_VERSION_PATTERN = re.compile(...)
_LIST_ITEM_PATTERN = re.compile(...)
_NUMBER_PATTERN = re.compile(...)
```

### proceed.py — Module-local constants

```python
_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS   # from lib.constants
_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified"})
```

---

## 9. Import Dependency Graph

```
cli.py -----> lib.constants (ARTIFACT_*, _PHASE_ARTIFACTS)
       |-----> lib.exceptions (InfoCollectorError)
       |-----> lib.utils (config_path, find_project_root)
       |-----> proceed.py (lazy import: proceeds, detect_current_phase, write_phase_state)
       |-----> reporter.py (lazy import: generate_report)
       |-----> lib.source_router (lazy import: recommend_sources)

proceed.py -> lib.utils (config_path, find_project_root, ensure_dir, read_json, tokenize_cjk_aware, write_json)
           -> gateway (run_all as run_gateway, run_report_checks)
           -> lib.source_router (get_default_min_sources, get_route, recommend_sources)
           -> lib.exceptions (ArtifactError)
           -> lib.constants (ARTIFACT_*, _CHINESE_STOP_WORDS, _COVERAGE_THRESHOLD, _DEPTH_MIN_SOURCES_PER_DIRECTION, _ENGLISH_STOP_WORDS, _NON_EXACT_EVIDENCE_TYPES, _VALID_TRANSITIONS_SET)
           -> lib.schemas (lazy import: validate_scope, validate_analysis, validate_collected)
           -> artifact_checks (lazy import: check_search_plan_compliance)

gateway.py -> artifact_checks (CheckResult + 18 check functions + run_all + 5 helpers)  # noqa: F401 re-export
           -> report_checks (10 check functions + run_report_checks)                    # noqa: F401 re-export

artifact_checks.py -> lib.constants (17 constants)
                   -> lib.exceptions (ArtifactError)
                   -> lib.utils (build_collected_by_url, normalize_url, read_json, tokenize_cjk_aware)
                   -> lib.schemas (lazy import: validate_analysis)

report_checks.py -> artifact_checks (CheckResult)
                 -> lib.constants (_OVERLONG_LINE_THRESHOLD)

reporter.py -> lib.constants (ARTIFACT_COLLECTED, _EXPLORATORY_GOAL_TYPES, _LABELS, _TIER_LABELS)
            -> lib.utils (build_collected_by_url, normalize_url, read_json)
            -> report_checks (_find_references_section)

source_router.py -> lib.utils (config_path)

schemas.py -> lib.constants (_VALID_AUDIENCES, _VALID_DEPTHS, _VALID_GOAL_TYPES, _VALID_METRIC_TYPES)
           -> lib.exceptions (ValidationError)

constants.py -> (no internal imports)

exceptions.py -> (no internal imports)

utils.py -> lib.exceptions (ArtifactError)
          -> lib.constants (ARTIFACT_CONFIG)
```

**External deps:** `argparse` (cli.py), `dataclasses` (artifact_checks.py, exceptions.py), `re` (cli.py, artifact_checks.py, report_checks.py, proceed.py, reporter.py), `string` (proceed.py), `time` (utils.py), `urllib.parse` (utils.py), `typing` (proceed.py, schemas.py, source_router.py, utils.py)

---

## 10. Error Handling Patterns

1. **Custom exception hierarchy**: `InfoCollectorError` base → `GateFailureError` (gate failures) + `ArtifactError` (file I/O). Top-level `cli.py:main()` catches `InfoCollectorError` uniformly. `ValidationError` is a dataclass (not an Exception) used by schemas.py for validation results.
2. **Gate-based error handling**: Almost all errors are terminal via `sys.exit(1)`. No graceful degradation on BLOCKER.
3. **JSON parse errors**: `read_json()` raises `ArtifactError` on `json.JSONDecodeError` (no retry — content corruption is permanent) and on exhausted `OSError` retries.
4. **File operation retry**: `read_json()`/`write_json()` retry up to 3 times (default `retries=2, delay=0.5`) on `OSError` only. `json.JSONDecodeError` is not retried (ADR 0014).
5. **Defensive fallbacks**: `_count_sources()` uses `except (ArtifactError, OSError)` to return safe default (0). `detect_current_phase()` uses `except (ArtifactError, OSError)` when reading pipeline state.
6. **WARN vs BLOCKER**: Two-tier severity. `proceeds()` prints WARN to stderr but continues; BLOCKER stops the gate and returns error list.
7. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` prefixes.
8. **Explicit state file with fallback**: `detect_current_phase()` reads `pipeline_state.json` first (ADR 0019), falls back to artifact-presence heuristic. Invalid/corrupt state file → fallback silently.
9. **Subagent output sanitization**: `_sanitize_sections()` in proceed.py normalizes known field name variations and strips unknown keys, providing a safety net against subagent output drift (ADR 0017).
10. **Write-phase-state warns on failure**: `write_phase_state()` prints warning to stderr instead of silently passing on `OSError`.

---

## 11. Test Coverage Summary

| Module | Tests | Lines | Notable | Gaps |
|---|---|---|---|---|
| `cli.py` | 30 | 432 | All 6 commands; `_build_report_filename`; `_detect_quality` verdict parsing; project root detection; `InfoCollectorError` catch in main | `cmd_report` with incomplete scope.json |
| `artifact_checks.py` | 96 | 1,439 | All 18 checks with edge cases; precision_inflation; claim_verified with unverifiable + ratio; claim_source_relevance; fetched_content_depth; search_plan_compliance | None |
| `report_checks.py` | 44 | 435 | All 10 report checks + `run_report_checks` aggregator | None |
| `content_concreteness` | 29 | 322 | `_count_words` CJK segmentation; vague phrase detection; number/name presence; strict vs non-strict goal types | None |
| `exceptions` | 13 | 38 | Exception hierarchy + `ValidationError` equality | None |
| `gateway_import` | 1 | 36 | jieba not imported at module level; facade re-exports work correctly | None |
| `proceed.py` | 54 | 697 | Phase detection (state file + artifact fallback); 5 gate transitions + review self-loop; Chinese search directions; per-direction min sources; tier coverage; `covered_directions`; `_sanitize_sections` | `_generate_search_plan` output shape not tested |
| `reporter.py` | 42 | 597 | Reference map dedup; test conditions table; i18n labels (zh/en/fallback); full pipeline; `report_language` priority; tier star labels | Empty analysis.json not tested |
| `reporter_postprocess` | 18 | 77 | `_post_process`, bare URL fix, reference section detection | None |
| `source_router.py` | 21 | 175 | Route resolution; optional tiers; unknown goal_type fallback; min sources; depth priority; integration against real config.json | None |
| `utils.py` | 17 | 100 | URL normalization (8 cases); JSON read/write round-trip with retry; directory creation; ArtifactError on JSONDecodeError | Write permission errors not tested |
| `reset` | 10 | 102 | All 4 phase resets + phase detection + invalid + nothing-to-remove | No test for `search_plan.json` deletion on scope reset |
| `schemas` | 68 | 303 | Full scope/analysis/collected validation; `english_title` requirement; `covered_directions` constraints; `ValidationError` equality | None |
| **Total** | **443** | **~4,753** | | |

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
| Constants | All shared constants in `lib/constants.py`; only module-local constants (regex patterns, schema field whitelists) remain in their modules |

---

## 13. Known Issues and Gaps

1. **No schema library**: Validation is manual via `schemas.py` TypedDict definitions + hand-written validators. No Pydantic/dataclasses for schema enforcement — fragile if schemas evolve.
2. **Test gaps**: `cmd_gateway` only tests pass path; `_generate_search_plan` output shape untested; `cmd_report` incomplete scope.json untested.
3. **No concurrency**: All operations synchronous and sequential. SKILL.md says "parallel" section writing but code doesn't implement it.
4. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
5. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
6. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` or `reset` removes them.
7. **CJK word count approximation**: `_count_words` uses segment-based counting (continuous CJK chars = 1 word) rather than proper segmentation. This is a deliberate tradeoff (ADR 0012) — mitigated by `covered_directions` (ADR 0017) which provides an agent-declaration alternative to token-based matching.

---

## 14. ADR Index

| ADR | Title | Key Decision |
|---|---|---|
| 0001 | Topic coverage token matching | Use jieba for Chinese search direction tokenization (superseded by ADR 0012) |
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
| 0012 | Concreteness gate and CJK word counting | Add `check_content_concreteness` + `check_methodology_depth`; CJK segment-based word counting (not per-character); supersedes ADR 0001 (jieba removed) |
| 0013 | Source credibility and recommendation structure | Tier star labels in reports; `check_source_tier_balance` gate; `check_recommendation_structure` gate |
| 0014 | Custom exceptions and file operation retry | 3-level exception hierarchy; `read_json`/`write_json` retry on OSError only |
| 0015 | Centralized schema validation | TypedDict + `lib/schemas.py` with per-artifact validate functions; `ValidationError` dataclass |
| 0016 | Reset subcommand | `reset --phase <X>` CLI command to delete target phase and all subsequent artifacts |
| 0017 | covered_directions field and gate improvements | (1) `covered_directions` on collected entries overrides token matching; (2) `_sanitize_sections` normalizes subagent output; (3) precision_inflation degrades when source text <200 chars; (4) `reset --phase review` documentation; (5) `_detect_quality` parses review verdict |
| 0018 | CLI entry, report auto-fix, precision, URL | `cmd_report` entry; `_sanitize_sections` auto-fix; precision downgrade; URL bare-fix |
| 0019 | Pipeline state, self-loop, normalization, optional tiers, search tracking | (1) Explicit `pipeline_state.json`; (2) review→review self-loop; (3) number normalization in precision check; (4) optional_tiers in routes; (5) search_plan status tracking |
