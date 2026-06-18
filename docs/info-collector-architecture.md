# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~1,722 lines (9 modules) |
| Tests | ~4,295 lines (12 files, 348 test functions) |
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
| 4 | `scripts/cli.py` | 237 | CLI entry: 6 subcommands, argparse, `sys.exit` on gate fail; catches `InfoCollectorError` |
| 5 | `scripts/gateway.py` | 715 | Quality gate engine: 15 checks, `CheckResult` dataclass |
| 6 | `scripts/proceed.py` | 377 | Phase transition gates, phase detection, CJK tokenization, `_sanitize_sections`, `covered_directions` support |
| 7 | `scripts/reporter.py` | 213 | Markdown report generator: YAML front matter, i18n, references, tier star labels |
| 8 | `scripts/lib/__init__.py` | 0 | Empty |
| 9 | `scripts/lib/constants.py` | 19 | Shared stop-word sets: `_ENGLISH_STOP_WORDS` (37), `_CHINESE_STOP_WORDS` (49) |
| 10 | `scripts/lib/exceptions.py` | 35 | Custom exception hierarchy: `InfoCollectorError`, `GateFailureError`, `ArtifactError`; `ValidationError` dataclass |
| 11 | `scripts/lib/utils.py` | 64 | `normalize_url`, `read_json` (with retry), `write_json` (with retry), `_find_project_root`, `ensure_dir` |
| 12 | `scripts/lib/source_router.py` | 83 | Pure-function routing: `get_route`, `recommend_sources`, defaults |
| 13 | `scripts/lib/schemas.py` | 232 | Centralized schema validation: TypedDict definitions + `validate_scope`, `validate_analysis`, `validate_collected` (ADR 0015) |
| 14 | `references/GATES.md` | — | 5-gate system reference |
| 15 | `references/REVIEW_PROMPT.md` | — | Review sub-agent prompt template |
| 16 | `references/cli-reference.md` | — | CLI commands reference |
| 17 | `references/subagent-template.md` | — | Subagent delegation template with JSON schema embedding |
| 18 | `references/writing-guide.md` | — | Writing guide for analysis.json content quality |

### Test Files

| # | Path | Lines | Tests | Coverage |
|---|---|---|---|---|
| 1 | `tests/conftest.py` | 4 | — | Adds skill dir to `sys.path` |
| 2 | `tests/__init__.py` | 0 | — | Empty |
| 3 | `tests/test_cli.py` | 484 | 30 | All 6 commands + project root detection + `_build_report_filename` + `_detect_quality` verdict parsing + `InfoCollectorError` catch in main |
| 4 | `tests/test_gateway.py` | 1,390 | 77 | All 15 gate checks, edge cases, `CheckResult`, `run_all`; precision_inflation with source text checks; claim_verified with unverifiable + ratio |
| 5 | `tests/test_gateway_import.py` | 44 | 1 | Gateway import guard (jieba not imported at module level) |
| 6 | `tests/test_content_concreteness.py` | 362 | 29 | `_count_words`, vague phrase detection, number/name presence, CJK specifics |
| 7 | `tests/test_exceptions.py` | 54 | 13 | Exception hierarchy + `ValidationError` dataclass: equality, fields |
| 8 | `tests/test_proceed.py` | 591 | 44 | Phase detection + gate routing + per-direction min sources + CJK coverage + `covered_directions` + `_sanitize_sections` |
| 9 | `tests/test_reporter.py` | 654 | 42 | Report pipeline + i18n + test conditions + reference numbering + tier labels |
| 10 | `tests/test_source_router.py` | 160 | 17 | Router functions + integration against real config.json |
| 11 | `tests/test_utils.py` | 136 | 17 | URL normalization + JSON I/O with retry + directory creation |
| 12 | `tests/test_reset.py` | 125 | 10 | Reset subcommand: scope/search/analysis/review reset, phase detection after reset, invalid phase |
| 13 | `tests/test_schemas.py` | 390 | 68 | Schema validation: scope, analysis, collected; english_title requirement; covered_directions; ValidationError equality |

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
    proceed --from review --to final   <-- Gate 4: full 15-check gateway
                |
                v
  Phase 3c: Final report generation
  cli.py report --quality ...          <-- reporter.py generates Markdown
  _detect_quality() parses verdict:
    **pass** → "passed"
    **pass_with_issues** → "degraded"
    **fail** → sys.exit(1)
                |
                v
  <output_dir>/<english_title_or_topic>.md
  (YAML front matter + numbered refs + appendix + tier star labels)
  Filename collision → append _YYYY-MM-DD
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
| `analysis.json` exists AND `review_report.md` doesn't | `post_analysis` |
| `review_report.md` exists | `post_review` |

