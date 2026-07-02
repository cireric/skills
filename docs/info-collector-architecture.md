# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~2,546 lines (14 modules) |
| Tests | ~5,729 lines (15 files, 515 test functions) |
| Config/docs | config.json + SKILL.md + 6 reference docs + 29 ADRs |
| Runtime pip deps | None (jieba removed; ADR 0001 superseded by ADR 0012) |
| HTTP deps | None — search done externally by AI via exa/playwright |

---

## 2. File Listing

### Source Files

| # | Path | Lines | Purpose |
|---|---|---|---|
| 1 | `SKILL.md` | 217 | Skill definition: 3-phase workflow + Setup Wizard, CLI reference, quality values |
| 2 | `config.json` | — | 4-tier source config + 10 goal-type routes + output settings |
| 3 | `scripts/__init__.py` | 0 | Empty (package marker) |
| 4 | `scripts/__main__.py` | 4 | `python -m scripts` entry |
| 5 | `scripts/cli.py` | 243 | CLI entry: 6 subcommands, argparse, `sys.exit` on gate fail; catches `InfoCollectorError` |
| 6 | `scripts/artifact_checks.py` | 378 | Artifact-level quality gate checks: 9 check functions, `CheckResult` dataclass, `_read_artifact` helper, `_suggest_similar_urls` |
| 7 | `scripts/claim_validator.py` | 455 | Claim-level quality gate checks: `ClaimValidator` class with 8 checks + `apply_source_verification` write-back |
| 8 | `scripts/search_gate.py` | 323 | Search-phase gate checks: `SearchGate` class with 7 checks |
| 9 | `scripts/report_checks.py` | 283 | Report-level quality gate checks: 10 check functions on generated .md file |
| 10 | `scripts/proceed.py` | 326 | Phase transition gates, phase detection, `_sanitize_sections`, search plan generation |
| 11 | `scripts/reporter.py` | 274 | Markdown report generator: YAML front matter, i18n, references, tier star labels, verification summary |
| 12 | `scripts/lib/__init__.py` | 0 | Empty |
| 13 | `scripts/lib/constants.py` | 193 | Centralized constants: enumerations, thresholds, artifact filenames, pipeline config, labels |
| 14 | `scripts/lib/exceptions.py` | 22 | Custom exception hierarchy: `InfoCollectorError`, `GateFailureError`, `ArtifactError`; `ValidationError` dataclass |
| 15 | `scripts/lib/utils.py` | 96 | `normalize_url`, `read_json`/`write_json` (with retry), `find_project_root`, `config_path`, `tokenize_cjk_aware`, `build_collected_by_url`, `build_collected_url_set`, `ensure_dir` |
| 16 | `scripts/lib/source_router.py` | 74 | Pure-function routing: `get_route`, `recommend_sources`, defaults |
| 17 | `scripts/lib/schemas.py` | 200 | Centralized schema validation: TypedDict definitions + `validate_scope`, `validate_analysis`, `validate_collected` (ADR 0015) |
| 18 | `references/GATES.md` | — | Gate system reference |
| 19 | `references/REVIEW_PROMPT.md` | — | Review sub-agent prompt template |
| 20 | `references/cli-reference.md` | — | CLI commands reference |
| 21 | `references/subagent-template.md` | — | Subagent delegation template with JSON schema embedding |
| 22 | `references/writing-guide.md` | — | Writing guide for analysis.json content quality |
| 23 | `references/search-strategy.md` | — | Search strategy reference |

### Test Files

| # | Path | Lines | Tests | Coverage |
|---|---|---|---|---|
| 1 | `tests/conftest.py` | 3 | — | Adds skill dir to `sys.path` |
| 2 | `tests/__init__.py` | 0 | — | Empty |
| 3 | `tests/test_cli.py` | 432 | 30 | All 6 commands + project root detection + `_build_report_filename` + `_detect_review_status` verdict parsing + `InfoCollectorError` catch in main |
| 4 | `tests/test_gateway.py` | 653 | 46 | Artifact checks (artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, methodology_depth, recommendation_structure, source_tier_balance), `CheckResult`, `run_all` |
| 5 | `tests/test_claim_validator.py` | 901 | 48 | All 8 claim checks: claim_metadata, precision_inflation, source_metadata, metric_type_homogeneity, claim_dedup, ref_marker_validity, claim_source_ref_coverage, source_verification_check; `TestRefMarkerSuggestion` |
| 6 | `tests/test_search_gate.py` | 382 | 30 | All 7 search checks: collected_exists, collected_schema, min_sources, tier_coverage, topic_coverage, fetched_content_depth, search_plan_compliance |
| 7 | `tests/test_report_gateway.py` | 509 | 54 | All 10 report checks + `run_report_checks` aggregator + F1/F2/F9 BLOCKER upgrade |
| 8 | `tests/test_content_concreteness.py` | 322 | 29 | `_count_words`, vague phrase detection, number/name presence, CJK specifics |
| 9 | `tests/test_exceptions.py` | 38 | 13 | Exception hierarchy + `ValidationError` dataclass: equality, fields |
| 10 | `tests/test_proceed.py` | 912 | 55 | Phase detection (state file + artifact fallback) + gate routing + `_sanitize_sections` + review self-loop + `post_final` phase + cleanup transition rejected + gate analysis checks BLOCKERs + source verification write-back + review advisory-only |
| 11 | `tests/test_reporter.py` | 705 | 56 | Report pipeline + i18n + test conditions + reference numbering + tier labels + verification summary + `source_verification` markers |
| 12 | `tests/test_reporter_postprocess.py` | 77 | 18 | `_post_process`, bare URL fix, reference section detection |
| 13 | `tests/test_source_router.py` | 277 | 38 | Router functions + optional tiers + integration against real config.json + source language field + route adjustments |
| 14 | `tests/test_utils.py` | 100 | 17 | URL normalization + JSON I/O with retry + directory creation |
| 15 | `tests/test_reset.py` | 102 | 10 | Reset subcommand: scope/search/analysis/review reset, phase detection after reset, invalid phase |
| 16 | `tests/test_schemas.py` | 316 | 71 | Schema validation: scope, analysis, collected; english_title requirement; covered_directions; ValidationError equality; claim source_verification |

