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
- **draft** — Render analysis.json as readable Markdown for review. Produces `draft/report.md`.
- **review** — Optional independent subagent review of draft + analysis.json. Produces `review_report.md`.
- **final** — Generate final report from analysis.json via reporter.py.
- **cleanup** — Remove intermediate workdir files.

### Gates

Quality checks at phase transitions. Each gate returns BLOCKER (must fix) or WARN (noted but not blocking).

- **scope→search**: validates scope.json schema (required fields + enum values)
- **search→analysis**: topic_coverage (BLOCKER) + min_sources (WARN)
- **draft→review**: analysis.json schema + draft existence
- **review→final**: 7 gateway checks (artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, claim_metadata)
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
| exploratory | exploratory | overview, details |
| panoramic_understanding | exploratory | overview, details |
| background_check | exploratory | overview, details |
| other | exploratory | overview, details |

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

Search depth (quick, standard, deep). A **hint field** — recorded in scope.json, influences AI behavior, but does not drive any deterministic code logic beyond config defaults.

### report_language

Language for the final report output (e.g., "zh", "en"). Stored in scope.json (per-research decision), falls back to config.json `default_report_language`, then "en". Drives AI writing language and reporter.py fixed label i18n (Sources/数据来源, References/参考文献, etc.).

### hint field

A scope.json field that informs AI behavior without driving deterministic code logic. Currently: audience, depth. Contrast with goal_type, which drives 5 code-level behavior differences.

### Claim

A statement in analysis.json with structured metadata:

- **text** — The claim statement
- **source_urls** — URLs supporting the claim (must exist in collected.json)
- **evidence_type** — official_data, independent_benchmark, third_party_estimate, qualitative_trend, expert_opinion
- **confidence** — high, medium, low
- **precision** — exact, range, qualitative
- **source_metadata** — Metadata about the claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type (vendor_benchmark, independent_test, production_case, survey)

Precision rules: `precision: exact` requires `evidence_type: official_data` or `independent_benchmark`. `third_party_estimate` and `qualitative_trend` must not use `precision: exact`.

### Test conditions

The testing environment behind benchmark claims. Rendered as a structured table in the report. Includes hardware, OS, runtime version, and test date. Stored in claim's source_metadata, validated by gateway, rendered by reporter.py.

### Draft

A readable Markdown rendering of analysis.json, produced for review purposes. The draft is NOT the final report. Review fixes target analysis.json (not draft). The final report is rendered by reporter.py from the reviewed analysis.json. AI writes full Markdown narrative (tables, emphasis, transitions) in analysis.json's sections[].content field.

### Methodology section

A required section (id="methodology") for quantitative goal_types. Written by AI in analysis.json sections. Content describes: data sources and their test conditions, limitations of cross-source comparisons, date range of data collection.

### Reference numbering

[N] citation system in the final report. Global numbering across all sections, assigned by first-appearance order. Maps to a References appendix at report end: `[N]: URL — title`. Titles looked up from collected.json.

### Setup wizard

First-run configuration wizard. AI-conversational (no new Python code). Triggers when config.json does not exist. Collects: output_dir, default_report_language, default_depth, source customization. User can re-invoke at any time.

### Artifacts

- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content}
- **analysis.json** — Phase 3a output: topic, goal_type, audience, sections (each with id, title, content, claims)
- **draft/report.md** — Phase 3b output: readable rendering of analysis.json
- **review_report.md** — Phase 3c output: subagent review findings
- **config.json** — Skill configuration: sources (4 tiers), routes (10 goal_types), output_dir, default_report_language, default_depth, goal_type_defaults