### Valid Transitions

```
scope -> search -> analysis -> review -> final -> cleanup
```

---

## 4. API Surface — Function Reference

### 4.1 `scripts/cli.py` — CLI Entry Point (237 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone 15-check gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > `"en"` |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `cmd_reset` | `(args: Namespace) -> None` | Reset pipeline to a given phase by deleting target and subsequent artifacts (ADR 0016) |
| `_detect_quality` | `() -> str` | Parse `## Overall Verdict` in review_report.md: `**pass**` → "passed", `**pass_with_issues**` → "degraded", `**fail**` → sys.exit(1), unparseable → "degraded" (ADR 0017) |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_read_topic` | `(scope_path: Path) -> str` | Read topic from scope.json, fallback `"untitled"` |
| `_build_report_filename` | `(scope_data: dict, output_path: Path) -> Path` | Build safe ASCII report filename; prefers `english_title` over `topic`; appends `_YYYY-MM-DD` on collision |
| `main` | `() -> None` | Argparse setup + dispatch; catches `InfoCollectorError` at top level |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|review|final|cleanup
gateway                    # Standalone 15-check run
report [--quality Q] [--search-rounds N] [--source-count N] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
reset --phase <X>          # X: scope|search|analysis|review — delete target + subsequent artifacts
```

**Module-level constants:**

| Name | Description |
|---|---|
| `WORKDIR` | `_find_project_root() / ".workdir"` |
| `_CONFIG_PATH` | `Path(__file__).parent.parent / "config.json"` |
| `_PHASE_ARTIFACTS` | `dict[str, list[str]]` — maps phase name to artifact filenames deleted on reset |

### 4.2 `scripts/gateway.py` — Quality Gate Engine (715 lines)

**Data class:**

```python
@dataclass
class CheckResult:
    name: str
    level: str      # "BLOCKER" | "WARN"
    passed: bool
    message: str = ""
```

**15 Check Functions:**