---

## 3. Data Flow

```
User input (topic, goal_type, depth, audience)
       |
       v
+-------------------------------------+
|  Phase 0: Pre-check                 |
|  Check for residual .workdir/       |
|  If exists → ask user to delete/keep|
|  If keep → abort pipeline           |
+---------------+---------------------+
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
    proceed --from search --to analysis  <-- Gate 2: search quality (SearchGate)
                |                           |-- collected_exists + schema (BLOCKER)
                |                           |-- topic_coverage (BLOCKER/WARN)
                |                           |   + covered_directions override (ADR 0017)
                |                           |-- fetched_content_depth (BLOCKER/WARN)
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
|           +- source_verification     |
|           +- verified (bool)         |
+---------------+---------------------+
                |
                v
    proceed --from analysis --to review  <-- Gate 3: schema + BLOCKERs only
                |                           |-- _sanitize_sections() normalizes output
                |                           |-- validate_analysis() schema check
                |                           |-- artifact BLOCKERs (url_traceability,
                |                           |   section_coverage, artifact_exists,
                |                           |   ref_marker_validity,
                |                           |   claim_source_ref_coverage)
                |                           |-- WARN checks printed but non-blocking
                |                           |-- INFO checks printed (source_verification)
                |                           +-- apply_source_verification() writes
                |                               source_verification + verified fields
                v
+-------------------------------------+
|  Phase 3b: Review (optional sub-agent)|
|  Review output: review_report.md     |
|  Overall Verdict: **pass** /         |
|    **pass_with_issues** / **fail**   |
+---------------+---------------------+
                |
                v
    proceed --from review --to final   <-- Gate 4: advisory-only (no BLOCKERs)
                |                         |-- All check results printed as [ADVISORY]
                |                         +-- Always passes (returns empty error list)
                v
+-------------------------------------+
|  Phase 3c: Final report generation  |
|  cli.py report --review-status ...   |
|    <-- reporter.py generates Markdown|
|  _detect_review_status() parses:     |
|    **pass** → "passed"               |
|    **pass_with_issues** → "degraded" |
|    **fail** → sys.exit(1)            |
|  Output: <output_dir>/<title>.md     |
|    (YAML front matter + numbered refs|
|     + verification summary + appendix|
|     + tier star labels)              |
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
|    (10 report checks: dangling refs, |
|    orphaned defs, refs visibility,   |
|    table delimiters, front matter,   |
|    heading levels, duplicate         |
|    headings, unclosed code blocks,   |
|    empty sections, overlong lines)   |
|  If any BLOCKER → fix .md → re-run  |
+---------------+---------------------+
                |
                v
        Pipeline terminates at post_final
        Manual cleanup: cli.py clean -> deletes .workdir/
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

Valid `current_phase` values: `pre_scope`, `post_scope`, `post_search`, `post_analysis`, `post_review`, `post_final`.

Invalid or corrupt state file → falls back to artifact detection (ADR 0019).

### Valid Transitions

```
scope -> search -> analysis -> review -> final
                                |
                                +-> review  (self-loop: re-validate after fixes)
```

Transition set is `_VALID_TRANSITIONS_SET` (set of tuples), defined in `lib/constants.py`. The `final -> cleanup` transition has been removed (ADR 0029); pipeline terminates at `post_final`. Use `cli clean` for manual cleanup.

---

## 4. API Surface — Function Reference

### 4.1 `scripts/cli.py` — CLI Entry Point (243 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > `"en"` |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `cmd_reset` | `(args: Namespace) -> None` | Reset pipeline to a given phase by deleting target and subsequent artifacts (ADR 0016) |
| `_detect_review_status` | `() -> str` | Parse `## Overall Verdict` in review_report.md: `**pass**` → "passed", `**pass_with_issues**` → "degraded", `**fail**` → sys.exit(1), unparseable → "degraded" |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_build_report_filename` | `(scope_data: dict, output_path: Path) -> Path` | Build safe ASCII report filename; prefers `english_title` over `topic`; appends `_YYYY-MM-DD` on collision |
| `main` | `() -> None` | Argparse setup + dispatch; catches `InfoCollectorError` at top level |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|review|final
gateway                    # Standalone gateway run
report [--review-status Q] [--search-rounds N] [--source-count N] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
reset --phase <X>          # X: scope|search|analysis|review — delete target + subsequent artifacts
```

**Module-level constants:**

| Name | Description |
|---|---|
| `WORKDIR` | `find_project_root() / ".workdir"` |
| `_CONFIG_PATH` | `config_path()` — delegates to `lib.utils.config_path()` |

### 4.2 `scripts/artifact_checks.py` — Artifact-Level Quality Gate Checks (378 lines)

**Data class:**

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN" | "INFO"
    passed: bool
    message: str = ""
```

