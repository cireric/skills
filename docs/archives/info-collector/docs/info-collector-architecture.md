# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~4,395 lines (27 modules) |
| Tests | ~9,752 lines (25 files, 897 test functions) |
| Config/docs | config.json + SKILL.md + 8 reference docs + 63 ADRs |
| Runtime pip deps | None (jieba removed; ADR 0001 superseded by ADR 0012) |
| HTTP deps | None — search done externally by AI via exa/playwright |

---

## 2. File Listing

### Source Files

| # | Path | Lines | Purpose |
|---|---|---|---|
| 1 | `SKILL.md` | 120 | Skill definition: 4-phase workflow, architecture constraints, execution freedom, CLI reference |
| 2 | `config.json` | — | 4-tier source config (38 sources) + 10 goal-type routes + fetch_defaults + output settings |
| 3 | `scripts/__init__.py` | 0 | Empty (package marker) |
| 4 | `scripts/__main__.py` | 8 | `python -m scripts` entry; forces UTF-8 mode on Windows (ADR 0048) |
| 5 | `scripts/cli.py` | 255 | CLI entry: 8 subcommands (proceed, gateway, report, source, clean, reset, fetch, batch-fetch), argparse, `InfoCollectorError` catch |
| 6 | `scripts/proceed.py` | 534 | Phase transition gates, phase detection, JSON repair, section merge, trust boundary validation, URL consistency checks |
| 7 | `scripts/search_gate.py` | 313 | SearchGate deep module: 7 checks (collected_exists, collected_schema, min_sources, tier_coverage, source_fidelity, direction_tagging, direction_coverage) |
| 8 | `scripts/claim_validator.py` | 584 | ClaimValidator deep module: 11 claim-level checks + `apply_source_verification` write-back |
| 9 | `scripts/artifact_checks.py` | 618 | Artifact-level gateway checks: 15 check functions + `run_all` aggregator |
| 10 | `scripts/reporter.py` | 272 | Markdown report generator: YAML front matter, i18n, reference numbering, tier star labels, verification summary, test conditions table |
| 11 | `scripts/report_checks.py` | 251 | Report-level checks: 10 checks on generated .md file (3 BLOCKER + 7 WARN) |
| 12 | `scripts/trust_boundary.py` | 113 | Trust boundary validation (ADR 0053): structural + semantic validation of subagent output |
| 13 | `scripts/repair_loop.py` | 107 | Repair loop logic (ADR 0055): parse fix_report.json, determine review_status, re-merge after fix |
| 14 | `scripts/sanitizer.py` | 78 | Output sanitizer: normalizes subagent field names, auto-downgrades precision, strips unknown keys, fixes URL traceability |
| 15 | `scripts/fetcher.py` | 201 | Fetch execution engine: Fetcher class with autonomous fetch (requests+markdownify, Playwright) and pipe mode, FetchResult dataclass |
| 16 | `scripts/fetch_router.py` | 69 | Fetch strategy router: resolves FetchStrategy from config; ComposedStrategy, ConfigRewriteStrategy, DefaultStrategy |
| 17 | `scripts/fetch_cleaner.py` | 54 | Content cleaner: strips cookie banners, social sharing, breadcrumbs, comments/related sections, HTML nav/footer/aside |
| 18 | `scripts/batch_fetch.py` | 184 | Batch fetch CLI (ADR 0041): process multiple URLs from stdin, update collected.json automatically |
| 19 | `scripts/fetch_strategies/__init__.py` | 5 | Re-exports FetchStrategy, UrlRewriter, DefaultStrategy, ArxivStrategy, GithubStrategy |
| 20 | `scripts/fetch_strategies/base.py` | 8 | Protocol definitions: UrlRewriter (rewrite_url), FetchStrategy (rewrite_url + tools + retries) |
| 21 | `scripts/fetch_strategies/default.py` | 8 | DefaultStrategy: no URL rewrite, tools=["webfetch"], tier-based retries |
| 22 | `scripts/fetch_strategies/arxiv.py` | 11 | ArxivStrategy: rewrites arxiv.org/pdf/ and /abs/ to ar5iv.labs.arxiv.org/html/ |
| 23 | `scripts/fetch_strategies/github.py` | 14 | GithubStrategy: rewrites bare repo URLs to README.md |
| 24 | `scripts/lib/__init__.py` | 0 | Empty |
| 25 | `scripts/lib/constants.py` | 202 | Single source of truth: all enumerations, thresholds, artifact filenames, pipeline config, display labels |
| 26 | `scripts/lib/schemas.py` | 275 | Centralized schema validation (ADR 0015): TypedDict definitions + validate_scope/validate_analysis/validate_collected |
| 27 | `scripts/lib/exceptions.py` | 22 | Exception hierarchy: InfoCollectorError, GateFailureError, ArtifactError; ValidationError dataclass |
| 28 | `scripts/lib/utils.py` | 110 | Utilities: normalize_url, read_json/write_json (with retry), find_project_root, config_path, CJK tokenization, URL set builders, compute_url_hash, suggest_similar_urls |
| 29 | `scripts/lib/source_router.py` | 74 | Pure-function routing: get_route, recommend_sources, get_default_min_sources, get_default_depth |
| 30 | `scripts/lib/check_types.py` | 25 | CheckResult dataclass + read_artifact helper (ADR 0061) |

### Reference Documents

| # | Path | Purpose |
|---|---|---|
| 1 | `references/writing-guide.md` | Content quality guide (false depth, synthesis guard, precision rules) |
| 2 | `references/subagent-template.md` | Subagent delegation template with JSON schema |
| 3 | `references/search-strategy.md` | Search strategy reference |
| 4 | `references/GATES.md` | Gate system reference |
| 5 | `references/cli-reference.md` | CLI commands reference |
| 6 | `references/REVIEW_PROMPT.md` | Review subagent prompt |
| 7 | `references/REVIEW_FIX_PROMPT.md` | Review-fix subagent prompt |
| 8 | `references/LIGHTWEIGHT_REVIEW_PROMPT.md` | Lightweight review prompt |

### Test Files

| # | Path | Lines | Tests | Coverage |
|---|---|---|---|---|
| 1 | `tests/conftest.py` | 3 | — | Adds skill dir to `sys.path` |
| 2 | `tests/test_proceed.py` | 1308 | 102 | Phase detection, gate routing, merge, trust boundary, review, JSON repair, section ordering |
| 3 | `tests/test_claim_validator.py` | 1245 | 83 | All 11 claim checks + edge cases |
| 4 | `tests/test_gateway.py` | 922 | 67 | 15 artifact checks + `run_all` |
| 5 | `tests/test_pipeline_integration.py` | 653 | 11 | End-to-end pipeline integration |
| 6 | `tests/test_reporter.py` | 731 | 58 | Report generation, i18n, references, verification summary |
| 7 | `tests/test_schemas.py` | 428 | 92 | Scope/analysis/collected validation, english_title, direction field |
| 8 | `tests/test_source_router.py` | 414 | 58 | Route resolution, optional tiers, integration against real config.json |
| 9 | `tests/test_report_gateway.py` | 556 | 60 | All 10 report checks + BLOCKER upgrade |
| 10 | `tests/test_search_gate.py` | 532 | 42 | All 7 search checks + source_fidelity + direction system |
| 11 | `tests/test_cli.py` | 557 | 36 | All 8 commands + project root detection + review status parsing |
| 12 | `tests/test_fetcher.py` | 232 | 31 | Fetcher autonomous + pipe mode |
| 13 | `tests/test_content_concreteness.py` | 318 | 29 | Vague phrase detection, number/name presence, CJK specifics |
| 14 | `tests/test_new_gates.py` | 248 | 20 | New gate checks (facet_coverage, direction_coverage, etc.) |
| 15 | `tests/test_fetch_router.py` | 126 | 22 | Fetch strategy resolution |
| 16 | `tests/test_trust_boundary.py` | 168 | 21 | Trust boundary structural + semantic validation |
| 17 | `tests/test_merge_automation.py` | 197 | 18 | Section merge + ordering |
| 18 | `tests/test_repair_loop.py` | 219 | 18 | Repair loop + fix_report parsing + re-merge |
| 19 | `tests/test_batch_fetch.py` | 170 | 12 | Batch fetch CLI |
| 20 | `tests/test_reporter_postprocess.py` | 99 | 22 | `_post_process`, bare URL fix, reference section detection |
| 21 | `tests/test_fetch_cleaner.py` | 93 | 17 | Content cleaning |
| 22 | `tests/test_proceed_trust_boundary.py` | 132 | 16 | Proceed + trust boundary integration |
| 23 | `tests/test_utils.py` | 146 | 28 | URL normalization, JSON I/O, hash computation |
| 24 | `tests/test_exceptions.py` | 38 | 13 | Exception hierarchy + ValidationError |
| 25 | `tests/test_reset.py` | 88 | 10 | Reset subcommand |
| 26 | `tests/test_v3_integration.py` | 132 | 11 | v3 integration |

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
|    - topic (required)               |
|    - goal_type (required)           |
|    - scope_description (required)   |
|    - depth (optional, default=standard)|
|    - audience (optional, default=general)|
|    - search_directions (optional, ADR 0046)|
|    - report_language (optional)     |
|    - english_title (required for CJK)|
|    - decision_questions (optional hint)|
+---------------+---------------------+
                |
                v
    proceed --from scope --to search   <-- Gate 1: scope.json schema validation
                |                         |-- _fill_scope_defaults() fills depth/audience
                |                         |-- validate_scope() checks required fields + enums
                |                         +-- english_title BLOCKER for non-ASCII topic
                v