| Function | Level | Purpose |
|---|---|---|
| `check_artifact_exists` | BLOCKER | scope.json + collected.json + analysis.json must exist |
| `check_url_traceability` | BLOCKER | All claim source_urls must normalize-match collected.json URLs |
| `check_section_coverage` | BLOCKER | Required section IDs per goal_type (lookup table) |
| `check_analysis_schema` | BLOCKER/WARN | Delegates to `validate_analysis()` from schemas.py; warns on duplicate `## ` headings |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `check_precision_inflation` | BLOCKER + WARN | Exact precision + wrong evidence_type (BLOCKER); third_party + unverified precise numbers (WARN, skips if source <200 chars); conflicting exact values in same metric_type (BLOCKER) |
| `check_metric_type_homogeneity` | BLOCKER | No mixing different metric_types within same section level (only checks claims with evidence_type in official_data/independent_benchmark) |
| `check_claim_verified` | BLOCKER + WARN | verified=False = BLOCKER; verified="unverifiable" = WARN; ratio < 60% = WARN; skipped if no review_report.md |
| `check_source_metadata` | BLOCKER | official_data/independent_benchmark claims require non-empty source_metadata.test_conditions |
| `check_content_concreteness` | BLOCKER/WARN (depends on goal_type) | Quantitative types: vague phrase density >10% (WARN); missing numbers/names in strict types (BLOCKER), others (WARN) |
| `check_methodology_depth` | WARN | Quantitative types: methodology section <150 words or lacks Markdown table |
| `check_recommendation_structure` | WARN | tech_selection/competitive_comparison: recommendation section lacks comparison table or "not recommended" |
| `check_source_tier_balance` | WARN | Quantitative types: Tier 1+2 source ratio <30% among referenced URLs |
| `check_claim_dedup` | WARN | Same claim text appears in multiple sections |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]`

**Private helpers:** `_validate_section_claims`, `_number_found_in_source`, `_count_words`, `_has_valid_number`, `_has_concrete_name`

### 4.3 `scripts/proceed.py` — Phase Transition Gates (377 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_is_stop_word` | `(token: str) -> bool` | Filter tokens <=1 char, punctuation, or in stop-word sets |
| `_tokenize_direction` | `(direction: str) -> list[str]` | Inline CJK segmentation + stop-word filtering (no jieba) |
| `_sanitize_sections` | `(analysis: dict) -> dict` | Normalize subagent output: `section_id` → `id`, `sources` → `source_urls`, strip non-schema keys, default `claims` to `[]` (ADR 0017) |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from artifact existence |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json via `schemas.validate_scope()` |
| `_has_cjk_tokens` | `(directions: list[str]) -> bool` | Check if any search direction contains CJK characters |
| `_check_search_gate` | `(workdir: Path, config?) -> tuple[list[str], list[str]]` | Search quality: (blockers, warnings); CJK directions downgrade topic_coverage to WARN; `covered_directions` override; schema validation via `schemas.validate_collected()` |
| `_check_url_traceability` | `(analysis: dict, collected: list[dict]) -> list[str]` | Lightweight URL traceability check (used in analysis→review gate) |
| `_generate_search_plan` | `(workdir: Path, config?) -> None` | Write search_plan.json with direction x tier tasks |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions + runs phase-specific gates |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `gateway.run_all()` |

**Depth -> Min Sources Per Direction:** `quick=1`, `standard=3`, `deep=5`

**Module-level constants:**

| Name | Value |
|---|---|
| `_STOP_WORDS` | `_ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS` |
| `_DEPTH_MIN_SOURCES_PER_DIRECTION` | `{"quick": 1, "standard": 3, "deep": 5}` |
| `_COVERAGE_THRESHOLD` | `0.5` |
| `_SECTION_KEYS` | `frozenset({"id", "title", "content", "claims"})` |
| `_CLAIM_KEYS` | `frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified"})` |
| `_VALID_TRANSITIONS` | `{"scope": "search", "search": "analysis", "analysis": "review", "review": "final", "final": "cleanup"}` |

### 4.4 `scripts/reporter.py` — Report Generator (213 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_build_reference_map` | `(analysis: dict, collected: list[dict]) -> dict[str, int]` | Build `{normalized_url -> ref_number}` by first-occurrence order |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix with tier star labels (★★★☆) |
| `build_front_matter` | `(topic, goal_type, scope, quality, search_rounds, source_count, audience?, report_language?) -> str` | YAML front matter block (8-12 fields) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `_build_claim_ref` | `(claim, reference_map) -> str` | Build `[N]` reference number from normalized URL |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body; exploratory types use compact mode (claims omitted) |
| `generate_report` | `(analysis_path, scope_path, quality, search_rounds, source_count, report_language?) -> str` | Main entry: reads files, builds front matter + body |

**i18n Labels (8 pairs):** Sources/数据来源, References/参考文献, Test Conditions/测试环境, Claim/声明, Conditions/条件, Date/日期, Source Type/来源类型, Methodology/方法论