**9 Check Functions:**

| Function | Level | Purpose |
|---|---|---|
| `check_artifact_exists` | BLOCKER | scope.json + collected.json + analysis.json must exist |
| `check_url_traceability` | BLOCKER | All claim source_urls must normalize-match collected.json URLs; includes "did you mean" suggestions for near-matches |
| `check_section_coverage` | BLOCKER | Required section IDs per goal_type (lookup table) |
| `check_analysis_schema` | BLOCKER/WARN | Delegates to `validate_analysis()` from schemas.py; warns on duplicate `## ` headings |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_content_concreteness` | WARN | Quantitative types: vague phrase density >10% or missing numbers/names |
| `check_methodology_depth` | WARN | Quantitative types: methodology section <150 words or lacks Markdown table |
| `check_recommendation_structure` | WARN | tech_selection/competitive_comparison: recommendation section lacks comparison table or "not recommended" |
| `check_source_tier_balance` | WARN | Quantitative types: Tier 1+2 source ratio <30% among referenced URLs |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]` — runs 9 artifact checks + delegates to `ClaimValidator.check()` for 8 claim-level checks

**Private helpers:** `_read_artifact`, `_suggest_similar_urls`, `_count_words`, `_has_valid_number`, `_has_concrete_name`

### 4.3 `scripts/claim_validator.py` — Claim-Level Quality Gate Checks (455 lines)

**Class: `ClaimValidator`**

```python
class ClaimValidator:
    def __init__(self, workdir: Path, goal_type: str) -> None: ...
    def check(self) -> list[CheckResult]: ...
```

Reads analysis.json + collected.json once in `__init__`, then `check()` runs all 8 claim-level validations.

**8 Check Methods:**

| Method | Level | Purpose |
|---|---|---|
| `_check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `_check_precision_inflation` | WARN | Exact precision + wrong evidence_type; third_party + unverified precise numbers; conflicting exact values in same metric_type (data_variance) |
| `_check_source_metadata` | WARN | official_data/independent_benchmark claims missing or have empty source_metadata.test_conditions |
| `_check_metric_type_homogeneity` | WARN | Mixing different metric_types within same section level (only checks claims with evidence_type in official_data/independent_benchmark) |
| `_check_claim_dedup` | WARN | Same claim text appears in multiple sections |
| `_check_ref_marker_validity` | BLOCKER | `{{ref:URL}}` markers in content must reference URLs in collected.json; includes "did you mean" suggestions |
| `_check_claim_source_ref_coverage` | BLOCKER | All claim source_urls must be referenced in section content via `{{ref:URL}}` markers |
| `_check_source_verification` | INFO | Computes source_verification (source_confirmed/source_absent/source_indirect) for each claim; never blocks |

**Standalone function:** `apply_source_verification(workdir: Path) -> None` — writes `source_verification` and `verified` fields back to analysis.json

**Private helpers:** `_source_text`, `_normalize_numbers`, `_number_found_in_source`, `_is_indirect_source`, `_extract_indirect_entity`, `_entity_matches_host`, `_check_data_variance`, `_compute_source_verification`

**Module-level regex:** `_PRECISE_NUMBER_PATTERN`, `_REF_MARKER_RE`

### 4.4 `scripts/search_gate.py` — Search-Phase Gate Checks (323 lines)

**Class: `SearchGate`**

```python
class SearchGate:
    def __init__(self, workdir: Path, config: dict | None = None) -> None: ...
    def check(self) -> list[CheckResult]: ...
```

**7 Check Methods:**

| Method | Level | Purpose |
|---|---|---|
| `_check_collected_exists` | BLOCKER | collected.json must exist and have >=1 entry |
| `_check_collected_schema` | BLOCKER | `schemas.validate_collected()` validates entry structure |
| `_check_min_sources` | WARN | Total collected entries >= goal_type default (fallback 2) |
| `_check_tier_coverage` | WARN | All required tiers in route must have >=1 source; optional tiers produce INFO only |
| `_check_topic_coverage` | BLOCKER/WARN | Token-based direction coverage; CJK directions downgrade to WARN; `covered_directions` override; includes per-direction min_sources |
| `_check_fetched_content_depth` | BLOCKER/WARN | >30% stub/empty entries = BLOCKER; otherwise WARN per tier minimum |
| `_check_search_plan_compliance` | WARN | Pending tasks in search_plan.json |

### 4.5 `scripts/report_checks.py` — Report-Level Quality Gate Checks (283 lines)

All functions operate on the generated `.md` report file.

| Function | Level | Purpose |
|---|---|---|
| `check_report_dangling_refs` | BLOCKER | In-text [N] has no matching definition in References |
| `check_report_orphaned_defs` | BLOCKER | Reference definition [N]: not cited in text |
| `check_report_refs_visibility` | WARN | References use visible format, not hidden `[N]: URL` definitions |
| `check_report_table_delimiters` | WARN | Markdown tables have correct `|---|` delimiter rows |
| `check_report_front_matter` | BLOCKER | YAML front matter exists and is well-formed |
| `check_report_heading_levels` | WARN | No heading level skips (e.g., `##` → `####`) |
| `check_report_duplicate_headings` | WARN | No duplicate heading text at same level |
| `check_report_unclosed_code_blocks` | WARN | All fenced code blocks are properly closed |
| `check_report_empty_sections` | WARN | No sections with empty content |
| `check_report_overlong_lines` | WARN | No lines exceeding 500 characters |