+-------------------------------------+
|  Phase 2: Search -> Collect -> Filter|
|  Output: collected.json              |
|    - url, title, snippet            |
|    - source_tier, fetched_content   |
|    - direction (ADR 0052)           |
|    - source_file (path to .md)      |
|    - vendor_affiliation (optional)  |
|  Source files: .workdir/sources/*.md|
|  Agent searches freely (ADR 0042)   |
|  Fetch via CLI: fetch / batch-fetch |
+---------------+---------------------+
                |
                v
    proceed --from search --to analysis  <-- Gate 2: SearchGate.check()
                |                           |-- collected_exists (BLOCKER)
                |                           |-- collected_schema (BLOCKER)
                |                           |-- min_sources (BLOCKER, depth-driven)
                |                           |-- tier_coverage (BLOCKER, repair hints from config)
                |                           |-- source_fidelity (BLOCKER/WARN)
                |                           |-- direction_tagging (BLOCKER, ADR 0052)
                |                           +-- direction_coverage (BLOCKER, ADR 0052)
                v
+-------------------------------------+
|  Phase 3a: Build analysis.json       |
|    - Plan sections (section plan)    |
|    - Subagents write                 |
|      analysis_section_{id}.json      |
|    - Trust boundary validates each   |
|      section (ADR 0053)              |
|    - Auto-merge → analysis.json      |
|      (ADR 0054)                      |
|    - sanitize_sections() normalizes  |
|    - apply_source_verification()     |
|      writes back to analysis.json    |
|  Schema:                             |
|    topic, goal_type, sections[]      |
|      +- id, title, content           |
|      +- depth_strategy, order        |
|      +- key_insights[{summary,sources}]|
|      +- tensions[{summary,sources}]  |
|      +- claims[]                     |
|           +- summary, sources[]      |
|           +- evidence_type           |
|           +- confidence, precision   |
|           +- metric_type (optional)  |
|           +- source_metadata (opt)   |
|           +- source_verification     |
|           +- verified (bool)         |
+---------------+---------------------+
                |
                v
    proceed --from analysis --to review  <-- Gate 3: schema + BLOCKERs
                |                           |-- Trust boundary validation
                |                           |-- Auto-merge if section files exist
                |                           |-- sanitize_sections() normalizes output
                |                           |-- validate_analysis() schema check
                |                           |-- BLOCKERs: artifact_exists, url_traceability,
                |                           |   section_coverage, ref_marker_validity,
                |                           |   claim_source_ref_coverage, subagent_delegation,
                |                           |   entity_number_conflict
                |                           |-- WARN: precision_inflation, source_metadata,
                |                           |   metric_type_homogeneity, content_concreteness,
                |                           |   claim_metadata, claim_dedup, methodology_depth,
                |                           |   recommendation_structure, source_tier_balance,
                |                           |   quality_heuristics, facet_coverage,
                |                           |   direction_coverage, table_suggestion,
                |                           |   section_deviation, key_insights_coverage
                |                           |-- INFO: source_verification_check
                |                           +-- apply_source_verification() writes back
                v
+-------------------------------------+
|  Phase 3b: Review (mandatory)        |
|  Review subagent produces:           |
|    - review_report.md                |
|    - fix_list.json (ADR 0055)        |
|  Repair loop (ADR 0055):             |
|    - review-fix subagent → fix_report|
|    - Lightweight review verification |
|    - Max 2 repair rounds             |
|    - BLOCKER all fixed → passed      |
|    - Otherwise → degraded            |
+---------------+---------------------+
                |
                v
    proceed --from review --to final   <-- Gate 4: advisory + BLOCKERs
                |                         |-- review→review: review_report.md must exist
                |                         |-- review→final:
                |                         |   + Advisory gateway checks (printed, non-blocking)
                |                         |   + review_report_exists BLOCKER (ADR 0028)
                |                         |   + Repair loop status check (ADR 0055)
                |                         |   + Re-merge after fix if BLOCKERs were fixed
                v
+-------------------------------------+
|  Phase 4: Report generation          |
|  cli.py report                       |
|    <-- reporter.py generates Markdown|
|  _detect_review_status() parses:     |
|    **pass** → "passed"               |
|    **pass_with_issues** → "degraded" |
|    **fail** → sys.exit(1)            |
|    missing review → "degraded"       |
|  Output: <output_dir>/<title>.md     |
|    (YAML front matter + numbered refs|
|     + verification summary + appendix|
|     + tier star labels)              |
|  Post-generation: run_report_checks()|
|    3 BLOCKERs → delete report, exit(1)|
|    7 WARNs → printed, non-blocking   |
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

### 4.1 `scripts/cli.py` — CLI Entry Point (255 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > `"en"`. Post-generation: runs `run_report_checks()`, BLOCKERs delete report. |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `cmd_reset` | `(args: Namespace) -> None` | Reset pipeline to a given phase by deleting target and subsequent artifacts (ADR 0016) |
| `cmd_fetch` | `(args: Namespace) -> None` | Fetch URL and save as source file. Supports `--from-stdin` for pipe mode. |
| `cmd_batch_fetch` | `(args: Namespace) -> None` | Batch-fetch multiple URLs from stdin, update collected.json |
| `_detect_review_status` | `() -> str` | Parse `## Overall Verdict` in review_report.md: `**pass**` → "passed", `**pass_with_issues**` → "degraded", `**fail**` → sys.exit(1), missing → "degraded" |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_build_report_filename` | `(scope_data: dict, output_path: Path) -> Path` | Build safe ASCII report filename; prefers `english_title` over `topic`; appends `_YYYY-MM-DD` on collision |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|review|final
gateway                    # Standalone gateway run
report [--review-status Q] [--search-rounds N] [--source-count N] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
reset --phase <X>          # X: scope|search|analysis|review — delete target + subsequent artifacts
fetch <url> [--tier N] [--no-playwright] [--from-stdin]  # Fetch URL, save source file
batch-fetch [--from-stdin] [--pending]  # Batch fetch, update collected.json
```

### 4.2 `scripts/proceed.py` — Phase Transition Gates (534 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_repair_json_text` | `(raw: str) -> str` | Fix unescaped double quotes inside JSON string values (LLM output repair) |
| `_preprocess_cjk_quotes` | `(raw: str) -> str` | Replace CJK full-width quotes with ASCII single quotes (ADR 0053) |
| `_read_json_with_repair` | `(path: Path) -> tuple[dict|list|None, str|None]` | Read JSON with quote repair fallback |
| `_validate_section_files` | `(workdir: Path) -> list[str]` | Validate section files against trust boundary (ADR 0053) |
| `mark_section_incomplete` | `(section_path: Path) -> None` | Mark section as `status: "incomplete"` after 3 trust boundary failures (ADR 0053) |
| `is_section_incomplete` | `(section_path: Path) -> bool` | Check whether section file is marked incomplete |
| `_sort_sections` | `(sections: list[dict], goal_type: str) -> list[dict]` | Sort sections into reading order (ADR 0060): quantitative → `_REQUIRED_SECTION_IDS` position; exploratory → `order` field |
| `_merge_section_files` | `(workdir: Path, topic: str, goal_type: str) -> dict | None` | Merge analysis_section_*.json into analysis.json (ADR 0054). Idempotent. |
| `_check_url_consistency` | `(analysis: dict, collected_urls: set[str]) -> list[str]` | Check URL consistency after merge with "did you mean" suggestions |
| `write_phase_state` | `(workdir: Path, phase: str) -> None` | Write current phase to `pipeline_state.json`; warns on failure |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from `pipeline_state.json` first, then artifact presence fallback (ADR 0019) |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json via `schemas.validate_scope()` |
| `_fill_scope_defaults` | `(workdir: Path) -> None` | Fill optional depth/audience defaults in scope.json if missing |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `_find_report_path` | `(workdir: Path) -> Path | None` | Find latest .md report in configured output directory |
| `_format_check_result` | `(r: CheckResult, prefix: str) -> list[str]` | Format a failed CheckResult as output lines, including repair_hints |
| `_gate_scope` | `(workdir, config?) -> list[str]` | Scope gate: fill defaults + schema check |
| `_gate_search` | `(workdir, config?) -> list[str]` | Search gate: delegates to `SearchGate.check()` |
| `_gate_analysis` | `(workdir) -> list[str]` | Analysis gate: trust boundary + auto-merge + sanitize + schema + BLOCKER artifact checks + INFO printing + `apply_source_verification` write-back |
| `_check_review_report_exists` | `(workdir: Path) -> CheckResult` | Check review_report.md exists and is non-empty (BLOCKER, ADR 0028) |
| `_gate_review` | `(workdir, to_phase) -> list[str]` | Review gate: review→review checks report exists; review→final runs advisory + review_report_exists BLOCKER + repair loop status + re-merge |
| `check_report` | `(workdir: Path) -> list[str]` | Run report checks on generated report file (ADR 0056, CLI post-step) |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions + runs phase-specific gates |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `run_all()` |

### 4.3 `scripts/artifact_checks.py` — Artifact-Level Quality Gate Checks (618 lines)

**Data class (from `lib/check_types.py`):**

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN" | "INFO"
    passed: bool
    message: str = ""
    repair_hints: list[str] = field(default_factory=list)
```

**15 Check Functions:**

| Function | Level | Purpose |
|---|---|---|
| `check_artifact_exists` | BLOCKER | scope.json + collected.json + analysis.json must exist |
| `check_url_traceability` | BLOCKER | All claim sources must normalize-match collected.json URLs; includes "did you mean" suggestions |
| `check_section_coverage` | BLOCKER | Required section IDs per goal_type (lookup table) |
| `check_analysis_schema` | BLOCKER/WARN | Delegates to `validate_analysis()` from schemas.py |
| `check_subagent_delegation` | BLOCKER | Multi-section reports must have analysis_section_*.json files (not monolithic) |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_content_concreteness` | WARN | Quantitative types: vague phrase density >10% or missing numbers/names |
| `check_methodology_depth` | WARN | Quantitative types: methodology section <150 words or lacks Markdown table |
| `check_recommendation_structure` | WARN | tech_selection/competitive_comparison: recommendation section lacks comparison table or "not recommended" |
| `check_source_tier_balance` | WARN | Quantitative types: Tier 1+2 source ratio <30% among referenced URLs |
| `check_key_insights_coverage` | WARN | Panoramic/exploratory sections need ≥2 key_insights |
| `check_section_deviation` | WARN | Section deviates significantly from section plan |
| `check_table_suggestion` | WARN | Comparison sections should include Markdown tables |
| `check_direction_coverage` | WARN | Analysis-phase: declared direction with collected sources but no claim referencing them |
| `check_facet_coverage` | WARN | Goal_type-aware fixed facet set (ADR 0050); community requires ≥2 platforms |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]` — runs 15 artifact checks + delegates to `ClaimValidator.check()` for claim-level checks

### 4.4 `scripts/claim_validator.py` — Claim-Level Quality Gate Checks (584 lines)

**Class: `ClaimValidator`**

```python
class ClaimValidator:
    def __init__(self, workdir: Path, goal_type: str) -> None: ...
    def check(self) -> list[CheckResult]: ...
```

Reads analysis.json + collected.json once in `__init__`, then `check()` runs all claim-level validations.

**11 Check Methods:**

| Method | Level | Purpose |
|---|---|---|
| `_check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `_check_precision_inflation` | WARN | Exact precision + wrong evidence_type; conflicting exact values in same metric_type (data_variance) |
| `_check_source_metadata` | WARN | official_data/independent_benchmark claims missing or have empty source_metadata.test_conditions |
| `_check_metric_type_homogeneity` | WARN | Mixing different metric_types within same section level |
| `_check_claim_dedup` | WARN | Same claim summary appears in multiple sections |
| `_check_entity_number_conflict` | BLOCKER | Same entity has conflicting numbers across claims |
| `_check_primary_source_ratio` | WARN | Tier/platform skew advisory metric (ADR 0051) |
| `_check_ref_marker_validity` | BLOCKER | `{{ref:URL}}` markers in content must reference URLs in collected.json |
| `_check_claim_source_ref_coverage` | BLOCKER | All claim sources must be referenced in section content via `{{ref:URL}}` markers |
| `_check_source_verification` | INFO | Computes source_verification (source_confirmed/source_absent/source_indirect) for each claim; never blocks |

**Standalone function:** `apply_source_verification(workdir: Path) -> None` — writes `source_verification` and `verified` fields back to analysis.json

### 4.5 `scripts/search_gate.py` — Search-Phase Gate Checks (313 lines)

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
| `_check_min_sources` | BLOCKER | Total collected entries >= depth-driven threshold (quick=3, standard=5, deep=8) |
| `_check_tier_coverage` | BLOCKER | All required tiers in route must have >=1 source; optional tiers produce INFO only |
| `_check_source_fidelity` | BLOCKER/WARN | Source file existence + depth + snippet overlap (ADR 0030). >30% missing/shallow → BLOCKER |
| `_check_direction_tagging` | BLOCKER | Every collected entry must have `direction` field when scope declares search_directions (ADR 0052) |
| `_check_direction_coverage` | BLOCKER | Every declared search_direction must have >=1 collected entry tagged to it (ADR 0052) |

**Repair hint generation:** `_build_tier_repair_hints()`, `_build_all_tier_repair_hints()` — query config.json sources for concrete site_query suggestions when BLOCKERs fire.

### 4.6 `scripts/trust_boundary.py` — Trust Boundary Validation (113 lines, ADR 0053)

| Function | Signature | Purpose |
|---|---|---|
| `validate_section_output` | `(raw_json: str, collected_urls: set[str]) -> ValidationResult` | Two-layer validation: structural (schema) + semantic (URL match against collected.json) |

**Data classes:**

```python
@dataclass
class ValidationError:
    path: str
    error: str
    expected: str
    actual: str

@dataclass
class ValidationResult:
    passed: bool
    errors: list[ValidationError]
    report_json: str  # Structured error report for retry prompt injection
```

### 4.7 `scripts/repair_loop.py` — Repair Loop (107 lines, ADR 0055)

| Function | Signature | Purpose |
|---|---|---|
| `check_fix_report` | `(workdir: Path) -> dict | None` | Parse fix_report.json, count blocker_fixed/blocker_skipped/warn_skipped |
| `determine_review_status` | `(workdir: Path) -> str` | "passed" if all BLOCKERs fixed + lightweight review confirmed; otherwise "degraded" |
| `re_merge_after_fix` | `(workdir: Path) -> None` | Delete analysis.json, re-merge section files, re-sanitize |

### 4.8 `scripts/sanitizer.py` — Output Sanitizer (78 lines)

| Function | Signature | Purpose |
|---|---|---|
| `sanitize_sections` | `(analysis: dict, collected_urls: set[str] | None = None) -> dict` | Normalize subagent output: `section_id` → `id`, `text` → `summary`, `source_urls` → `sources`, strip non-schema keys, auto-downgrade `precision: exact` → `range` for `_NON_EXACT_EVIDENCE_TYPES`, auto-fix evidence_type aliases, auto-fix source_type aliases, filter URLs not in collected_urls |

### 4.9 `scripts/fetcher.py` — Fetch Execution Engine (201 lines)

**Data class:**

```python
@dataclass
class FetchResult:
    url: str
    actual_url: str
    source_file: str | None
    url_hash: str
    char_count: int
    fetched_content: str
    fetch_failed: bool
    tool_used: str
    content_insufficient: bool
    source_tier: int | None
```

**Class: `Fetcher`**

```python
class Fetcher:
    def __init__(self, workdir: Path, config: dict | None = None) -> None: ...
    def fetch(self, url: str, tier: int, no_playwright: bool = False) -> FetchResult: ...
    def save_piped(self, url: str, content: str, tier: int) -> FetchResult: ...
    def infer_tier(self, url: str) -> int | None: ...
```

- `fetch()`: Autonomous fetch via requests+markdownify → Playwright fallback. Uses `get_fetch_strategy()` for URL rewrite + tool order.
- `save_piped()`: Pipe mode — agent provides content, CLI does post-processing only (skip cleaning).
- Adaptive retry by tier: Tier 1-2 retry twice per tool, Tier 3-4 retry once; 60s global timeout (ADR 0038).

### 4.10 `scripts/fetch_router.py` — Fetch Strategy Router (69 lines)

| Function | Signature | Purpose |
|---|---|---|
| `get_fetch_strategy` | `(source_config: dict | None) -> FetchStrategy` | Resolve FetchStrategy from config. Returns ComposedStrategy (UrlRewriter + config), ConfigRewriteStrategy, or DefaultStrategy. |

### 4.11 `scripts/fetch_strategies/` — URL Rewriting Strategies

| File | Class | Purpose |
|---|---|---|
| `base.py` | `UrlRewriter` (Protocol) | `rewrite_url(url) -> str` — code-level URL rewriting only |
| `base.py` | `FetchStrategy` (Protocol) | `rewrite_url` + `tools` + `retries` — full strategy for Fetcher |
| `default.py` | `DefaultStrategy` | No URL rewrite, tools=["webfetch"], tier-based retries |
| `arxiv.py` | `ArxivStrategy` | Rewrites arxiv.org/pdf/ and /abs/ to ar5iv.labs.arxiv.org/html/ |
| `github.py` | `GithubStrategy` | Rewrites bare repo URLs to README.md |

### 4.12 `scripts/batch_fetch.py` — Batch Fetch (184 lines, ADR 0041)

| Function | Signature | Purpose |
|---|---|---|
| `cmd_batch_fetch` | `(args: Namespace) -> None` | Process multiple URLs from stdin JSON array, write source files via `Fetcher.save_piped()`, update collected.json automatically. Also has `--pending` mode to list URLs that still need fetching. |

### 4.13 `scripts/report_checks.py` — Report-Level Quality Checks (251 lines)

All functions operate on the generated `.md` report file. Called by `cmd_report` as a post-generation step (ADR 0056), not as a pipeline gate.

| Function | Level | Purpose |
|---|---|---|
| `check_report_dangling_refs` | BLOCKER | In-text [N] has no matching definition in References |
| `check_report_orphaned_defs` | BLOCKER | Reference definition not cited in text |
| `check_report_front_matter` | BLOCKER | YAML front matter exists and is well-formed |
| `check_report_refs_visibility` | WARN | References use visible format, not hidden `[N]: URL` definitions |
| `check_report_table_delimiters` | WARN | Markdown tables have correct `|---|` delimiter rows |
| `check_report_heading_levels` | WARN | No heading level skips (e.g., `##` → `####`) |
| `check_report_duplicate_headings` | WARN | No duplicate heading text at same level |
| `check_report_unclosed_code_blocks` | WARN | All fenced code blocks are properly closed |
| `check_report_empty_sections` | WARN | No sections with empty content |
| `check_report_overlong_lines` | WARN | No lines exceeding 500 characters |

**Aggregator:** `run_report_checks(report_path) -> list[CheckResult]`

### 4.14 `scripts/reporter.py` — Report Generator (272 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_resolve_ref_markers` | `(content, ref_map, sv_map?) -> str` | Replace `{{ref:URL}}` with `[N†/‡](#refs)` links; appends source_verification markers |
| `_build_sv_map` | `(analysis: dict) -> dict[str, str]` | Build `{normalized_url -> worst source_verification}` across all claims |
| `_render_verification_summary` | `(analysis, lang) -> str` | Generate verification note + status table (confirmed/indirect/absent) |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix with tier star labels (★★★☆) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `build_front_matter` | `(topic, goal_type, scope, review_status, search_rounds, source_count, audience?, report_language?) -> str` | YAML front matter block (8-12 fields including `verification_required: true`) |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body; exploratory types use compact mode |
| `generate_report` | `(analysis_path, scope_path, review_status, search_rounds, source_count, report_language?) -> str` | Main entry: reads files, builds front matter + body |

**i18n Labels (8 pairs):** Sources/数据来源, References/参考文献, Test Conditions/测试环境, Claim/声明, Conditions/条件, Date/日期, Source Type/来源类型, Methodology/方法论

**Tier Star Labels:** Tier 1 → ★★★☆, Tier 2 → ★★☆☆, Tier 3 → ★☆☆☆, Tier 4 → ☆☆☆☆

**Source Verification Markers:** source_absent → †, source_indirect → ‡

### 4.15 `scripts/lib/source_router.py` — Source Routing (74 lines)

| Function | Signature | Purpose |
|---|---|---|
| `get_route` | `(goal_type, config?) -> dict` | Return route dict (entry_tier, path, optional_tiers); unknown -> "other" |
| `recommend_sources` | `(goal_type, config?) -> dict` | Structured output with recommended/all sources (includes optional_tiers) |
| `get_default_min_sources` | `(goal_type, config?) -> int` | Lookup from goal_type_defaults, fallback 2 |
| `get_default_depth` | `(goal_type, config?) -> str` | Priority: goal_type_defaults > config.default_depth > "standard" |

### 4.16 `scripts/lib/utils.py` — Utilities (110 lines)

| Function | Signature | Purpose |
|---|---|---|
| `normalize_url` | `(url: str) -> str` | Lowercase, strip www, sort query params, strip fragment, strip trailing slash |
| `read_json` | `(path: Path, retries: int = 2, delay: float = 0.5) -> Any` | `json.load()` with UTF-8; retries on OSError; raises `ArtifactError` on JSONDecodeError |
| `write_json` | `(data, path: Path, retries: int = 2, delay: float = 0.5) -> None` | `json.dump()` with UTF-8, indent=2, ensure_ascii=False; auto-mkdir; retries on OSError |
| `config_path` | `() -> Path` | Returns absolute path to `config.json` in skill root directory |
| `find_project_root` | `() -> Path` | Walk up from CWD to find `.git` directory; fallback to CWD |
| `ensure_dir` | `(path: Path) -> Path` | `mkdir(parents=True, exist_ok=True)` + return path |
| `compute_url_hash` | `(url: str) -> str` | SHA-1 hash of normalized URL (first 12 hex chars) |
| `suggest_similar_urls` | `(url: str, candidates: set[str], max_suggestions: int = 3) -> list[str]` | "Did you mean?" suggestions using normalized URL similarity |
| `tokenize_cjk_aware` | `(text: str, *, lowercase: bool = False) -> list[str]` | CJK-aware tokenization: splits on whitespace/CJK boundaries |
| `build_collected_by_url` | `(collected: list[dict]) -> dict[str, dict]` | Build `{normalized_url: entry}` lookup dict |
| `build_collected_url_set` | `(collected: list[dict]) -> set[str]` | Build `{normalized_url}` set |

### 4.17 `scripts/lib/constants.py` — Centralized Constants (202 lines)

Single source of truth for all enumerations, thresholds, and classification sets.

| Category | Constants |
|---|---|
| Stop words | `_ENGLISH_STOP_WORDS` (37), `_CHINESE_STOP_WORDS` (49) |
| Enumerations | `_VALID_GOAL_TYPES` (10), `_VALID_DEPTHS` (3), `_VALID_AUDIENCES` (4), `_VALID_METRIC_TYPES` (6), `_VALID_EVIDENCE_TYPES` (5), `_VALID_CONFIDENCE` (3), `_VALID_PRECISION` (3), `_VALID_SOURCE_VERIFICATIONS` (3), `_VALID_DEPTH_STRATEGIES` (4), `_VALID_SOURCE_TYPES` (8) |
| Alias maps | `_EVIDENCE_TYPE_ALIASES` (6), `_SOURCE_TYPE_ALIASES` (4) |
| Cross-constraints | `_NON_EXACT_EVIDENCE_TYPES`, `_VENDOR_SOURCE_TYPES` (4), `_INDIRECT_CITATION_PATTERNS` (3 regex) |
| Goal-type classifications | `_QUANTITATIVE_GOAL_TYPES` (5), `_EXPLORATORY_GOAL_TYPES` (4) |
| Schema field sets | `_SECTION_KEYS` (8: id, title, content, claims, depth_strategy, key_insights, tensions, order), `_CLAIM_KEYS` (9: summary, sources, evidence_type, confidence, precision, metric_type, source_metadata, verified, source_verification) |
| Thresholds | `_VAGUE_DENSITY_THRESHOLD` (0.10), `_TIER_BALANCE_THRESHOLD` (0.30), `_METHODOLOGY_MIN_WORDS` (150), `_MIN_SOURCES` (2), `_SUBAGENT_DELEGATION_MIN_SECTIONS` (2), `_DEPTH_MIN_SOURCES` ({quick:3, standard:5, deep:8}), `_OVERLONG_LINE_THRESHOLD` (500), `_SINGLE_SOURCE_RATIO` (0.5), `_SINGLE_SOURCE_RATIO_STANDARD` (0.70), `_SINGLE_SOURCE_RATIO_DEEP` (0.50), `_SOURCE_INDIRECT_RATIO_WARN` (0.30) |
| Source fidelity | `_SOURCE_FIDELITY_MISSING_RATIO_BLOCKER` (0.30), `_SOURCE_FIDELITY_EXEMPT_RATIO_WARN` (0.50), `_SOURCE_FIDELITY_SHALLOW_RATIO_BLOCKER` (0.30), `_SOURCE_FIDELITY_SHALLOW_CHARS` (2000), `_SOURCE_FIDELITY_THIN_RATIO_WARN` (0.50), `_SOURCE_FIDELITY_THIN_CHARS` (5000), `_SOURCE_FIDELITY_SNIPPET_OVERLAP_RATIO_BLOCKER` (0.30), `_SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD` (0.80) |
| Fetch config | `_FETCH_TIMEOUT_SECONDS` (60), `_FETCH_PLAYWRIGHT_TIMEOUT` (30000), `_FETCH_PLAYWRIGHT_CHANNEL_DEFAULT` ("chrome"), `_FETCH_PLAYWRIGHT_CHANNEL_FALLBACK` ("chromium"), `_FETCHED_CONTENT_INDEX_LENGTH` (200), `_SOURCES_DIR` ("sources") |
| Vague phrases | `_VAGUE_PHRASES_ZH` (12), `_VAGUE_PHRASES_EN` (10) |
| Required sections | `_REQUIRED_SECTION_IDS` (6 goal types) |
| Artifact filenames | `ARTIFACT_SCOPE`, `ARTIFACT_COLLECTED`, `ARTIFACT_ANALYSIS`, `ARTIFACT_PIPELINE_STATE`, `ARTIFACT_REVIEW_REPORT`, `ARTIFACT_FIX_LIST`, `ARTIFACT_FIX_REPORT`, `ARTIFACT_LIGHTWEIGHT_REVIEW`, `ARTIFACT_CONFIG` |
| Pipeline config | `_VALID_TRANSITIONS_SET` (5 transitions incl. review→review), `_PHASE_ARTIFACTS` (5 phases) |
| Display labels | `_TIER_LABELS` (4 tiers), `_LABELS` (8 key × 2 languages) |

### 4.18 `scripts/lib/schemas.py` — Centralized Schema Validation (275 lines)

**TypedDict definitions:**

| Name | Fields |
|---|---|
| `ScopeDict` | topic, goal_type, depth, audience, scope_description, search_directions, report_language, english_title |
| `ClaimDict` | summary, sources, evidence_type, confidence, precision, metric_type, source_metadata, verified, source_verification |
| `SectionDict` | id, title, content, claims, depth_strategy, key_insights, tensions, order |
| `AnalysisDict` | topic, goal_type, sections |
| `CollectedEntryDict` | url, title, snippet, source_tier, fetched_content, vendor_affiliation, source_file, direction |

**Required fields:**

| Artifact | Required |
|---|---|
| scope.json | topic, goal_type, scope_description |
| analysis.json | topic, goal_type |
| section | id, title, content |
| claim | summary, sources |
| collected entry | url, title, snippet |

**Public functions:**

| Function | Signature | Purpose |
|---|---|---|
| `validate_scope` | `(data: dict) -> list[ValidationError]` | Validate scope.json structure, enums, types, english_title requirement for non-ASCII topic |
| `validate_analysis` | `(data: dict) -> list[ValidationError]` | Validate analysis.json structure, sections, claims, key_insights, tensions, depth_strategy, order |
| `validate_collected` | `(data: list) -> list[ValidationError]` | Validate collected.json entries, direction field, source_file, vendor_affiliation |

### 4.19 `scripts/lib/exceptions.py` — Custom Exceptions + ValidationError (22 lines)

| Class | Base | Attributes | Purpose |
|---|---|---|---|
| `InfoCollectorError` | `Exception` | — | Base exception for all info-collector errors |
| `GateFailureError` | `InfoCollectorError` | `phase: str`, `blockers: list[str]` | Gate check failed with BLOCKER-level issues |
| `ArtifactError` | `InfoCollectorError` | `path: str`, `reason: str` | Artifact file missing, unreadable, or schema-invalid |
| `ValidationError` | `@dataclass` (not Exception) | `field: str`, `message: str` | Schema validation error carrier (ADR 0015) |

### 4.20 `scripts/lib/check_types.py` — CheckResult Dataclass (25 lines, ADR 0061)

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN" | "INFO"
    passed: bool
    message: str = ""
    repair_hints: list[str] = field(default_factory=list)
```

Also provides `read_artifact()` helper for reading artifact JSON files.

---

## 5. Configuration — `config.json`

### Source Tiers (4 tiers, 38 sources)

| Tier | Name | Sources |
|---|---|---|
| 1 | Academic/Standards | arXiv, Google Scholar, PubMed, CNKI (zh), W3C, IETF, ISO, ACL Anthology, Semantic Scholar, Wanfang (zh), CQVIP (zh), CBOA (zh) |
| 2 | Docs/Open Source | GitHub, MDN, Wikipedia, Hugging Face, PyPI, ReadTheDocs, Gitee (zh), Wikipedia (zh) |
| 3 | Industry/Expert Blogs | Medium, IEEE Spectrum, MIT Tech Review, Substack, Towards Data Science, The New Stack, 36氪 (zh), InfoQ 中文 (zh), 机器之心 (zh), 少数派 (zh), CSDN (zh) |
| 4 | Community/UGC | Reddit, Stack Overflow, Zhihu (zh), Weibo (zh), Hacker News, Dev.to, V2EX (zh), 掘金 (zh), 豆瓣 (zh), 小红书 (zh) |

### Goal Type Routes (10 types)

| Goal Type | Entry Tier | Path | Optional Tiers |
|---|---|---|---|
| exploratory | 4 | [4, 3, 2] | — |
| panoramic_understanding | 2 | [2, 1, 3, 4] | — |
| tech_selection | 2 | [2, 3, 4, 1] | — |
| feasibility_assessment | 2 | [2, 1, 3] | — |
| competitive_comparison | 2 | [2, 1, 3, 4] | — |
| academic_research | 1 | [1] | [2] |
| fact_check | 1 | [1, 2, 4] | — |
| background_check | 3 | [3, 2, 1, 4] | — |
| market_analysis | 3 | [3, 4, 1, 2] | — |
| other | 3 | [3, 2, 1] | — |

### Other Settings

- `output_dir`: `"./reports/"`
- `default_report_language`: `"zh"`
- `default_depth`: `"standard"`
- `goal_type_defaults`: exploratory (depth=quick, min_sources=1), fact_check (depth=quick, min_sources=1)
- `fetch_defaults`: source_dir=".workdir/sources/", shallow_threshold=2000, playwright_enabled=true, playwright_channel="chrome", playwright_timeout=30000

---

## 6. Quality Gate Detail

### Gate 1: Scope -> Search

- **`_fill_scope_defaults()`** fills optional depth/audience with defaults ("standard"/"general")
- **scope.json schema validation** via `schemas.validate_scope()`: 3 required fields (topic, goal_type, scope_description)
- **Enum validation**: goal_type in 10 values, depth in {quick, standard, deep}, audience in {CTO, engineer, researcher, general}
- **english_title**: required (BLOCKER) when topic contains non-ASCII characters

### Gate 2: Search -> Analysis

| Check | Level | Logic |
|---|---|---|
| collected_exists | BLOCKER | collected.json must exist and have >=1 entry |
| collected_schema | BLOCKER | `schemas.validate_collected()` validates entry structure + direction field |
| min_sources | BLOCKER | Total collected entries >= depth-driven threshold (quick=3, standard=5, deep=8) |
| tier_coverage | BLOCKER | All required tiers in goal_type route must have >=1 source; optional tiers produce INFO only. Repair hints from config.json source list. |
| source_fidelity | BLOCKER/WARN | Source file existence + depth + snippet overlap (ADR 0030). >30% missing → BLOCKER; >30% shallow (<2000 chars) → BLOCKER; >30% snippet overlap → BLOCKER; >50% exempt → WARN |
| direction_tagging | BLOCKER | Every collected entry must have `direction` field when scope declares search_directions (ADR 0052) |
| direction_coverage | BLOCKER | Every declared search_direction must have >=1 collected entry tagged to it (ADR 0052) |

### Gate 3: Analysis -> Review

1. **Trust boundary validation** of section files (ADR 0053): structural + semantic validation against collected.json URLs
2. **Auto-merge** if section files exist but analysis.json doesn't (ADR 0054): `_merge_section_files()` + `_check_url_consistency()`
3. **JSON repair** on analysis.json: `_read_json_with_repair()` fixes unescaped quotes + CJK quotes
4. **`sanitize_sections()`** normalizes subagent output: field name aliases, precision downgrades, evidence_type/source_type aliases, URL filtering, unknown key stripping
5. **Schema validation** via `validate_analysis()`
6. **`run_all()` gateway checks** — only BLOCKER-level failures in analysis-phase checks block:
   - **BLOCKERs**: artifact_exists, url_traceability, section_coverage, ref_marker_validity, claim_source_ref_coverage, subagent_delegation, entity_number_conflict
   - **WARNs**: precision_inflation, source_metadata, metric_type_homogeneity, content_concreteness, claim_metadata, claim_dedup, methodology_depth, recommendation_structure, source_tier_balance, quality_heuristics, facet_coverage, direction_coverage, table_suggestion, section_deviation, key_insights_coverage, primary_source_ratio
   - **INFO**: source_verification_check
7. **`apply_source_verification()`** writes `source_verification` and `verified` fields to analysis.json

### Gate 4: Review -> Final

No longer advisory-only. Has BLOCKER-level checks (ADR 0055, 0056):

- **review→review (self-loop)**: review_report.md must exist
- **review→final**:
  - Advisory gateway checks (printed as `[ADVISORY]`, non-blocking)
  - `review_report_exists` BLOCKER — review is mandatory (ADR 0028)
  - Repair loop status check: `check_fix_report()` counts blocker_fixed/blocker_skipped
  - If blocker_skipped > 0 → BLOCKER (report status is degraded)
  - If blocker_fixed > 0 → `re_merge_after_fix()` re-merges section files + re-sanitizes
  - warn_skipped → WARN (report usable but not all issues resolved)

### Report Checks (Post-generation, ADR 0056)

Run by `cmd_report` after generating the .md file. Not a pipeline gate.

**BLOCKERs** (prevent report from being saved):

- `report_dangling_refs`: In-text citation with no source definition
- `report_orphaned_defs`: Source definition with no in-text citation
- `report_front_matter`: Missing or malformed YAML front matter

**WARNs**: refs visibility, table delimiters, heading levels, duplicate headings, unclosed code blocks, empty sections, overlong lines

### Review Status Values

| Value | Condition |
|---|---|
| `passed` | All BLOCKER issues fixed + lightweight review confirmed |
| `degraded` | BLOCKER issues not all fixed, or no fix_report.json, or lightweight review not confirmed |

The `unreviewed` option has been removed (ADR 0028) — review is mandatory, minimum level is degraded.

### Gate Philosophy (ADR 0029)

The gate system follows an "auto-downgrade suspicious metadata + honestly mark" philosophy:

- **BLOCKERs** are reserved for **structural integrity** checks — things that code can verify deterministically (artifact existence, URL traceability, schema validity, section coverage, direction contracts, review existence)
- **WARN** checks flag **quality concerns** that deserve attention but don't block the pipeline
- **INFO** checks provide **observability** without any judgment (e.g., source_verification_check)
- `verified` and `source_verification` fields are set deterministically by `apply_source_verification()` code, not by LLM

---

## 7. Data Model Schemas

### scope.json

```json
{
  "topic": "string (required)",
  "goal_type": "enum (10 values, required)",
  "scope_description": "string (required)",
  "depth": "quick | standard | deep (optional, default=standard)",
  "audience": "CTO | engineer | researcher | general (optional, default=general)",
  "search_directions": ["string (optional, ADR 0046)"],
  "report_language": "string (optional)",
  "english_title": "string (required when topic contains non-ASCII)",
  "decision_questions": ["string (optional hint, 2-3 questions)"]
}
```

### collected.json

```json
[
  {
    "url": "string (required)",
    "title": "string (required)",
    "snippet": "string (required)",
    "source_tier": "int 1-4 (required)",
    "fetched_content": "string (first 200 chars of source file)",
    "direction": "string (ADR 0052: scope.search_directions value or 'other')",
    "source_file": "string (relative path to .workdir/sources/{hash}.md)",
    "vendor_affiliation": "string | null (optional)"
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
      "id": "string (required)",
      "title": "string (required)",
      "content": "string (required, with {{ref:URL}} markers)",
      "depth_strategy": "overview | deep_dive | comparison | methodology",
      "order": "int (optional, explicit reading position, ADR 0060)",
      "key_insights": [
        {
          "summary": "string (required)",
          "sources": ["string (URL from collected.json)"]
        }
      ],
      "tensions": [
        {
          "summary": "string (required)",
          "sources": ["string (URL from collected.json)"]
        }
      ],
      "claims": [
        {
          "summary": "string (required, ADR 0045)",
          "sources": ["string (required, non-empty, ADR 0045)"],
          "evidence_type": "official_data | independent_benchmark | third_party_estimate | qualitative_trend | expert_opinion",
          "confidence": "high | medium | low",
          "precision": "exact | range | qualitative",
          "metric_type": "swe_bench_verified | swe_bench_pro | terminal_bench | pr_merge_rate | refactoring_safety | custom",
          "source_metadata": {
            "test_conditions": "string",
            "test_date": "string",
            "source_type": "official_report | independent_test | production_case | survey | vendor_benchmark | analyst_forecast | vendor_survey | vendor_blog"
          },
          "source_verification": "source_confirmed | source_absent | source_indirect (set by apply_source_verification, never by LLM)",
          "verified": "bool (derived from source_verification: confirmed/indirect → true, absent → false)"
        }
      ]
    }
  ],
  "_merge_completed": true
}
```

### pipeline_state.json

```json
{
  "current_phase": "pre_scope | post_scope | post_search | post_analysis | post_review | post_final"
}
```

### fix_list.json (ADR 0055)

```json
[
  {
    "issue_id": "string",
    "type": "string",
    "severity": "BLOCKER | WARN",
    "section": "string",
    "description": "string",
    "recommendation": "string"
  }
]
```

### fix_report.json (ADR 0055)

```json
[
  {
    "issue_id": "string",
    "status": "fixed | skipped",
    "reason": "string (if skipped)"
  }
]
```

---

## 8. Import Dependency Graph

```
cli.py -----> lib.constants (ARTIFACT_*, _PHASE_ARTIFACTS)
        |----->.exceptions (InfoCollectorError)
        |----->.utils (config_path, find_project_root)
        |-----> proceed.py (lazy: proceeds, detect_current_phase, write_phase_state)
        |-----> reporter.py (lazy: generate_report)
        |----->.source_router (lazy: recommend_sources)
        |-----> fetcher.py (lazy: Fetcher)
        |-----> batch_fetch.py (lazy: cmd_batch_fetch)

proceed.py ->.utils (config_path, find_project_root, ensure_dir, read_json, build_collected_url_set, write_json, normalize_url, suggest_similar_urls)
            ->.check_types (CheckResult)
            -> artifact_checks (run_all as run_gateway)
            -> repair_loop (check_fix_report, determine_review_status, re_merge_after_fix)
            -> report_checks (run_report_checks)
            -> sanitizer (sanitize_sections)
            -> search_gate (SearchGate)
            -> trust_boundary (lazy: validate_section_output)
            ->.exceptions (ArtifactError)
            ->.constants (ARTIFACT_*, _REQUIRED_SECTION_IDS, _VALID_TRANSITIONS_SET)
            ->.schemas (lazy: validate_scope, validate_analysis)
            -> claim_validator (lazy: apply_source_verification)

artifact_checks.py ->.constants (13+ constants)
                    ->.check_types (CheckResult, read_artifact)
                    ->.exceptions (ArtifactError)
                    ->.utils (build_collected_by_url, build_collected_url_set, normalize_url, read_json, tokenize_cjk_aware, suggest_similar_urls)
                    ->.schemas (lazy: validate_analysis)
                    -> claim_validator (lazy: ClaimValidator)

claim_validator.py ->.check_types (CheckResult, read_artifact)
                    ->.constants (ARTIFACT_*, _INDIRECT_CITATION_PATTERNS, _QUANTITATIVE_GOAL_TYPES, _SINGLE_SOURCE_RATIO_*, _VENDOR_SOURCE_TYPES, _VALID_SOURCE_TYPES, _SOURCE_TYPE_ALIASES)
                    ->.exceptions (ArtifactError)
                    ->.utils (build_collected_by_url, build_collected_url_set, normalize_url, read_json, write_json)

search_gate.py ->.check_types (CheckResult)
                ->.constants (ARTIFACT_*, _DEPTH_MIN_SOURCES, _SOURCE_FIDELITY_*)
                ->.exceptions (ArtifactError)
                ->.source_router (get_default_min_sources, get_route)
                ->.utils (read_json)
                ->.schemas (lazy: validate_collected)

trust_boundary.py ->.utils (normalize_url)
                  ->.schemas (_validate_sections)

repair_loop.py ->.constants (ARTIFACT_*)
               ->.exceptions (ArtifactError)
               ->.utils (build_collected_url_set, read_json, write_json)
               -> proceed (lazy: _merge_section_files)
               -> sanitizer (lazy: sanitize_sections)

sanitizer.py ->.constants (_CLAIM_KEYS, _SECTION_KEYS, _EVIDENCE_TYPE_ALIASES, _NON_EXACT_EVIDENCE_TYPES, _SOURCE_TYPE_ALIASES, _VALID_*)

fetcher.py -> fetch_cleaner (clean)
           -> fetch_router (get_fetch_strategy)
           ->.constants (_FETCH_*, _SOURCE_FIDELITY_SHALLOW_CHARS, _SOURCES_DIR)
           ->.utils (compute_url_hash)

fetch_router.py -> fetch_strategies (ArxivStrategy, GithubStrategy, DefaultStrategy, ComposedStrategy, ConfigRewriteStrategy)
               ->.utils (config_path)

report_checks.py ->.check_types (CheckResult)
                 ->.constants (_OVERLONG_LINE_THRESHOLD)

reporter.py ->.constants (ARTIFACT_COLLECTED, _EXPLORATORY_GOAL_TYPES, _LABELS, _TIER_LABELS)
            ->.utils (build_collected_by_url, normalize_url, read_json)
            -> report_checks (_find_references_section)

source_router.py ->.utils (config_path)

schemas.py ->.constants (_VALID_*)
           ->.exceptions (ValidationError)

constants.py -> (no internal imports)

exceptions.py -> (no internal imports)

utils.py ->.exceptions (ArtifactError)
          ->.constants (ARTIFACT_CONFIG)

check_types.py ->.exceptions (ArtifactError)
               ->.utils (read_json)
```

**External deps:** `argparse`, `dataclasses`, `hashlib`, `json`, `re`, `string`, `time`, `urllib.parse`, `typing` — all stdlib, zero third-party.

---

## 9. Error Handling Patterns

1. **Custom exception hierarchy**: `InfoCollectorError` base → `GateFailureError` + `ArtifactError`. Top-level `cli.py:main()` catches `InfoCollectorError` uniformly. `ValidationError` is a dataclass (not Exception) used by schemas.py.
2. **Gate-based error handling**: BLOCKERs are terminal via `sys.exit(1)`. WARNs are printed but non-blocking. INFOs are printed for observability.
3. **JSON parse errors**: `read_json()` raises `ArtifactError` on `json.JSONDecodeError` (no retry — content corruption is permanent). `_read_json_with_repair()` attempts quote repair + CJK quote preprocessing before giving up.
4. **File operation retry**: `read_json()`/`write_json()` retry up to 3 times (default `retries=2, delay=0.5`) on `OSError` only. `json.JSONDecodeError` is not retried (ADR 0014).
5. **Defensive fallbacks**: `_count_sources()` uses `except (ArtifactError, OSError)` to return safe default (0). `detect_current_phase()` uses `except (ArtifactError, OSError)` when reading pipeline state.
6. **Three-tier severity**: BLOCKER (blocks pipeline), WARN (printed, non-blocking), INFO (printed for observability). `proceeds()` returns errors for BLOCKERs only.
7. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` / `[INFO]` / `[ADVISORY]` prefixes.
8. **Explicit state file with fallback**: `detect_current_phase()` reads `pipeline_state.json` first (ADR 0019), falls back to artifact-presence heuristic.
9. **Subagent output sanitization**: `sanitize_sections()` normalizes known field name variations (`text`→`summary`, `source_urls`→`sources`, `section_id`→`id`), strips unknown keys, auto-downgrades precision, auto-fixes evidence_type/source_type aliases.
10. **Trust boundary validation**: Section files validated before merge (ADR 0053). Failed validation → retry with structured error report (max 2). 3 failures → BLOCK pipeline → orchestrator manual rewrite → `status: "incomplete"` if also fails.
11. **Deterministic verification**: `verified` and `source_verification` fields are set by `apply_source_verification()` code, not by LLM (ADR 0029).
12. **Repair loop**: Review findings → fix_list.json → review-fix subagent → fix_report.json → lightweight review verification. Max 2 rounds. BLOCKER all fixed → passed; otherwise → degraded (ADR 0055).

---

## 10. Test Coverage Summary

| Module | Tests | Lines | Notable |
|---|---|---|---|
| `proceed.py` | 102 | 1308 | Phase detection, gate routing, merge, trust boundary, review, JSON repair, section ordering, URL consistency |
| `claim_validator.py` | 83 | 1245 | All 11 claim checks + edge cases, precision_inflation, source_verification, primary_source_ratio |
| `artifact_checks.py` | 67 | 922 | 15 artifact checks + `run_all`, facet_coverage, direction_coverage |
| `reporter.py` | 58 | 731 | Report generation, i18n, references, verification summary, test conditions |
| `schemas.py` | 92 | 428 | Scope/analysis/collected validation, english_title, direction, depth_strategy, order |
| `source_router.py` | 58 | 414 | Route resolution, optional tiers, integration against real config.json |
| `report_checks.py` | 60 | 556 | All 10 report checks + BLOCKER upgrade |
| `search_gate.py` | 42 | 532 | All 7 search checks, source_fidelity, direction system, repair hints |
| `cli.py` | 36 | 557 | All 8 commands, project root detection, review status parsing |
| `fetcher.py` | 31 | 232 | Autonomous fetch, pipe mode, FetchResult |
| `content_concreteness` | 29 | 318 | Vague phrase detection, number/name presence, CJK specifics |
| `new_gates` | 20 | 248 | Facet_coverage, direction_coverage, key_insights_coverage |
| `fetch_router.py` | 22 | 126 | Strategy resolution, ComposedStrategy, ConfigRewriteStrategy |
| `trust_boundary.py` | 21 | 168 | Structural + semantic validation, ValidationError conversion |
| `merge_automation.py` | 18 | 197 | Section merge, ordering, idempotency |
| `repair_loop.py` | 18 | 219 | fix_report parsing, review_status determination, re-merge |
| `batch_fetch.py` | 12 | 170 | Batch fetch, collected.json update |
| `reporter_postprocess` | 22 | 99 | `_post_process`, bare URL fix |
| `fetch_cleaner.py` | 17 | 93 | Content cleaning, HTML stripping |
| `proceed_trust_boundary` | 16 | 132 | Proceed + trust boundary integration |
| `utils.py` | 28 | 146 | URL normalization, JSON I/O, hash computation |
| `exceptions` | 13 | 38 | Exception hierarchy + ValidationError |
| `reset` | 10 | 88 | All 4 phase resets |
| `v3_integration` | 11 | 132 | v3 integration |
| **Total** | **897** | **~9,752** | |

**Test patterns**: `tmp_path` for file isolation, `unittest.mock.patch` to override `WORKDIR` and `sys.exit`, `argparse.Namespace` constructed directly (no subprocess), ADR references in test comments.

---

## 11. Code Style Patterns

| Aspect | Convention |
|---|---|
| Type hints | `from __future__ import annotations` everywhere; all signatures typed; `typing.cast` for JSON-loaded data |
| Imports | stdlib first, then project-internal; relative imports (`from .module import`); lazy imports for circular-avoidance |
| Docstrings | `"""one-line"""` style; concise; some private functions lack docstrings |
| Naming | `snake_case` functions/vars, `PascalCase` classes/tests, `UPPER_CASE` module constants, `_` prefix for private |
| Side effects | No global mutable state; all state in JSON files; print to stdout/stderr; `sys.exit(n)` for CLI exit codes |
| Config injection | Functions accept `config: dict | None` parameter for testability |
| Async | None — all code is synchronous |
| Constants | All shared constants in `lib/constants.py`; only module-local constants (regex patterns) remain in their modules |
| Deep modules | `ClaimValidator`, `SearchGate` are class-based deep modules that load data once and expose a `check()` method; `artifact_checks` remains function-based for simpler checks |
| Module extractions | Trust boundary (ADR 0053), repair loop (ADR 0055), sanitizer (ADR 0063), CheckResult (ADR 0061) extracted from proceed.py/artifact_checks.py into standalone modules |

---

## 12. Known Issues and Gaps

1. **No schema library**: Validation is manual via `schemas.py` TypedDict definitions + hand-written validators. No Pydantic/dataclasses for schema enforcement — fragile if schemas evolve.
2. **No concurrency**: All operations synchronous and sequential. SKILL.md says "parallel" section writing but code doesn't implement it.
3. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
4. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
5. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` or `reset` removes them.
6. **CJK word count approximation**: `_count_words` uses segment-based counting (continuous CJK chars = 1 word) rather than proper segmentation. Deliberate tradeoff (ADR 0012).
7. **Chinese source fetch reliability**: Many Chinese sources (36氪, 机器之心, 掘金, V2EX, 中文维基百科) require exa as primary fetch path; webfetch alone returns insufficient content or fails. Weibo is best-effort (login-wall/anti-bot). Zhihu is the dependable Chinese-community voice.

---

## 13. ADR Index (63 ADRs)

| ADR | Title | Key Decision |
|---|---|---|
| 0001 | Topic coverage token matching | Use jieba for Chinese tokenization (superseded by ADR 0012) |
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
| 0012 | Concreteness gate and CJK word counting | Add content_concreteness + methodology_depth; CJK segment-based counting; supersedes ADR 0001 |
| 0013 | Source credibility and recommendation structure | Tier star labels; source_tier_balance gate; recommendation_structure gate |
| 0014 | Custom exceptions and file operation retry | 3-level exception hierarchy; read_json/write_json retry on OSError only |
| 0015 | Centralized schema validation | TypedDict + lib/schemas.py; ValidationError dataclass |
| 0016 | Reset subcommand | reset --phase X CLI command |
| 0017 | covered_directions field and gate improvements | covered_directions override; _sanitize_sections; precision_inflation degrades |
| 0018 | CLI entry, report auto-fix, precision, URL | cmd_report; _sanitize_sections auto-fix; precision downgrade; URL bare-fix |
| 0019 | Pipeline state, self-loop, normalization, optional tiers | Explicit pipeline_state.json; review→review self-loop; optional_tiers |
| 0020 | Claim source relevance gate | Flag claims whose source text doesn't contain key numbers/names |
| 0021 | Report rendering verification step | Final→cleanup transition runs report checks |
| 0022 | Deepen search gate into SearchGate module | Extract search gate logic into SearchGate class |
| 0023 | Remove gateway re-export layer | Delete gateway.py; import directly from artifact_checks and report_checks |
| 0024 | Deepen claim validation into ClaimValidator module | Extract claim checks into ClaimValidator class |
| 0025 | Gate phase responsibility split | Each gate checks only its own phase's concerns |
| 0026 | F1/F2/F9 BLOCKER upgrade | Upgrade dangling refs, orphaned defs, front matter to BLOCKER |
| 0027 | PR-001 design decisions | Review subagent no longer sets verified; claim_verified check level reduced |
| 0028 | Repositioning to research starting point | Pipeline output is starting point, not citable authority; verification summary; review mandatory |
| 0029 | Gate philosophy shift | Auto-downgrade + honestly mark; precision_inflation all WARN; claim_verified removed; Phase 4 removed |
| 0030 | Source fidelity and fetch strategy | Source files in .workdir/sources/; source_fidelity gate replaces fetched_content_depth |
| 0031 | Route decisions (grilling session) | Updated routes for 7 goal_types; +Tier 3/4 for broader coverage |
| 0038 | FetchStrategy Protocol split | UrlRewriter (code) + FetchStrategy (composed); config is single source of truth for tools |
| 0039 | fetched_content from source file | fetched_content derived from source file first 200 chars; source_file field |
| 0040 | Snippet overlap heuristic | Detect summary-not-full: >30% source files with >80% snippet overlap → BLOCKER |
| 0041 | Batch-fetch CLI | Process multiple URLs from stdin; update collected.json automatically |
| 0042 | Remove search_plan, unpin directions | Agent searches freely; config as repair toolbook; min_sources/tier_coverage upgraded to BLOCKER |
| 0043 | Remove source_hints from section plan | Subagent prompt injects all sources; subagent self-selects |
| 0045 | Unified field naming | text→summary, source_urls→sources across key_insights/tensions/claims |
| 0046 | search_directions as fallback reference | Directions are interview context, not gate-enforced (superseded by ADR 0052) |
| 0048 | Windows UTF-8 mode | Force UTF-8 in __main__.py on Windows |
| 0049 | panoramic_understanding Tier 2 required | panoramic route changed to [2,1,3,4]; Tier 2 now required |
| 0050 | Facet coverage safety net | Goal_type-aware fixed facet set; community requires ≥2 platforms |
| 0051 | Primary source ratio metric | Tier/platform skew advisory metric |
| 0052 | Direction field on collected entries | direction field + direction_tagging BLOCKER + direction_coverage BLOCKER |
| 0053 | Trust boundary for subagent output | Two-layer validation (structural + semantic); retry max 2; 3 failures → BLOCK; incomplete section |
| 0054 | Merge automation | Auto-merge section files when analysis.json missing; URL consistency check |
| 0055 | Automated repair loop | review→fix→re-validate cycle; fix_list.json + fix_report.json; max 2 rounds; passed/degraded |
| 0056 | Pipeline repair merge + report checks as CLI post-step | Re-merge after fix; report checks moved from pipeline gate to cmd_report post-step |
| 0058 | Source type enum unification | 8 valid source_type values; alias auto-fix; vendor_benchmark tier-aware indirectness |
| 0060 | Agent-driven section ordering | order field for explicit reading position; quantitative vs exploratory sorting regimes |
| 0061 | CheckResult extraction | CheckResult → lib/check_types.py; read_artifact helper |
| 0062 | Repair loop extraction | repair_loop.py as standalone module |
| 0063 | Sanitizer extraction | sanitize_sections → sanitizer.py as standalone module |