**Tier Star Labels:** Tier 1 → ★★★☆, Tier 2 → ★★☆☆, Tier 3 → ★☆☆☆, Tier 4 → ☆☆☆☆

### 4.5 `scripts/lib/source_router.py` — Source Routing (83 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_get_config` | `(config?) -> dict` | Return injected config or load from disk |
| `get_route` | `(goal_type, config?) -> dict` | Return route dict (entry_tier, path); unknown -> "other" |
| `recommend_sources` | `(goal_type, config?) -> dict` | Structured output with recommended/all sources |
| `get_default_min_sources` | `(goal_type, config?) -> int` | Lookup from goal_type_defaults, fallback 2 |
| `get_default_depth` | `(goal_type, config?) -> str` | Priority: goal_type_defaults > config.default_depth > "standard" |

### 4.6 `scripts/lib/utils.py` — Utilities (64 lines)

| Function | Signature | Purpose |
|---|---|---|
| `normalize_url` | `(url: str) -> str` | Lowercase, strip www, sort query params, strip fragment, strip trailing slash |
| `read_json` | `(path: Path, retries: int = 2, delay: float = 0.5) -> Any` | `json.load()` with UTF-8; retries on OSError; raises `ArtifactError` on JSONDecodeError or exhausted retries |
| `write_json` | `(data, path: Path, retries: int = 2, delay: float = 0.5) -> None` | `json.dump()` with UTF-8, indent=2, ensure_ascii=False; auto-mkdir; retries on OSError; raises `ArtifactError` on exhausted retries |
| `_find_project_root` | `() -> Path` | Walk up from CWD to find `.git` directory; fallback to CWD |
| `ensure_dir` | `(path: Path) -> Path` | `mkdir(parents=True, exist_ok=True)` + return path |

### 4.7 `scripts/lib/constants.py` — Shared Constants (19 lines)

| Name | Type | Purpose |
|---|---|---|
| `_ENGLISH_STOP_WORDS` | `frozenset` (37 words) | English stop words for tokenization |
| `_CHINESE_STOP_WORDS` | `frozenset` (49 chars) | Chinese stop words for tokenization |

### 4.8 `scripts/lib/exceptions.py` — Custom Exceptions + ValidationError (35 lines)

| Class | Base | Attributes | Purpose |
|---|---|---|---|
| `InfoCollectorError` | `Exception` | — | Base exception for all info-collector errors |
| `GateFailureError` | `InfoCollectorError` | `phase: str`, `blockers: list[str]` | Gate check failed with BLOCKER-level issues |
| `ArtifactError` | `InfoCollectorError` | `path: str`, `reason: str` | Artifact file missing, unreadable, or schema-invalid |
| `ValidationError` | `@dataclass` (not Exception) | `field: str`, `message: str` | Schema validation error carrier (ADR 0015) |

### 4.9 `scripts/lib/schemas.py` — Centralized Schema Validation (232 lines)

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

**Module-level constants:**

| Name | Value |
|---|---|
| `_VALID_GOAL_TYPES` | frozenset of 10 goal types |
| `_VALID_DEPTHS` | frozenset {"quick", "standard", "deep"} |
| `_VALID_AUDIENCES` | frozenset {"CTO", "engineer", "researcher", "general"} |
| `_VALID_METRIC_TYPES` | frozenset of 6 metric types |
| `_SCOPE_REQUIRED_FIELDS` | tuple of 6 fields |
| `_ANALYSIS_REQUIRED_FIELDS` | tuple of 2 fields |
| `_SECTION_REQUIRED_FIELDS` | tuple of 3 fields |
| `_CLAIM_REQUIRED_FIELDS` | tuple of 2 fields |
| `_COLLECTED_REQUIRED_FIELDS` | tuple of 3 fields |

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