**Aggregator:** `run_report_checks(report_path) -> list[CheckResult]`

**Private helpers:** `_strip_front_matter`, `_find_references_section`, `_extract_defined_nums`, `_extract_cited_nums`

### 4.6 `scripts/proceed.py` — Phase Transition Gates (326 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_sanitize_sections` | `(analysis: dict, collected_urls: set[str] \| None = None) -> dict` | Normalize subagent output: `section_id` → `id`, `sources` → `source_urls`, strip non-schema keys, default `claims` to `[]`; auto-downgrade `precision: exact` → `range` for `_NON_EXACT_EVIDENCE_TYPES`; auto-fix URL traceability if `collected_urls` provided (ADR 0017) |
| `write_phase_state` | `(workdir: Path, phase: str) -> None` | Write current phase to `pipeline_state.json`; warns on failure instead of silent pass |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from `pipeline_state.json` first, then artifact presence fallback (ADR 0019). Recognizes `post_final` |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json via `schemas.validate_scope()` |
| `_generate_search_plan` | `(workdir: Path, config?) -> None` | Write search_plan.json with direction x tier tasks, per-source language split |
| `_build_fetch_hints` | `(sources: list[dict]) -> str` | Generate fetch hints for arXiv/GitHub sources |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `_find_report_path` | `(workdir: Path) -> Path \| None` | Find latest .md report in configured output directory |
| `_gate_scope` | `(workdir, config?) -> list[str]` | Scope gate: schema check + search plan generation |
| `_gate_search` | `(workdir, config?) -> list[str]` | Search gate: delegates to `SearchGate.check()` |
| `_gate_analysis` | `(workdir) -> list[str]` | Analysis gate: sanitize + schema + BLOCKER-only artifact checks + INFO printing + `apply_source_verification` write-back |
| `_gate_review` | `(workdir) -> list[str]` | Review gate: advisory-only — prints all results as `[ADVISORY]`, always returns empty list |
| `_gate_final` | `(workdir) -> list[str]` | Final gate: report checks via `run_report_checks`; only BLOCKERs block |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions via `_VALID_TRANSITIONS_SET` + runs phase-specific gates via dispatch table |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `run_all()` |

**Depth -> Min Sources Per Direction:** `quick=1`, `standard=3`, `deep=5`

**Module-level constants:**

| Name | Value |
|---|---|
| `_SECTION_KEYS` | `frozenset({"id", "title", "content", "claims"})` |
| `_CLAIM_KEYS` | `frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified", "source_verification"})` |

### 4.7 `scripts/reporter.py` — Report Generator (274 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_resolve_ref_markers` | `(content, ref_map, sv_map?) -> str` | Replace `{{ref:URL}}` with `[N†/‡](#refs)` links; appends source_verification markers (†=absent, ‡=indirect) |
| `_build_sv_map` | `(analysis: dict) -> dict[str, str]` | Build `{normalized_url -> worst source_verification}` across all claims |
| `_render_verification_summary` | `(analysis, lang) -> str` | Generate verification note + status table (confirmed/indirect/absent) |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix with tier star labels (★★★☆) |
| `_clean_url` | `(url: str) -> str` | Remove preview- prefix and other non-standard URL prefixes |
| `_post_process` | `(markdown: str) -> str` | Fix bare URLs in body (not in reference section); fix literal `\n`; fix preview- URLs |
| `build_front_matter` | `(topic, goal_type, scope, review_status, search_rounds, source_count, audience?, report_language?) -> str` | YAML front matter block (8-12 fields including `verification_required: true`) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `_build_claim_ref` | `(claim, reference_map) -> str` | Build `[N]` reference number from normalized URL |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body; exploratory types use compact mode (claims omitted); includes verification summary |
| `generate_report` | `(analysis_path, scope_path, review_status, search_rounds, source_count, report_language?) -> str` | Main entry: reads files, builds front matter + body |

**i18n Labels (8 pairs):** Sources/数据来源, References/参考文献, Test Conditions/测试环境, Claim/声明, Conditions/条件, Date/日期, Source Type/来源类型, Methodology/方法论

**Tier Star Labels:** Tier 1 → ★★★☆, Tier 2 → ★★☆☆, Tier 3 → ★☆☆☆, Tier 4 → ☆☆☆☆

**Source Verification Markers:** source_absent → †, source_indirect → ‡

### 4.8 `scripts/lib/source_router.py` — Source Routing (74 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_get_config` | `(config?) -> dict` | Return injected config or load from disk via `config_path()` |
| `get_route` | `(goal_type, config?) -> dict` | Return route dict (entry_tier, path, optional_tiers); unknown -> "other" |
| `recommend_sources` | `(goal_type, config?) -> dict` | Structured output with recommended/all sources (includes optional_tiers) |
| `get_default_min_sources` | `(goal_type, config?) -> int` | Lookup from goal_type_defaults, fallback 2 |
| `get_default_depth` | `(goal_type, config?) -> str` | Priority: goal_type_defaults > config.default_depth > "standard" |

