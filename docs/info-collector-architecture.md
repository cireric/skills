# Info-Collector Skill Architecture Reference

> Auto-generated from codebase exploration. Covers structure, data flow, API surface, quality gates, configuration, testing, and known issues.

## 1. Overview

Info-Collector is a **gate-based pipeline skill** for collecting, organizing, and summarizing structured information from web sources. It is fully self-contained (zero shared code with other skills) and **stateless** — all intermediate state lives in JSON files under `.workdir/`.

| Metric | Value |
|---|---|
| Python source | ~1,644 lines (8 modules) |
| Tests | ~3,576 lines (10 files, 242 test functions in 9 test files) |
| Config/docs | config.json + SKILL.md + 2 reference docs |
| Runtime pip deps | None (jieba removed; ADR 0001 superseded by ADR 0012) |
| HTTP deps | None — search done externally by AI via exa/playwright |

---

## 2. File Listing

### Source Files

| # | Path | Purpose |
|---|---|---|
| 1 | `SKILL.md` | Skill definition: 352 lines, 4-phase workflow + Setup Wizard, CLI reference, quality values |
| 2 | `config.json` | 4-tier source config + 10 goal-type routes + output settings |
| 3 | `scripts/__init__.py` | Empty (package marker) |
| 4 | `scripts/cli.py` | CLI entry: 5 subcommands, argparse, `sys.exit` on gate fail; catches `InfoCollectorError` |
| 5 | `scripts/gateway.py` | Quality gate engine: 15 checks, `CheckResult` dataclass |
| 6 | `scripts/proceed.py` | Phase transition gates, phase detection, CJK tokenization (no jieba — uses inline segmentation) |
| 7 | `scripts/reporter.py` | Markdown report generator: YAML front matter, i18n, references, tier star labels |
| 8 | `scripts/lib/__init__.py` | Empty |
| 9 | `scripts/lib/constants.py` | Shared stop-word sets: `_ENGLISH_STOP_WORDS` (27), `_CHINESE_STOP_WORDS` (60) |
| 10 | `scripts/lib/exceptions.py` | Custom exception hierarchy: `InfoCollectorError`, `GateFailureError`, `ArtifactError` |
| 11 | `scripts/lib/utils.py` | `normalize_url`, `read_json` (with retry), `write_json` (with retry), `_find_project_root`, `ensure_dir` |
| 12 | `scripts/lib/source_router.py` | Pure-function routing: `get_route`, `recommend_sources`, defaults |
| 13 | `references/GATES.md` | 5-gate system reference |
| 14 | `references/REVIEW_PROMPT.md` | Review sub-agent prompt template |

### Test Files

| # | Path | Lines | Coverage |
|---|---|---|---|
| 1 | `tests/conftest.py` | 4 | Adds skill dir to `sys.path` |
| 2 | `tests/__init__.py` | 0 | Empty |
| 3 | `tests/test_cli.py` | 337 | 5 command handlers + project root detection + main dispatch |
| 4 | `tests/test_gateway.py` | 1,316 | All 15 gate checks, edge cases, `CheckResult`, `run_all` |
| 5 | `tests/test_gateway_import.py` | 37 | Gateway import guard (jieba not imported at module level) |
| 6 | `tests/test_content_concreteness.py` | 362 | `_count_words`, vague phrase detection, number/name presence, CJK specifics |
| 7 | `tests/test_exceptions.py` | 54 | Exception hierarchy: `InfoCollectorError`, `GateFailureError`, `ArtifactError` |
| 8 | `tests/test_proceed.py` | 516 | Phase detection + gate routing + per-direction min sources + CJK coverage |
| 9 | `tests/test_reporter.py` | 654 | Report pipeline + i18n + test conditions + reference numbering + tier labels |
| 10 | `tests/test_source_router.py` | 160 | Router functions + integration against real config.json |
| 11 | `tests/test_utils.py` | 136 | URL normalization + JSON I/O with retry + directory creation |

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
                |                           |-- topic_coverage (BLOCKER for non-CJK, WARN for CJK)
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
    proceed --from analysis --to review  <-- Gate 3: analysis + URL traceability
                |                           |-- analysis.json has topic + goal_type
                |                           |-- analysis.json sections non-empty
                |                           +-- URL traceability (all claim URLs in collected.json)
                v