- **scope.json schema validation** via `schemas.validate_scope()`: 6 required fields (topic, goal_type, depth, audience, scope_description, search_directions)
- **Enum validation**: goal_type in 10 values, depth in {quick, standard, deep}, audience in {CTO, engineer, researcher, general}
- **english_title**: required (BLOCKER) when topic contains non-ASCII characters
- **Generates**: `search_plan.json` with direction x tier search tasks

### Gate 2: Search -> Analysis

| Check | Level | Logic |
|---|---|---|
| topic_coverage | BLOCKER (non-CJK) / WARN (CJK) | Two-pass: (1) entries with `covered_directions` override token matching; (2) remaining entries use token matching. CJK-heavy directions downgrade to WARN |
| tier_coverage | WARN | All tiers in goal_type route must have >=1 source in collected.json |
| per_direction_min_sources | WARN | Depth-driven: quick=1, standard=3, deep=5 per direction |
| min_sources | WARN | Total collected entries >= goal_type default (fallback 2) |
| schema validation | BLOCKER | `schemas.validate_collected()` validates entry structure + covered_directions constraints |

### Gate 3: Analysis -> Review

- `_sanitize_sections()` normalizes subagent output: `section_id` → `id`, `sources` → `source_urls`, strips non-schema keys, defaults `claims` to `[]`
- `schemas.validate_analysis()` validates structure
- URL traceability: all claim source_urls must normalize-match collected.json URLs (BLOCKER, via `gateway.run_all`)

### Gate 4: Review -> Final

Full 15-check gateway run (see section 4.2). Only BLOCKER-level failures block this transition; WARN-level failures are reported but do not prevent proceeding. Notable checks:

- **precision_inflation**: Detects exact-precision claims with wrong evidence types (BLOCKER), third-party estimates with unverified precise numbers (WARN, skips if source text <200 chars), conflicting exact values within same metric_type (BLOCKER)
- **metric_type_homogeneity**: No mixing metric_types within a section for official_data/independent_benchmark claims (ensures clean benchmark tables)
- **claim_verified**: verified=False = BLOCKER; verified="unverifiable" = WARN; ratio < 60% = WARN; skipped if no review_report.md
- **content_concreteness**: Vague phrase density >10% (WARN); missing numbers/names in strict goal types (BLOCKER), others (WARN)
- **methodology_depth**: Methodology section <150 words or lacks Markdown table (WARN)
- **recommendation_structure**: tech_selection/competitive_comparison recommendation section lacks comparison table or "not recommended" (WARN)
- **source_tier_balance**: Tier 1+2 source ratio <30% among referenced URLs (WARN)
- **claim_dedup**: Same claim text appears in multiple sections (WARN)

### Gate 5: Final -> Cleanup