### 4.9 `scripts/lib/utils.py` — Utilities (96 lines)

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
| `build_collected_url_set` | `(collected: list[dict]) -> set[str]` | Build `{normalized_url}` set from collected list |

### 4.10 `scripts/lib/constants.py` — Centralized Constants (193 lines)

Single source of truth for all enumerations, thresholds, and classification sets.

| Category | Constants |
|---|---|
| Stop words | `_ENGLISH_STOP_WORDS` (37), `_CHINESE_STOP_WORDS` (49) |
| Enumerations | `_VALID_GOAL_TYPES` (10), `_VALID_DEPTHS` (3), `_VALID_AUDIENCES` (4), `_VALID_METRIC_TYPES` (6), `_VALID_EVIDENCE_TYPES` (5), `_VALID_CONFIDENCE` (3), `_VALID_PRECISION` (3), `_VALID_SOURCE_VERIFICATIONS` (3) |
| Cross-constraints | `_NON_EXACT_EVIDENCE_TYPES`, `_VENDOR_SOURCE_TYPES` (4), `_INDIRECT_CITATION_PATTERNS` (3 regex) |
| Goal-type classifications | `_QUANTITATIVE_GOAL_TYPES` (5), `_EXPLORATORY_GOAL_TYPES` (4) |
| Thresholds | `_VAGUE_DENSITY_THRESHOLD` (0.10), `_TIER_BALANCE_THRESHOLD` (0.30), `_METHODOLOGY_MIN_WORDS` (150), `_MIN_SOURCES` (2), `_FETCHED_CONTENT_MIN_LENGTH` (200), `_FETCHED_CONTENT_STUB_RATIO_BLOCKER` (0.30), `_FETCHED_CONTENT_MIN_BY_TIER` ({1:1000, 2:800, 3:600, 4:400}), `_DEPTH_MIN_SOURCES_PER_DIRECTION` (quick=1/standard=3/deep=5), `_COVERAGE_THRESHOLD` (0.5), `_OVERLONG_LINE_THRESHOLD` (500), `_SINGLE_SOURCE_RATIO` (0.5), `_SOURCE_INDIRECT_RATIO_WARN` (0.30), `_MAX_COVERED_DIRECTIONS` (3) |
| Vague phrases | `_VAGUE_PHRASES_ZH` (12), `_VAGUE_PHRASES_EN` (10) |
| Required sections | `_REQUIRED_SECTION_IDS` (6 goal types) |
| Artifact filenames | `ARTIFACT_SCOPE`, `ARTIFACT_COLLECTED`, `ARTIFACT_ANALYSIS`, `ARTIFACT_SEARCH_PLAN`, `ARTIFACT_PIPELINE_STATE`, `ARTIFACT_REVIEW_REPORT`, `ARTIFACT_REVIEW_FALLBACK_LOG`, `ARTIFACT_CONFIG` |
| Pipeline config | `_VALID_TRANSITIONS_SET` (5 transitions incl. review→review, no final→cleanup), `_PHASE_ARTIFACTS` (5 phases: scope/search/analysis/review/final) |
| Display labels | `_TIER_LABELS` (4 tiers), `_LABELS` (8 key × 2 languages) |

### 4.11 `scripts/lib/exceptions.py` — Custom Exceptions + ValidationError (22 lines)

| Class | Base | Attributes | Purpose |
|---|---|---|---|
| `InfoCollectorError` | `Exception` | — | Base exception for all info-collector errors |
| `GateFailureError` | `InfoCollectorError` | `phase: str`, `blockers: list[str]` | Gate check failed with BLOCKER-level issues |
| `ArtifactError` | `InfoCollectorError` | `path: str`, `reason: str` | Artifact file missing, unreadable, or schema-invalid |
| `ValidationError` | `@dataclass` (not Exception) | `field: str`, `message: str` | Schema validation error carrier (ADR 0015) |

### 4.12 `scripts/lib/schemas.py` — Centralized Schema Validation (200 lines)

**TypedDict definitions:**

| Name | Fields |
|---|---|
| `ScopeDict` | topic, goal_type, depth, audience, scope_description, search_directions, report_language, english_title |
| `ClaimDict` | text, source_urls, evidence_type, confidence, precision, metric_type, source_metadata, verified, source_verification |
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
- **Generates**: `search_plan.json` with direction x tier x language search tasks

### Gate 2: Search -> Analysis

| Check | Level | Logic |
|---|---|---|
| collected_exists | BLOCKER | collected.json must exist and have >=1 entry |
| collected_schema | BLOCKER | `schemas.validate_collected()` validates entry structure + covered_directions constraints |
| topic_coverage | BLOCKER (non-CJK) / WARN (CJK) | Two-pass: (1) entries with `covered_directions` override token matching; (2) remaining entries use `tokenize_cjk_aware` token matching. CJK-heavy directions downgrade to WARN. Includes per-direction min_sources |
| fetched_content_depth | BLOCKER/WARN | >30% stub/empty entries = BLOCKER; otherwise WARN per tier minimum |
| tier_coverage | WARN | All required tiers in goal_type route must have >=1 source in collected.json; optional tiers produce INFO only |
| per_direction_min_sources | WARN | Depth-driven: quick=1, standard=3, deep=5 per direction |
| search_plan_compliance | WARN | Pending tasks in search_plan.json |
| min_sources | WARN | Total collected entries >= goal_type default (fallback 2) |

