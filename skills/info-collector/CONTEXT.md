# Info-Collector

Structured research pipeline that collects, organizes, and synthesizes information from web sources into a quality-gated report.

## Language

**goal_type**:
Research objective type. Drives source routing, required sections, and metadata check intensity. 10 valid values: tech_selection, competitive_comparison, feasibility_assessment, market_analysis, academic_research (quantitative); fact_check (verification); exploratory, panoramic_understanding, background_check, other (exploratory).
_Avoid_: research type, objective type

**quantitative goal_type**:
The 5 goal types that require methodology sections and claim metadata validation (evidence_type/confidence/precision). Defined in code as `_QUANTITATIVE_GOAL_TYPES`.
_Avoid_: data-driven goal type

**source tiers**:
Four tiers of information sources, ordered by authority: (1) Academic/Standards, (2) Documentation/Open Source, (3) Industry/Expert Blogs, (4) Community/UGC. Each goal_type maps to a route (entry_tier + path) that determines which tiers to search and in what order.
_Avoid_: source levels, source categories

**audience**:
Report reader type (CTO, engineer, researcher, general). A hint field — recorded in scope.json, passed to AI prompts and review subagent, but does not drive any deterministic code logic.
_Avoid_: reader, target reader

**hint field**:
A scope.json field that informs AI behavior without driving deterministic code logic. Currently: audience only. Contrast with goal_type (drives 5+ code-level behavior differences) and depth (drives per-direction source counts).
_Avoid_: advisory field

**depth**:
Search depth (quick, standard, deep). A behavior-driving field — drives per-direction minimum source count in search gate (quick=1, standard=3, deep=5) and search plan generation.
_Avoid_: research level, thoroughness

**report_language**:
Language for the final report output (e.g., "zh", "en"). Stored in scope.json, falls back to config.json `default_report_language`, then "en". Drives AI writing language and reporter.py fixed label i18n.
_Avoid_: output language

**english_title**:
An optional field in scope.json providing an English title for the research topic. Required (BLOCKER) when `topic` contains non-ASCII characters. Used as the report filename base, ensuring filenames are ASCII-only.
_Avoid_: english name, translated title

**Claim**:
A statement in analysis.json with structured metadata: text, source_urls, evidence_type, confidence, precision, metric_type, verified, source_metadata.
_Avoid_: finding, assertion

**evidence_type**:
Classification of a claim's evidence: official_data, independent_benchmark, third_party_estimate, qualitative_trend, expert_opinion.
_Avoid_: evidence category

**confidence**:
Claim reliability level: high, medium, low.
_Avoid_: certainty, reliability

**precision**:
Claim specificity level: exact, range, qualitative. Precision rules: `exact` requires `official_data` or `independent_benchmark`. `third_party_estimate` and `qualitative_trend` must not use `exact`.
_Avoid_: granularity, specificity

**metric_type**:
What kind of measurement a claim represents: swe_bench_verified, swe_bench_pro, terminal_bench, pr_merge_rate, refactoring_safety, custom. Used by gateway to prevent mixing different metrics in the same table.
_Avoid_: measurement type, benchmark type

**verified**:
Boolean (default false) on a Claim. Set to true by review subagent after confirming source_url content actually supports the claim. Required for review→final gate.
_Avoid_: confirmed, validated

**source_metadata**:
Metadata about a claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type (vendor_benchmark, independent_test, production_case, survey). Rendered as a structured table in the report.
_Avoid_: test metadata, benchmark metadata

**Test conditions**:
The testing environment behind benchmark claims. Includes hardware, OS, runtime version, and test date. Stored in claim's source_metadata, validated by gateway, rendered by reporter.py.
_Avoid_: test environment, test setup

**Methodology section**:
A required section (id="methodology") for quantitative goal_types. Describes: data sources and their test conditions, limitations of cross-source comparisons, date range of data collection.
_Avoid_: method section, approach section

**Reference numbering**:
[N] citation system in the final report. Global numbering across all sections, assigned by first-appearance order. Maps to a References appendix at report end: `[N]: URL — title`.
_Avoid_: citation numbering, footnote numbering

**topic_coverage**:
The search→analysis gate check that verifies collected sources cover all search_directions. Uses inline CJK segmentation: each direction is split into tokens, filtered by stop-word sets. A direction is "covered" when a threshold of its tokens appear in collected.json entries' title + snippet, OR when the entry's `covered_directions` field explicitly lists that direction.
_Avoid_: direction coverage, search coverage

**covered_directions**:
An optional field in collected.json entries where the agent declares which search_directions this source covers. Subset of scope.json's search_directions, max 3 per entry. Overrides token-based direction assignment when present.
_Avoid_: matched directions, direction tags

**tier_coverage**:
search→analysis gate check (WARN level) that verifies collected.json contains at least one source from each tier in the goal_type's route.
_Avoid_: source diversity, tier balance

**search plan**:
Auto-generated plan (`.workdir/search_plan.json`) produced after scope→search gate passes. Based on goal_type route and search_directions, generates specific search tasks per direction × tier. AI executes the plan rather than free-form searching.
_Avoid_: search strategy, search outline

**project root**:
The directory containing `.git/`. Used as the base for resolving all relative paths (output_dir, WORKDIR). Auto-detected by walking up from CWD. Falls back to CWD if not in a git repository.
_Avoid_: repo root, workspace root

**Artifacts**:
- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions, english_title?
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content, covered_directions?}
- **analysis.json** — Phase 3a output: topic, goal_type, audience, sections (each with id, title, content, claims)
- **review_report.md** — Phase 3b output: subagent review findings
- **config.json** — Skill configuration: sources (4 tiers), routes (10 goal_types), output_dir, default_report_language, default_depth, goal_type_defaults

## Relationships

- A **goal_type** determines required **source tiers** route and required sections in **analysis.json**
- A **Claim** belongs to a section in **analysis.json** and references URLs from **collected.json**
- **depth** drives minimum source count per search_direction; **audience** does not drive deterministic logic
- **covered_directions** overrides **topic_coverage** token matching when present
- **precision: exact** requires **evidence_type: official_data** or **independent_benchmark**