Always passes — no structural checks.

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
      "min_sources": "int"
    }
  ]
}
```

---

## 8. Constants Reference

### lib/constants.py

```python
_ENGLISH_STOP_WORDS = frozenset({...})    # 37 words
_CHINESE_STOP_WORDS = frozenset({...})    # 49 characters
```

### lib/schemas.py

```python
_VALID_GOAL_TYPES = frozenset({...})          # 10 types
_VALID_DEPTHS = frozenset({"quick", "standard", "deep"})
_VALID_AUDIENCES = frozenset({"CTO", "engineer", "researcher", "general"})
_VALID_METRIC_TYPES = frozenset({...})         # 6 types
_SCOPE_REQUIRED_FIELDS = (...)                 # 6 fields
_ANALYSIS_REQUIRED_FIELDS = (...)              # 2 fields
_SECTION_REQUIRED_FIELDS = (...)               # 3 fields
_CLAIM_REQUIRED_FIELDS = (...)                 # 2 fields
_COLLECTED_REQUIRED_FIELDS = (...)             # 3 fields
```

### gateway.py

```python
_VAGUE_PHRASES_ZH = frozenset({...})      # 12 Chinese vague phrases
_VAGUE_PHRASES_EN = frozenset({...})      # 10 English vague phrases
_VAGUE_DENSITY_THRESHOLD = 0.10
_CONCRETENESS_STRICT_GOAL_TYPES = frozenset({"tech_selection", "competitive_comparison"})
_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')
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
_TIER_BALANCE_THRESHOLD = 0.30
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
_VERSION_PATTERN = re.compile(...)
_LIST_ITEM_PATTERN = re.compile(...)
_NUMBER_PATTERN = re.compile(...)
_METHODOLOGY_MIN_WORDS = 150
```

### proceed.py

```python
_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS   # from lib.constants
_DEPTH_MIN_SOURCES_PER_DIRECTION = {"quick": 1, "standard": 3, "deep": 5}
_COVERAGE_THRESHOLD = 0.5
_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({"text", "source_urls", "evidence_type", "confidence", "precision", "metric_type", "source_metadata", "verified"})
_VALID_TRANSITIONS = {
    "scope": "search", "search": "analysis",
    "analysis": "review", "review": "final", "final": "cleanup",
}
```

### reporter.py

```python
_TIER_LABELS = {"1": "★★★☆ Tier 1", "2": "★★☆☆ Tier 2", "3": "★☆☆☆ Tier 3", "4": "☆☆☆☆ Tier 4"}
_LABELS = {...}  # 8 i18n key pairs (en + zh)
_EXPLORATORY_GOAL_TYPES = frozenset({"exploratory", "panoramic_understanding", "background_check", "other"})
```

---

## 9. Import Dependency Graph

```
cli.py -----> lib.exceptions (InfoCollectorError)
       |-----> lib.utils (_find_project_root)
       |-----> proceed.py (lazy import, circular-avoidance)
       |-----> reporter.py (lazy import)
       |-----> lib.source_router (recommend_sources, lazy import)
       |-----> lib.utils (read_json, lazy import in cmd_report/_count_sources/_read_topic)

proceed.py -> lib.utils (ensure_dir, normalize_url, read_json, write_json)
           -> lib.source_router (get_default_min_sources, get_route, recommend_sources)
           -> lib.exceptions (ArtifactError)
           -> lib.constants (_CHINESE_STOP_WORDS, _ENGLISH_STOP_WORDS)
           -> lib.schemas (validate_scope, validate_analysis, validate_collected)
           -> gateway.py (run_all, CheckResult)
           -> cli.py (_find_project_root)

gateway.py -> lib.constants (_CHINESE_STOP_WORDS)
           -> lib.exceptions (ArtifactError)
           -> lib.schemas (validate_analysis)
           -> lib.utils (normalize_url, read_json)

reporter.py -> lib.utils (normalize_url, read_json)

source_router.py -> (no internal imports)

schemas.py -> exceptions (ValidationError)

constants.py -> (no internal imports)

exceptions.py -> (no internal imports)

utils.py -> exceptions (ArtifactError)
```

**External deps:** `argparse` (cli.py), `dataclasses` (gateway.py, exceptions.py), `re` (cli.py, gateway.py, proceed.py), `string` (proceed.py), `time` (utils.py), `urllib.parse` (utils.py), `typing` (cli.py, proceed.py, schemas.py, source_router.py)

---

## 10. Error Handling Patterns

1. **Custom exception hierarchy**: `InfoCollectorError` base → `GateFailureError` (gate failures) + `ArtifactError` (file I/O). Top-level `cli.py:main()` catches `InfoCollectorError` uniformly. `ValidationError` is a dataclass (not an Exception) used by schemas.py for validation results.
2. **Gate-based error handling**: Almost all errors are terminal via `sys.exit(1)`. No graceful degradation on BLOCKER.
3. **JSON parse errors**: `read_json()` raises `ArtifactError` on `json.JSONDecodeError` (no retry — content corruption is permanent) and on exhausted `OSError` retries.
4. **File operation retry**: `read_json()`/`write_json()` retry up to 3 times (default `retries=2, delay=0.5`) on `OSError` only. `json.JSONDecodeError` is not retried (ADR 0014).
5. **Defensive fallbacks**: `_count_sources()` and `_read_topic()` use `try/except Exception` to return safe defaults (0 or `"untitled"`).
6. **WARN vs BLOCKER**: Two-tier severity. `proceeds()` prints WARN to stderr but continues; BLOCKER stops the gate and returns error list.
7. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` prefixes.
8. **Stateless phase detection**: `detect_current_phase()` is pure — derives state from file existence, no mutable state.
9. **Subagent output sanitization**: `_sanitize_sections()` in proceed.py normalizes known field name variations and strips unknown keys, providing a safety net against subagent output drift (ADR 0017).