### Gate 3: Analysis -> Review

- `_sanitize_sections()` normalizes subagent output: `section_id` → `id`, `sources` → `source_urls`, strips non-schema keys, defaults `claims` to `[]`; auto-downgrades `precision: exact` → `range` for `_NON_EXACT_EVIDENCE_TYPES`; auto-fixes URL traceability if `collected_urls` provided
- `schemas.validate_analysis()` validates structure
- Runs `run_all()` gateway checks, but only BLOCKER-level failures in analysis-phase checks block the transition
- **Analysis-phase BLOCKERs**: artifact_exists, url_traceability, section_coverage, ref_marker_validity, claim_source_ref_coverage
- **WARN checks**: printed to stderr but non-blocking (precision_inflation, source_metadata, metric_type_homogeneity, content_concreteness, claim_metadata, claim_dedup, methodology_depth, recommendation_structure, source_tier_balance, quality_heuristics)
- **INFO checks**: printed to stderr (source_verification_check)
- `apply_source_verification()` writes `source_verification` and `verified` fields to analysis.json

### Gate 4: Review -> Final

Advisory-only — all check results are printed as `[ADVISORY]` and the gate always passes (returns empty error list). The review subagent's role is informational, not gate-blocking.

### Gate 5: Final (Report Verification)

10-check report gateway on the generated `.md` file. Only BLOCKER-level failures block.

**Report BLOCKERs** (ADR 0026):

- `report_dangling_refs`: In-text citation with no source definition
- `report_orphaned_defs`: Source definition with no in-text citation
- `report_front_matter`: Missing or malformed YAML front matter

**Report WARNs**: refs visibility, table delimiters, heading levels, duplicate headings, unclosed code blocks, empty sections, overlong lines

### Review Status Values

| Value | Condition |
|---|---|
| `passed` | `review_report.md` has `## Overall Verdict` with `**pass**` |
| `degraded` | Auto-assigned when verdict is `**pass_with_issues**` or unparseable; also settable via `--review-status degraded` |
| `unreviewed` | `review_report.md` does not exist |

### Gate Philosophy (ADR 0029)

The gate system follows an "auto-downgrade suspicious metadata + honestly mark" philosophy:

- **BLOCKERs** (11 total) are reserved for **structural integrity** checks — things that code can verify deterministically (artifact existence, URL traceability, schema validity, section coverage)
- **WARN** checks flag **quality concerns** that deserve attention but don't block the pipeline — they are honest markers, not forced LLM judgment
- **INFO** checks provide **observability** without any judgment (e.g., source_verification_check)
- Previously BLOCKER checks that required LLM judgment (precision_inflation data_variance, source_metadata, metric_type_homogeneity, content_concreteness strict types) have been downgraded to WARN
- `claim_verified` check has been removed entirely — the `verified` field is now set deterministically by `source_verification_check()` code, not by the review subagent

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
            "test_conditions": "string (WARN if missing/empty for official_data/independent_benchmark claims)"
          },
          "source_verification": "source_confirmed | source_absent | source_indirect (set by apply_source_verification, never by LLM)",
          "verified": "bool (set by apply_source_verification: true if source_confirmed or source_indirect, false if source_absent)"
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
      "fetch_hints": "string (optional)",
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
  "current_phase": "pre_scope | post_scope | post_search | post_analysis | post_review | post_final"
}
```

---

## 8. Constants Reference

### lib/constants.py — Single Source of Truth

All constants previously scattered across modules are now centralized here. Only module-local constants (regex patterns, schema field whitelists) remain in their respective modules.

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
_VALID_SOURCE_VERIFICATIONS = frozenset({"source_confirmed", "source_absent", "source_indirect"})
_VENDOR_SOURCE_TYPES = frozenset({"analyst_forecast", "vendor_benchmark", "vendor_survey", "vendor_blog"})
_INDIRECT_CITATION_PATTERNS = (...)       # 3 compiled regex

# Goal-type classifications
_QUANTITATIVE_GOAL_TYPES = frozenset({...})  # 5 types
_EXPLORATORY_GOAL_TYPES = frozenset({...})   # 4 types

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
_SOURCE_INDIRECT_RATIO_WARN = 0.30
_MAX_COVERED_DIRECTIONS = 3

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
ARTIFACT_REVIEW_FALLBACK_LOG = "review_fallback.log"
ARTIFACT_CONFIG = "config.json"

# Pipeline configuration
_VALID_TRANSITIONS_SET = {
    ("scope", "search"), ("search", "analysis"), ("analysis", "review"),
    ("review", "final"), ("review", "review"),
}
_PHASE_ARTIFACTS = {...}                  # 5 phases

# Display labels
_TIER_LABELS = {...}                      # 4 tiers
_LABELS = {...}                           # 8 key × 2 languages
```

### claim_validator.py — Module-local constants

