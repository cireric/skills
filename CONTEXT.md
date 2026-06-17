# CONTEXT.md — Domain Glossary

This repo is a collection of agent skills. Each skill is an independent directory under `skills/` with its own code, config, tests, and SKILL.md workflow definition.

## Skills

- **info-collector** — Collect, organize, and summarize structured information from web sources. Triggered by research/intelligence-gathering requests.
- **reading-grill** — Socratic comprehension quiz after reading. Markdown-only, no code.
- **book-grill** — Post-reading deep reflection with type-adaptive questioning.

## Info-Collector Domain

### Research phases

The research pipeline has ordered phases. Each phase transition triggers a **gate** (quality check) via the `proceed` command.

- **scope** — Define research scope: topic, goal_type, depth, audience, search_directions, report_language. Produces `scope.json`.
- **search** — Search and collect web sources. Produces `collected.json`.
- **analysis** — Synthesize findings into claims with metadata. Produces `analysis.json`.
- **review** — Optional independent subagent review of analysis.json. Produces `review_report.md`.
- **final** — Generate final report from analysis.json via reporter.py.
- **cleanup** — Remove intermediate workdir files.

### Gates

Quality checks at phase transitions. Each gate returns BLOCKER (must fix) or WARN (noted but not blocking).

- **scope→search**: validates scope.json schema (required fields + enum values)
- **search→analysis**: topic_coverage (BLOCKER, token-level matching) + tier_coverage (WARN) + per_direction_min_sources (WARN, driven by depth) + min_sources (WARN)
- **analysis→review**: analysis.json schema + url_traceability (BLOCKER)
- **review→final**: 15 gateway checks (artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, metric_type_homogeneity, claim_metadata, claim_verified, source_metadata, content_concreteness, methodology_depth, recommendation_structure, source_tier_balance, claim_dedup)
- **final→cleanup**: no structural checks

### goal_type

Research objective type. Drives source routing, required sections, and metadata check intensity. 10 valid values:

| goal_type | Category | Required sections |
|-----------|----------|-------------------|
| tech_selection | quantitative | overview, comparison, recommendation, methodology |
| competitive_comparison | quantitative | overview, comparison, positioning, methodology |
| feasibility_assessment | quantitative | overview, analysis, conclusion, methodology |
| market_analysis | quantitative | overview, data, trends, conclusion, methodology |
| academic_research | quantitative | abstract, findings, references, methodology |
| fact_check | verification | claims, evidence, conclusion |
| exploratory | exploratory | overview + ≥1 other (any id) |
| panoramic_understanding | exploratory | overview + ≥1 other (any id) |
| background_check | exploratory | overview + ≥1 other (any id) |
| other | exploratory | overview + ≥1 other (any id) |

**quantitative goal_type** — The 5 goal types that require methodology sections and claim metadata validation (evidence_type/confidence/precision). Defined in code as `_QUANTITATIVE_GOAL_TYPES`.

### Source tiers

Four tiers of information sources, ordered by authority:

1. **Academic / Standards** — arXiv, Google Scholar, PubMed, CNKI, W3C, IETF, ISO
2. **Documentation / Open Source** — GitHub, MDN, Wikipedia
3. **Industry / Expert Blogs** — Medium, IEEE Spectrum, MIT Tech Review
4. **Community / UGC** — Reddit, Stack Overflow, Zhihu

Each goal_type maps to a **route** (entry_tier + path) that determines which tiers to search and in what order.

### audience

Report reader type (CTO, engineer, researcher, general). A **hint field** — recorded in scope.json, passed to AI prompts and review subagent, but does not drive any deterministic code logic. The only code-level impact is in REVIEW_PROMPT.md's audience alignment check.

### depth

Search depth (quick, standard, deep). A **behavior-driving field** — drives per-direction minimum source count in search gate (quick=1, standard=3, deep=5) and search plan generation. Contrasts with `audience`, which remains a hint field.

### report_language

Language for the final report output (e.g., "zh", "en"). Stored in scope.json (per-research decision), falls back to config.json `default_report_language`, then "en". Drives AI writing language and reporter.py fixed label i18n (Sources/数据来源, References/参考文献, etc.).

### hint field

A scope.json field that informs AI behavior without driving deterministic code logic. Currently: audience only. Contrast with goal_type (drives 5+ code-level behavior differences) and depth (drives per-direction source counts).

### Claim

A statement in analysis.json with structured metadata:

- **text** — The claim statement
- **source_urls** — URLs supporting the claim (must exist in collected.json)
- **evidence_type** — official_data, independent_benchmark, third_party_estimate, qualitative_trend, expert_opinion
- **confidence** — high, medium, low
- **precision** — exact, range, qualitative
- **metric_type** — What kind of measurement this claim represents: swe_bench_verified, swe_bench_pro, terminal_bench, pr_merge_rate, refactoring_safety, custom. Used by gateway to prevent mixing different metrics in the same table.
- **verified** — Boolean (default false). Set to true by review subagent after confirming source_url content actually supports the claim. Required for review→final gate.
- **source_metadata** — Metadata about the claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type (vendor_benchmark, independent_test, production_case, survey)

Precision rules: `precision: exact` requires `evidence_type: official_data` or `independent_benchmark`. `third_party_estimate` and `qualitative_trend` must not use `precision: exact`. Conflicting metric values with `precision: exact` must be changed to `precision: range` with explanation.

### Test conditions

The testing environment behind benchmark claims. Rendered as a structured table in the report. Includes hardware, OS, runtime version, and test date. Stored in claim's source_metadata, validated by gateway, rendered by reporter.py.

### Methodology section

A required section (id="methodology") for quantitative goal_types. Written by AI in analysis.json sections. Content describes: data sources and their test conditions, limitations of cross-source comparisons, date range of data collection.

### Reference numbering

[N] citation system in the final report. Global numbering across all sections, assigned by first-appearance order. Maps to a References appendix at report end: `[N]: URL — title`. Titles looked up from collected.json.

### Setup wizard

First-run configuration wizard. AI-conversational (no new Python code). Triggers when config.json does not exist. Collects: output_dir, default_report_language, default_depth, source customization. User can re-invoke at any time.

### topic_coverage

The search→analysis gate check that verifies collected sources cover all search_directions. Uses jieba tokenization: each direction is split into tokens, and a direction is considered "covered" when all its tokens appear in collected.json entries' title + snippet. This allows natural language directions in any language (Chinese, English, mixed) without requiring specific keyword formatting.

### project root

The directory containing `.git/`. Used as the base for resolving all relative paths (output_dir, WORKDIR). Auto-detected by walking up from CWD to find the first `.git`-containing directory. Falls back to CWD if not in a git repository. Defined in code as `_find_project_root()`.

### search plan

Auto-generated search plan (`.workdir/search_plan.json`) produced after scope→search gate passes. Based on goal_type route and search_directions, generates specific search tasks per direction × tier with English/Chinese keyword conversion and site: filters. AI executes the plan rather than free-form searching. Ensures systematic coverage and source tier diversity.

### tier_coverage

search→analysis gate check (WARN level) that verifies collected.json contains at least one source from each tier in the goal_type's route. For example, panoramic_understanding's route [4, 2, 1] requires sources from Tier 4 (Community), Tier 2 (Documentation), and Tier 1 (Academic).

### Artifacts

- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content}
- **analysis.json** — Phase 3a output: topic, goal_type, audience, sections (each with id, title, content, claims)
- **review_report.md** — Phase 3b output: subagent review findings
- **config.json** — Skill configuration: sources (4 tiers), routes (10 goal_types), output_dir, default_report_language, default_report_language, default_depth, goal_type_defaults