---

## 11. Test Coverage Summary

| Module | Tests | Lines | Notable | Gaps |
|---|---|---|---|---|
| `cli.py` | 30 | 484 | All 6 commands; `_build_report_filename`; `_detect_quality` verdict parsing; project root detection; `InfoCollectorError` catch in main | `cmd_report` with incomplete scope.json |
| `gateway.py` | 77 | 1,390 | All 15 checks with edge cases; precision_inflation with source text checks; claim_verified with unverifiable + ratio | None |
| `content_concreteness` | 29 | 362 | `_count_words` CJK segmentation; vague phrase density; number/name presence; strict vs non-strict goal types | None |
| `exceptions` | 13 | 54 | Exception hierarchy + `ValidationError` equality | None |
| `gateway_import` | 1 | 44 | jieba not imported at module level | None |
| `proceed.py` | 44 | 591 | Phase detection (5 states); 5 gate transitions; Chinese search directions; per-direction min sources; tier coverage; `covered_directions`; `_sanitize_sections` | `_generate_search_plan` output shape not tested |
| `reporter.py` | 42 | 654 | Reference map dedup; test conditions table (6 cases); i18n labels (zh/en/fallback); full pipeline; `report_language` priority; tier star labels | Empty analysis.json not tested |
| `source_router.py` | 17 | 160 | Route resolution; unknown goal_type fallback; min sources; depth priority; integration against real config.json | None |
| `utils.py` | 17 | 136 | URL normalization (8 cases); JSON read/write round-trip with retry; directory creation; ArtifactError on JSONDecodeError | Write permission errors not tested |
| `reset` | 10 | 125 | All 4 phase resets + phase detection + invalid + nothing-to-remove | No test for `search_plan.json` deletion on scope reset |
| `schemas` | 68 | 390 | Full scope/analysis/collected validation; `english_title` requirement; `covered_directions` constraints; `ValidationError` equality | None |
| **Total** | **348** | **~4,295** | | |

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

1. **No schema library**: Validation is manual via `schemas.py` TypedDict definitions + hand-written validators. No Pydantic/dataclasses for schema enforcement — fragile if schemas evolve.
2. **Test gaps**: `cmd_gateway` only tests pass path; `_generate_search_plan` output shape untested; `cmd_report` incomplete scope.json untested.
3. **No concurrency**: All operations synchronous and sequential. SKILL.md says "parallel" section writing but code doesn't implement it.
4. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
5. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
6. **Silent exception swallowing**: `_count_sources()` and `_read_topic()` use `except Exception` fallbacks.
7. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` or `reset` removes them.
8. **CJK word count approximation**: `_count_words` uses segment-based counting (continuous CJK chars = 1 word) rather than proper segmentation. This is a deliberate tradeoff (ADR 0012) — mitigated by `covered_directions` (ADR 0017) which provides an agent-declaration alternative to token-based matching.
9. **proceed.py duplicates gateway logic**: `_check_url_traceability` in proceed.py mirrors `check_url_traceability` in gateway.py — the proceed version is a lightweight check for Gate 3, while the gateway version runs as part of the full 15-check suite in Gate 4.

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