```python
_PRECISE_NUMBER_PATTERN = re.compile(...)
_REF_MARKER_RE = re.compile(r'\{\{ref:(.*?)\}\}')
```

### artifact_checks.py — Module-local constants

```python
_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')
_VERSION_PATTERN = re.compile(...)
_LIST_ITEM_PATTERN = re.compile(...)
_NUMBER_PATTERN = re.compile(...)
```

### proceed.py — Module-local constants

```python
_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified", "source_verification"})
```

### search_gate.py — Module-local constants

```python
_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS   # from lib.constants
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

proceed.py -> lib.utils (config_path, find_project_root, ensure_dir, read_json, build_collected_url_set, write_json)
           -> artifact_checks (CheckResult, run_all as run_gateway)
           -> report_checks (run_report_checks)
           -> search_gate (SearchGate)
           -> lib.source_router (get_route, recommend_sources)
           -> lib.exceptions (ArtifactError)
           -> lib.constants (ARTIFACT_*, _NON_EXACT_EVIDENCE_TYPES, _VALID_TRANSITIONS_SET)
           -> lib.schemas (lazy import: validate_scope, validate_analysis, validate_collected)
           -> claim_validator (lazy import: apply_source_verification)

artifact_checks.py -> lib.constants (13 constants)
                   -> lib.exceptions (ArtifactError)
                   -> lib.utils (build_collected_by_url, build_collected_url_set, normalize_url, read_json, tokenize_cjk_aware)
                   -> lib.schemas (lazy import: validate_analysis)
                   -> claim_validator (lazy import: ClaimValidator)

claim_validator.py -> artifact_checks (CheckResult, _read_artifact)
                   -> lib.constants (ARTIFACT_ANALYSIS, ARTIFACT_COLLECTED, _INDIRECT_CITATION_PATTERNS, _QUANTITATIVE_GOAL_TYPES, _SINGLE_SOURCE_RATIO, _VENDOR_SOURCE_TYPES)
                   -> lib.exceptions (ArtifactError)
                   -> lib.utils (build_collected_by_url, build_collected_url_set, normalize_url, read_json)
                   -> lib.constants (lazy import: ARTIFACT_SCOPE)
                   -> lib.utils (lazy import: read_json, write_json)

search_gate.py -> artifact_checks (CheckResult, _read_artifact)
               -> lib.constants (ARTIFACT_*, _CHINESE_STOP_WORDS, _COVERAGE_THRESHOLD, _DEPTH_MIN_SOURCES_PER_DIRECTION, _ENGLISH_STOP_WORDS, _FETCHED_CONTENT_*, _MAX_COVERED_DIRECTIONS)
               -> lib.exceptions (ArtifactError)
               -> lib.source_router (get_default_min_sources, get_route)
               -> lib.utils (read_json, tokenize_cjk_aware)
               -> lib.schemas (lazy import: validate_collected)

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

**External deps:** `argparse` (cli.py), `dataclasses` (artifact_checks.py, exceptions.py), `re` (cli.py, artifact_checks.py, claim_validator.py, report_checks.py, reporter.py), `string` (search_gate.py), `time` (utils.py), `urllib.parse` (claim_validator.py, utils.py), `typing` (proceed.py, schemas.py, source_router.py, utils.py)

---

## 10. Error Handling Patterns

1. **Custom exception hierarchy**: `InfoCollectorError` base → `GateFailureError` (gate failures) + `ArtifactError` (file I/O). Top-level `cli.py:main()` catches `InfoCollectorError` uniformly. `ValidationError` is a dataclass (not an Exception) used by schemas.py for validation results.
2. **Gate-based error handling**: BLOCKERs are terminal via `sys.exit(1)`. WARNs are printed but non-blocking. INFOs are printed for observability. The review gate is advisory-only and never blocks.
3. **JSON parse errors**: `read_json()` raises `ArtifactError` on `json.JSONDecodeError` (no retry — content corruption is permanent) and on exhausted `OSError` retries.
4. **File operation retry**: `read_json()`/`write_json()` retry up to 3 times (default `retries=2, delay=0.5`) on `OSError` only. `json.JSONDecodeError` is not retried (ADR 0014).
5. **Defensive fallbacks**: `_count_sources()` uses `except (ArtifactError, OSError)` to return safe default (0). `detect_current_phase()` uses `except (ArtifactError, OSError)` when reading pipeline state.
6. **Three-tier severity**: BLOCKER (blocks pipeline), WARN (printed, non-blocking), INFO (printed for observability). `proceeds()` returns errors for BLOCKERs only.
7. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` / `[INFO]` / `[ADVISORY]` prefixes.
8. **Explicit state file with fallback**: `detect_current_phase()` reads `pipeline_state.json` first (ADR 0019), falls back to artifact-presence heuristic. Invalid/corrupt state file → fallback silently. Recognizes `post_final` phase.
9. **Subagent output sanitization**: `_sanitize_sections()` in proceed.py normalizes known field name variations, strips unknown keys, and auto-downgrades `precision: exact` → `range` for non-official evidence types, providing a safety net against subagent output drift (ADR 0017).
10. **Write-phase-state warns on failure**: `write_phase_state()` prints warning to stderr instead of silently passing on `OSError`.
11. **Deterministic verification**: `verified` and `source_verification` fields are set by `apply_source_verification()` code, not by the review subagent. This eliminates the "force LLM judgment" pattern (ADR 0029).