+-------------------------------------+
|  Phase 3b: Review (optional sub-agent)|
|  Review output: review_report.md     |
|  Updates analysis.json verified field|
+---------------+---------------------+
                |
                v
    proceed --from review --to final   <-- Gate 4: full 15-check gateway
                |
                v
  Phase 3c: Final report generation
  cli.py report --quality ...          <-- reporter.py generates Markdown
                |
                v
  <output_dir>/<topic>_v<N>.md
  (YAML front matter + numbered refs + appendix + tier star labels)
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

### 4.1 `scripts/cli.py` — CLI Entry Point (171 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_load_config` | `() -> dict | None` | Load config.json from skill dir; returns None if missing |
| `cmd_proceed` | `(args: Namespace) -> None` | Run phase transition gate; `sys.exit(0/1)` |
| `cmd_gateway` | `(args: Namespace) -> None` | Standalone 15-check gateway run; exit(1) on BLOCKER |
| `cmd_report` | `(args: Namespace) -> None` | Generate final report from analysis.json. Language priority: scope.json `report_language` > config.json `default_report_language` > hardcoded `"zh"`. CJK characters preserved in filenames |
| `cmd_source` | `(args: Namespace) -> None` | Print JSON source recommendations for goal_type |
| `cmd_clean` | `(args: Namespace) -> None` | Delete `.workdir/` via `shutil.rmtree` |
| `_detect_quality` | `() -> str` | `"passed"` if review_report.md exists, else `"unreviewed"` |
| `_count_sources` | `() -> int` | Read collected.json, return entry count (silently returns 0 on error) |
| `_read_topic` | `(scope_path: Path) -> str` | Read topic from scope.json, fallback `"untitled"` |
| `main` | `() -> None` | Argparse setup + dispatch; catches `InfoCollectorError` at top level |

**CLI Subcommands:**

```
proceed --from X --to Y    # X/Y: scope|search|analysis|review|final|cleanup
gateway                    # Standalone 15-check run
report [--quality Q] [--search-rounds N] [--source-count N] [--version N (default=1)] [--output DIR]
source <goal_type>         # Print source recommendations as JSON
clean                      # Remove .workdir/
```

### 4.2 `scripts/gateway.py` — Quality Gate Engine (726 lines)

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
| `check_analysis_schema` | BLOCKER | Top-level fields + section/claim shape validation |
| `check_quality_heuristics` | WARN | Flag if >50% claims have single source |
| `check_claim_metadata` | WARN | For quantitative goal_types: flag if >50% claims missing evidence_type/confidence/precision |
| `check_precision_inflation` | BLOCKER (primary); can return WARN for third-party-estimate findings | Exact precision + wrong evidence_type (BLOCKER); third_party + exact numbers (WARN); conflicting exact values in same metric_type (BLOCKER) |
| `check_metric_type_homogeneity` | BLOCKER | No mixing different metric_types within same section level (only checks claims with evidence_type in official_data/independent_benchmark) |
| `check_claim_verified` | BLOCKER | Post-review: all claims must have `verified=true` |
| `check_source_metadata` | BLOCKER | official_data/independent_benchmark claims require non-empty source_metadata.test_conditions |
| `check_content_concreteness` | BLOCKER/WARN (depends on goal_type) | Quantitative types: vague phrase density >10% (WARN); missing numbers/names in strict types (BLOCKER), others (WARN) |
| `check_methodology_depth` | WARN | Quantitative types: methodology section <150 words or lacks Markdown table |
| `check_recommendation_structure` | WARN | tech_selection/competitive_comparison: recommendation section lacks comparison table or "不推荐"/"not recommended" |
| `check_source_tier_balance` | WARN | Quantitative types: Tier 1+2 source ratio <30% among referenced URLs |
| `check_claim_dedup` | WARN | Same claim text appears in multiple sections |

