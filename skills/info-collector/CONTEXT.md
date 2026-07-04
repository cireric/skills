# Info-Collector

Structured research pipeline that produces a panoramic map with traceable sources — a starting point for deep research, not a citable authority.

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

**gate phase responsibility**:
Each pipeline gate checks only its own phase's concerns. `_gate_analysis` (analysis→review) checks analysis-phase BLOCKERs only (including `ref_marker_validity`, `claim_source_ref_coverage`), excluding `claim_verified` and `claim_source_relevance`. Also runs `source_verification_check` (WARN only, never BLOCKER). `_gate_review` (review→review, review→final) is advisory-only — `claim_verified` is now WARN level and `claim_source_relevance` has been replaced by `source_verification_check` in the analysis phase. The `verified` field is set deterministically by `source_verification_check()` code, not by the review subagent. `_gate_final` (final→cleanup) runs report checks; only BLOCKER-level failures block, WARN are advisory. See ADR 0025, ADR 0027, ADR 0028.
_Avoid_: gate scope, gate coverage, per-gate filtering

**report_checks**:
The deep module that validates the final report file. Interface: `run_report_checks(report_path) → list[CheckResult]`. Owns 10 checks: 3 BLOCKER (dangling refs F1, orphaned defs F2, front matter 9) + 7 WARN (refs visibility, table delimiters, heading levels, duplicate headings, unclosed code blocks, empty sections, overlong lines). See ADR 0026.
_Avoid_: report gateway, report validator, final gate checks

**BLOCKER report checks**:
The 3 report-level checks that block the final→cleanup transition: `report_dangling_refs` (in-text citation with no source definition), `report_orphaned_defs` (source definition with no in-text citation), `report_front_matter` (missing or malformed YAML front matter). Upgraded from WARN in ADR 0026.
_Avoid_: hard report checks, mandatory report checks

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
Boolean (default false) on a Claim. Mapped from `source_verification` by deterministic code in `source_verification_check()`: source_confirmed → true, source_indirect → true, source_absent → false. No longer set by review subagent. Retained for backward compatibility with gate logic.
_Avoid_: confirmed, validated

**source_verification**:
Three-level classification of a claim's source traceability: source_confirmed (number found in fetched_content or qualitative claim), source_absent (number not found in fetched_content), source_indirect (indirect source: Tier 3+ with non-official evidence, vendor source_type with exact/range precision, or indirect citation pattern in claim text where cited entity is not the source host). Computed deterministically by `source_verification_check()` in claim_validator.py, never by LLM. Indirect takes priority over confirmed/absent — even if a number is found, an indirect source deserves scrutiny.
_Avoid_: verification level, trust level

**source_metadata**:
Metadata about a claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type (vendor_benchmark, independent_test, production_case, survey). Rendered as a structured table in the report.
_Avoid_: test metadata, benchmark metadata

**review_status**:
Renamed from `quality`. Front matter field in the final report indicating the review outcome: passed, degraded, or unreviewed. The rename avoids implying that "passed" means all content is verified.
_Avoid_: quality, report quality

**verification_required**:
Front matter boolean field (always true) indicating the report contains claims that need source verification before citation. Tools/agents reading the report can use this flag to automatically identify reports requiring follow-up verification.
_Avoid_: requires verification, needs verification

**Test conditions**:
The testing environment behind benchmark claims. Includes hardware, OS, runtime version, and test date. Stored in claim's source_metadata, validated by gateway, rendered by reporter.py.
_Avoid_: test environment, test setup

**Methodology section**:
A required section (id="methodology") for quantitative goal_types. Describes: data sources and their test conditions, limitations of cross-source comparisons, date range of data collection.
_Avoid_: method section, approach section

**Reference numbering**:
[N] citation system in the final report. Global numbering across all sections, assigned by first-appearance order. In analysis.json content, sources are referenced via `{{ref:URL}}` markers (URL must match collected.json entry). reporter.py resolves markers to `[&#91;N&#93;](#refs)` links, owning the sole numbering authority. Hardcoded reference numbers in content (e.g., `[8]`) are prohibited. The References appendix uses a visible list format (e.g., `- [N] [Title](URL)`) with an explicit anchor (`<a id="refs"></a>`) for in-text link targets. Pure `[N]: URL` hidden definitions are not rendered by most Markdown renderers and must not be the sole format in the References section.
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

**SearchGate**:
The deep module that validates whether the search phase produced sufficient material to proceed to analysis. Owns topic_coverage, tier_coverage, fetched_content_depth, search_plan_compliance, and collected.json schema checks. Interface: `SearchGate(workdir, config).check() → list[CheckResult]`. Internal helpers (tokenization, stop-word filtering, per-direction counting) are private to its implementation.
_Avoid_: search validator, search quality checker, search gate checks

**ClaimValidator**:
The deep module that validates claim quality in analysis.json against collected.json. Owns claim_metadata, precision_inflation, claim_verified, source_metadata, metric_type_homogeneity, claim_dedup, claim_source_relevance, ref_marker_validity, claim_source_ref_coverage, and source_verification_check checks. Interface: `ClaimValidator(workdir, goal_type).check() → list[CheckResult]`. Reads analysis.json + collected.json once; shared helpers (number normalization, source text matching, data variance) are private to its implementation. See ADR 0027, ADR 0028.
_Avoid_: claim checker, claim gate, claim quality checker

**search plan**:
Auto-generated plan (`.workdir/search_plan.json`) produced after scope→search gate passes. Based on goal_type route and search_directions, generates specific search tasks per direction × tier × source language. AI executes the plan rather than free-form searching.
_Avoid_: search strategy, search outline

**project root**:
The directory containing `.git/`. Used as the base for resolving all relative paths (output_dir, WORKDIR). Auto-detected by walking up from CWD. Falls back to CWD if not in a git repository.
_Avoid_: repo root, workspace root

**Artifacts**:
- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions, english_title?
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content, covered_directions?}
- **analysis.json** — Phase 3a output: topic, goal_type, audience, sections (each with id, title, content, claims)
- **review_report.md** — Phase 3b output: subagent review findings
- **config.json** — Skill configuration: sources (4 tiers, each with language field), routes (10 goal_types), output_dir, default_report_language, default_depth, goal_type_defaults

## Relationships

- A **goal_type** determines required **source tiers** route and required sections in **analysis.json**
- A **Claim** belongs to a section in **analysis.json** and references URLs from **collected.json**
- **depth** drives minimum source count per search_direction; **audience** does not drive deterministic logic
- **covered_directions** overrides **topic_coverage** token matching when present
- **precision: exact** requires **evidence_type: official_data** or **independent_benchmark**
- A **gate phase responsibility** determines which checks run at each pipeline transition; BLOCKERs caught at earliest stage
- **BLOCKER report checks** block final→cleanup; the 7 WARN report checks are advisory
- **Reference numbering** uses `{{ref:URL}}` markers in analysis.json; claim.source_urls must be a subset of content `{{ref:URL}}` markers in the same section
- **ref_marker_validity** and **claim_source_ref_coverage** are analysis-phase BLOCKERs ensuring URL consistency between analysis.json content and collected.json
- Source **language** field in config.json drives search plan task splitting (per source, not per tier)