---

## 11. Test Coverage Summary

| Module | Tests | Lines | Notable | Gaps |
|---|---|---|---|---|
| `cli.py` | 30 | 432 | All 6 commands; `_build_report_filename`; `_detect_review_status` verdict parsing; project root detection; `InfoCollectorError` catch in main | `cmd_report` with incomplete scope.json |
| `artifact_checks.py` | 46 | 653 | 9 artifact checks + `CheckResult` + `run_all`; `_suggest_similar_urls` via `TestCheckUrlTraceability` | None |
| `claim_validator.py` | 48 | 901 | All 8 claim checks + edge cases; precision_inflation (WARN); source_metadata (WARN); metric_type_homogeneity (WARN); source_verification (INFO); ref_marker suggestions; `TestNumberNormalization`; `TestRefMarkerSuggestion` | None |
| `search_gate.py` | 30 | 382 | All 7 search checks + CJK downgrade + per-direction min sources + tier coverage + fetched content depth + search plan compliance | None |
| `report_checks.py` | 54 | 509 | All 10 report checks + `run_report_checks` aggregator + F1/F2/F9 BLOCKER upgrade + inline citation with markers | None |
| `content_concreteness` | 29 | 322 | `_count_words` CJK segmentation; vague phrase detection; number/name presence | None |
| `exceptions` | 13 | 38 | Exception hierarchy + `ValidationError` equality | None |
| `proceed.py` | 55 | 912 | Phase detection (state file + artifact fallback + `post_final`); gate routing; `_sanitize_sections`; review self-loop; cleanup transition rejected; gate analysis checks BLOCKERs; source verification write-back; review advisory-only | `_generate_search_plan` output shape not tested |
| `reporter.py` | 56 | 705 | Reference map dedup; test conditions table; i18n labels; full pipeline; verification summary; `source_verification` markers; front matter repositioning | Empty analysis.json not tested |
| `reporter_postprocess` | 18 | 77 | `_post_process`, bare URL fix, reference section detection | None |
| `source_router.py` | 38 | 277 | Route resolution; optional tiers; unknown goal_type fallback; min sources; depth priority; integration against real config.json; source language field; route adjustments | None |
| `utils.py` | 17 | 100 | URL normalization (8 cases); JSON read/write round-trip with retry; directory creation; ArtifactError on JSONDecodeError | Write permission errors not tested |
| `reset` | 10 | 102 | All 4 phase resets + phase detection + invalid + nothing-to-remove | No test for `search_plan.json` deletion on scope reset |
| `schemas` | 71 | 316 | Full scope/analysis/collected validation; `english_title` requirement; `covered_directions` constraints; `ValidationError` equality; claim source_verification | None |
| **Total** | **515** | **~5,729** | | |

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
| Deep modules | `ClaimValidator`, `SearchGate` are class-based deep modules that load data once and expose a `check()` method; `artifact_checks` remains function-based for simpler checks |

---

## 13. Known Issues and Gaps

1. **No schema library**: Validation is manual via `schemas.py` TypedDict definitions + hand-written validators. No Pydantic/dataclasses for schema enforcement — fragile if schemas evolve.
2. **Test gaps**: `_generate_search_plan` output shape untested; `cmd_report` incomplete scope.json untested.
3. **No concurrency**: All operations synchronous and sequential. SKILL.md says "parallel" section writing but code doesn't implement it.
4. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
5. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
6. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` or `reset` removes them.
7. **CJK word count approximation**: `_count_words` uses segment-based counting (continuous CJK chars = 1 word) rather than proper segmentation. This is a deliberate tradeoff (ADR 0012) — mitigated by `covered_directions` (ADR 0017) which provides an agent-declaration alternative to token-based matching.
8. **`_SOURCE_INDIRECT_RATIO_WARN` constant unused**: The constant (0.30) exists in constants.py but is not currently imported or used by any module. Retained for potential future use.

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
| 0020 | Claim source relevance gate | Flag claims whose source text doesn't contain the claim's key numbers/names |
| 0021 | Report rendering verification step | Final→cleanup transition runs report checks on generated .md |
| 0022 | Deepen search gate into SearchGate module | Extract search gate logic into `SearchGate` class |
| 0023 | Remove gateway re-export layer | Delete `gateway.py`; import directly from `artifact_checks` and `report_checks` |
| 0024 | Deepen claim validation into ClaimValidator module | Extract claim checks into `ClaimValidator` class |
| 0025 | Gate phase responsibility split | Each gate checks only its own phase's concerns; analysis gate excludes claim_verified and claim_source_relevance |
| 0026 | F1/F2/F9 BLOCKER upgrade | Upgrade dangling refs, orphaned defs, and front matter to BLOCKER in report checks |
| 0027 | PR-001 design decisions | Review subagent no longer sets verified; `claim_verified` check level reduced |
| 0028 | Repositioning to research starting point | Pipeline output is a starting point, not a citable authority; verification summary in report |
| 0029 | Gate philosophy shift | Auto-downgrade suspicious metadata + honestly mark: precision_inflation all WARN, source_metadata WARN, metric_type_homogeneity WARN, content_concreteness unified WARN, source_verification INFO, claim_verified removed, Phase 4 removed, URL traceability "did you mean" suggestions |