**Aggregator:** `run_all(workdir, goal_type) -> list[CheckResult]`

**Private helpers:** `_validate_section_claims`, `_number_found_in_source`, `_count_words`, `_has_valid_number`, `_has_concrete_name`

### 4.3 `scripts/proceed.py` — Phase Transition Gates (339 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_is_stop_word` | `(token: str) -> bool` | Filter tokens <=1 char, punctuation, or in stop-word sets |
| `_tokenize_direction` | `(direction: str) -> list[str]` | Inline CJK segmentation + stop-word filtering (no jieba) |
| `detect_current_phase` | `(workdir: Path) -> str` | Derive phase from artifact existence |
| `_check_scope_schema` | `(workdir: Path) -> list[str]` | Validate scope.json fields + enums |
| `_has_cjk_tokens` | `(directions: list[str]) -> bool` | Check if any search direction contains CJK characters |
| `_check_search_gate` | `(workdir: Path, config?) -> tuple[list[str], list[str]]` | Search quality: (blockers, warnings); CJK directions downgrade topic_coverage to WARN |
| `_check_url_traceability` | `(analysis: dict, collected: list[dict]) -> list[str]` | Lightweight URL traceability check (used in analysis→review gate) |
| `_generate_search_plan` | `(workdir: Path, config?) -> None` | Write search_plan.json with direction x tier tasks |
| `_get_goal_type` | `(workdir: Path) -> str` | Read goal_type from scope, default `"other"` |
| `proceeds` | `(workdir, from_phase, to_phase, config?) -> tuple[bool, list[str]]` | Main gate function: validates transitions + runs phase-specific gates |
| `get_gateway_results` | `(workdir: Path) -> list[CheckResult]` | Convenience wrapper for `gateway.run_all()` |

**Depth -> Min Sources Per Direction:** `quick=1`, `standard=3`, `deep=5`

### 4.4 `scripts/reporter.py` — Report Generator (217 lines)

| Function | Signature | Purpose |
|---|---|---|
| `_label` | `(key: str, lang: str) -> str` | i18n lookup: requested lang → English fallback → raw key |
| `_build_reference_map` | `(analysis: dict, collected: list[dict]) -> dict[str, int]` | Build `{normalized_url -> ref_number}` by first-occurrence order |
| `_render_references` | `(reference_map, collected, lang) -> str` | Generate `## References` appendix with tier star labels (★★★☆) |
| `build_front_matter` | `(topic, goal_type, scope, quality, search_rounds, source_count, version, audience?, report_language?) -> str` | YAML front matter block (8-12 fields) |
| `_render_test_conditions` | `(claims, reference_map?, lang) -> str` | Markdown table of claims with source_metadata |
| `_build_claim_ref` | `(claim, reference_map) -> str` | Build `[N]` reference number from normalized URL |
| `sections_to_markdown` | `(analysis, collected?, lang) -> str` | Render full analysis to Markdown body; exploratory types use compact mode (claims omitted) |
| `generate_report` | `(analysis_path, scope_path, quality, search_rounds, source_count, version, report_language?) -> str` | Main entry: reads files, builds front matter + body |

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
| `_ENGLISH_STOP_WORDS` | `frozenset` (27 words) | English stop words for tokenization |
| `_CHINESE_STOP_WORDS` | `frozenset` (60 chars) | Chinese stop words for tokenization |

### 4.8 `scripts/lib/exceptions.py` — Custom Exceptions (25 lines)

| Class | Base | Attributes | Purpose |
|---|---|---|---|
| `InfoCollectorError` | `Exception` | — | Base exception for all info-collector errors |
| `GateFailureError` | `InfoCollectorError` | `phase: str`, `blockers: list[str]` | Gate check failed with BLOCKER-level issues |
| `ArtifactError` | `InfoCollectorError` | `path: str`, `reason: str` | Artifact file missing, unreadable, or schema-invalid |

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
| topic_coverage | BLOCKER (non-CJK) / WARN (CJK) | Every search_direction token must match >=1 collected entry (inline CJK segmentation). CJK-heavy directions downgrade to WARN due to segmentation imprecision |
| tier_coverage | WARN | All tiers in goal_type route must have >=1 source in collected.json |
| per_direction_min_sources | WARN | Depth-driven: quick=1, standard=3, deep=5 per direction |
| min_sources | WARN | Total collected entries >= goal_type default (fallback 2) |

### Gate 3: Analysis -> Review

- analysis.json is readable and has `topic` + `goal_type` keys
- analysis.json `sections` is non-empty
- URL traceability: all claim source_urls must normalize-match collected.json URLs (BLOCKER)

Note: This gate includes lightweight URL traceability validation (via `_check_url_traceability` in proceed.py), not the full gateway run.

### Gate 4: Review -> Final

Full 15-check gateway run (see section 4.2). Only BLOCKER-level failures block this transition; WARN-level failures are reported but do not prevent proceeding. Notable checks:

- **precision_inflation**: Detects exact-precision claims with wrong evidence types (BLOCKER), third-party estimates with precise numbers (WARN), conflicting exact values within same metric_type (BLOCKER)
- **metric_type_homogeneity**: No mixing metric_types within a section for official_data/independent_benchmark claims (ensures clean benchmark tables)
- **claim_verified**: All claims must have `verified=true` post-review
- **content_concreteness**: Vague phrase density >10% (WARN); missing numbers/names in strict goal types (BLOCKER), others (WARN)
- **methodology_depth**: Methodology section <150 words or lacks Markdown table (WARN)
- **recommendation_structure**: tech_selection/competitive_comparison recommendation section lacks comparison table or "不推荐"/"not recommended" (WARN)
- **source_tier_balance**: Tier 1+2 source ratio <30% among referenced URLs (WARN)
- **claim_dedup**: Same claim text appears in multiple sections (WARN)

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

### lib/constants.py

```python
_ENGLISH_STOP_WORDS = frozenset({...})    # 27 words
_CHINESE_STOP_WORDS = frozenset({...})    # 60 characters
```

### gateway.py

```python
_VAGUE_PHRASES_ZH = frozenset({...})      # 12 Chinese vague phrases
_VAGUE_PHRASES_EN = frozenset({...})      # 11 English vague phrases
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
# Note: goal_type, depth, audience valid values are inline tuples in _check_scope_schema(), not named constants
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
           -> gateway.py (run_all, CheckResult)
           -> cli.py (_find_project_root)

gateway.py -> lib.constants (_CHINESE_STOP_WORDS)
           -> lib.exceptions (ArtifactError)
           -> lib.utils (normalize_url, read_json)

reporter.py -> lib.utils (normalize_url, read_json)

source_router.py -> (no internal imports)

constants.py -> (no internal imports)

exceptions.py -> (no internal imports)

utils.py -> exceptions (ArtifactError)
```

**External deps:** `argparse` (cli.py), `dataclasses` (gateway.py), `re` (gateway.py, proceed.py), `string` (proceed.py), `time` (utils.py), `urllib.parse` (utils.py)

---

## 10. Error Handling Patterns

1. **Custom exception hierarchy**: `InfoCollectorError` base → `GateFailureError` (gate failures) + `ArtifactError` (file I/O). Top-level `cli.py:main()` catches `InfoCollectorError` uniformly.
2. **Gate-based error handling**: Almost all errors are terminal via `sys.exit(1)`. No graceful degradation on BLOCKER.
3. **JSON parse errors**: `read_json()` raises `ArtifactError` on `json.JSONDecodeError` (no retry — content corruption is permanent) and on exhausted `OSError` retries.
4. **File operation retry**: `read_json()`/`write_json()` retry up to 3 times (default `retries=2, delay=0.5`) on `OSError` only. `json.JSONDecodeError` is not retried (ADR 0014).
5. **Defensive fallbacks**: `_count_sources()` and `_read_topic()` use `try/except Exception` to return safe defaults (0 or `"untitled"`).
6. **WARN vs BLOCKER**: Two-tier severity. `proceeds()` prints WARN to stderr but continues; BLOCKER stops the gate and returns error list.
7. **Minimal logging**: No `logging` module — just `print()` to stderr with `[WARN]` / `[BLOCKER]` prefixes.
8. **Stateless phase detection**: `detect_current_phase()` is pure — derives state from file existence, no mutable state.

---

## 11. Test Coverage Summary

| Module | Tests | Lines | Notable | Gaps |
|---|---|---|---|---|
| `cli.py` | 13 | 337 | All 5 commands tested; project root detection (3 cases); `InfoCollectorError` catch in main | `cmd_report` with incomplete scope.json; `cmd_gateway` only tests pass path |
| `gateway.py` | 74 | 1,316 | All 15 checks with edge cases; precision_inflation has 8 test cases; section_coverage tests 5 goal_types + 4 exploratory scenarios; content_concreteness with CJK | None |
| `content_concreteness` | 29 | 362 | `_count_words` CJK segmentation; vague phrase density; number/name presence; strict vs non-strict goal types | None |
| `exceptions` | 13 | 54 | Exception hierarchy; `GateFailureError`/`ArtifactError` attributes and messages | None |
| `gateway_import` | 1 | 37 | jieba not imported at module level | None |
| `proceed.py` | 36 | 516 | Phase detection (5 states); 5 gate transitions; Chinese search directions (CJK segmentation); per-direction min sources (3 depths); tier coverage; CJK coverage downgrade | `_generate_search_plan` output shape not tested |
| `reporter.py` | 42 | 654 | Reference map dedup; test conditions table (6 cases); i18n labels (zh/en/fallback); full pipeline; `report_language` priority; tier star labels | Empty analysis.json not tested |
| `source_router.py` | 17 | 160 | Route resolution; unknown goal_type fallback; min sources; depth priority; integration against real config.json | None |
| `utils.py` | 17 | 136 | URL normalization (8 cases); JSON read/write round-trip with retry; directory creation; ArtifactError on JSONDecodeError | Write permission errors not tested |
| **Total** | **242** | **3,576** | | |

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
5. **No template engine**: Reports built via string concatenation. Changing layout requires code changes.
6. **No content length validation**: 500-2000 word constraint per section is AI-self-discipline only.
7. **Silent exception swallowing**: `_count_sources()` and `_read_topic()` use `except Exception` fallbacks.
8. **Stale workfile accumulation**: If pipeline fails after producing analysis.json, earlier-phase artifacts remain. Only `clean` removes everything.
9. **CJK word count approximation**: `_count_words` uses segment-based counting (continuous CJK chars = 1 word) rather than proper segmentation. This is a deliberate tradeoff (ADR 0012) — less precise than jieba but avoids inflating word counts for Chinese content.
10. **proceed.py duplicates gateway logic**: `_check_url_traceability` in proceed.py mirrors `check_url_traceability` in gateway.py — the proceed version is a lightweight check for Gate 3, while the gateway version runs as part of the full 15-check suite in Gate 4.

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
| 0012 | Concreteness gate and CJK word counting | Add `check_content_concreteness` + `check_methodology_depth`; CJK segment-based word counting (not per-character) |
| 0013 | Source credibility and recommendation structure | Tier star labels in reports; `check_source_tier_balance` gate; `check_recommendation_structure` gate |
| 0014 | Custom exceptions and file operation retry | 3-level exception hierarchy; `read_json`/`write_json` retry on OSError only |
| 0015 | Centralized schema validation | TypedDict + `lib/schemas.py` with per-artifact validate functions; `ValidationError` dataclass |
| 0016 | Reset subcommand | `reset --phase <X>` CLI command to delete target phase and all subsequent artifacts |
