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

**depth strategy**:
Per-section content depth strategy, derived implicitly from goal_type × section id (Phase 1), or declared explicitly via `depth_strategy` field (Phase 2). Four strategies: overview (breadth-first summary), deep_dive (key findings argued with 3+ sources), comparison (multi-dimensional comparison table), methodology (detailed methods and limitations). Different sections in the same report may use different depth strategies.
_Avoid_: depth level, content depth, analysis depth

**deep-dive anchor**:
A depth paragraph within a panoramic/exploratory section that argues one key finding with 3+ sources. Selection criteria: the finding has tension (multiple sources disagree), impact (changes reader's action/judgment), or mechanism (explains WHY/HOW, not just WHAT). Each section must have ≥ 2 deep-dive anchors.
_Avoid_: deep section, in-depth analysis, deep point

**report_language**:
Language for the final report output (e.g., "zh", "en"). Stored in scope.json, falls back to config.json `default_report_language`, then "en". Drives AI writing language and reporter.py fixed label i18n.
_Avoid_: output language

**gate phase responsibility**:
Each pipeline gate checks only its own phase's concerns. `_gate_analysis` (analysis→review) checks analysis-phase BLOCKERs only (including `ref_marker_validity`, `claim_source_ref_coverage`, `entity_number_conflict`), plus `source_verification_check` (INFO level, never BLOCKER) which writes back `source_verification` and `verified` on claims deterministically. `_gate_review` (review→review, review→final) is advisory-only — it runs all checks but never blocks. The `verified` field is set deterministically by `source_verification_check()` code, not by the review subagent. `_gate_final` (final→cleanup) runs report checks; only BLOCKER-level failures block, WARN are advisory. See ADR 0025, ADR 0027, ADR 0028.
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

**false depth**:
Using analytical language to wrap listed content and create an illusion of depth. Three patterns: pseudo-synthesis (causal language without causal evidence), name-as-analysis (mentioning an entity + one-sentence description without evaluation), action-platitude ("readers need to understand X" without actionable guidance). Pseudo-synthesis is hard-prohibited; name-as-analysis requires ≥ 2 analytical entries per section; action-platitude is prohibited.
_Avoid_: shallow analysis, fake analysis

**Claim**:
A statement in analysis.json with structured metadata: text, source_urls, evidence_type, confidence, precision, metric_type, source_verification, verified, source_metadata.
_Avoid_: finding, assertion

**evidence_type**:
Classification of a claim's evidence: official_data, independent_benchmark, third_party_estimate, qualitative_trend, expert_opinion.
_Avoid_: evidence category

**confidence**:
Claim reliability level: high, medium, low.
_Avoid_: certainty, reliability

**precision**:
Claim specificity level: exact, range, qualitative. Precision rules: `exact` requires `official_data` or `independent_benchmark`. `third_party_estimate`, `qualitative_trend`, and `expert_opinion` must not use `exact`.
_Avoid_: granularity, specificity

**metric_type**:
What kind of measurement a claim represents: swe_bench_verified, swe_bench_pro, terminal_bench, pr_merge_rate, refactoring_safety, custom. Used by gateway to prevent mixing different metrics in the same table.
_Avoid_: measurement type, benchmark type

**verified**:
Boolean (default false) on a Claim. Mapped from `source_verification` by deterministic code in `source_verification_check()`: source_confirmed → true, source_indirect → true, source_absent → false. No longer set by review subagent. Retained as a convenience boolean derived from source_verification. No gate logic reads this field; use source_verification for gate-level decisions.
_Avoid_: confirmed, validated

**source_verification**:
Three-level classification of a claim's source traceability: source_confirmed (number found in fetched_content or qualitative claim), source_absent (number not found in fetched_content), source_indirect (indirect source: Tier 3+ source regardless of evidence_type (low-tier sources claiming official data are inherently suspect), vendor source_type with exact/range precision, or indirect citation pattern in claim text where cited entity is not the source host). Computed deterministically by `source_verification_check()` in claim_validator.py, never by LLM. Indirect takes priority over confirmed/absent — even if a number is found, an indirect source deserves scrutiny.
_Avoid_: verification level, trust level

**synthesis guard**:
The standard for genuine synthesis: causal direction must be explicitly stated (A→B), and each step in the causal chain must have at least one source supporting it. When this standard cannot be met, the writer must present the observations as "co-occurring phenomena" rather than synthesis. Applies to panoramic overview sections and all synthesis paragraphs.
_Avoid_: synthesis rule, causation requirement

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
The deep module that validates whether the search phase produced sufficient material to proceed to analysis. Owns collected_exists, collected_schema, min_sources, topic_coverage, tier_coverage, fetched_content_depth, search_plan_compliance, domain_concentration, and tier_task_completion checks. Interface: `SearchGate(workdir, config).check() → list[CheckResult]`. Internal helpers (tokenization, stop-word filtering, per-direction counting) are private to its implementation.
_Avoid_: search validator, search quality checker, search gate checks

**section plan**:
Phase 3a Step 1 output, extended from `{id, title}` to `{id, title, deep_dive_topics: [{topic, source_hints}], depth_strategy}`. The orchestrator reads scope.json + collected.json and plans each section's depth strategy, deep-dive anchor topics, and suggested sources. source_hints are advisory — subagents are not limited to these sources. depth_strategy determines per-section content organization rules (overview, deep_dive, comparison, methodology).
_Avoid_: section outline, section schema

**ClaimValidator**:
The deep module that validates claim quality in analysis.json against collected.json. Owns claim_metadata, precision_inflation, source_metadata, metric_type_homogeneity, claim_dedup, entity_number_conflict, ref_marker_validity, claim_source_ref_coverage, and source_verification_check checks. Interface: `ClaimValidator(workdir, goal_type).check() → list[CheckResult]`. Reads analysis.json + collected.json once; shared helpers (number normalization, source text matching, data variance) are private to its implementation. See ADR 0027, ADR 0028.
_Avoid_: claim checker, claim gate, claim quality checker

**source fidelity**:
`.workdir/sources/` 目录中原文文件的存在率和非空率。替代 `fetched_content_depth` 作为 search→analysis gate 的 BLOCKER 检查。阈值：如果 >30% 的 collected entry 没有对应的原文文件（文件不存在或为空且未标记 `fetch_failed: true`），则 BLOCKER。`fetch_failed: true` 的 entry 豁免检查，但豁免率本身受上限约束（如 >50% 豁免则 WARN）。
_Avoid_: fetch quality, content depth, fetch completeness

**source_file**:
collected.json entry 中新增的字段，值为 `.workdir/sources/` 下对应原文文件的相对路径（如 `"sources/abc123.md"`）。与 `url_hash` 一一对应。subagent 通过此字段定位原文文件。
_Avoid_: source path, content file

**FetchStrategy**:
per-source 的 fetch 策略接口，负责 URL 重写和工具 fallback 链。两种实现：`url_rewrite` 声明式规则（config.json，覆盖 80% 场景）和 `fetch_strategies/*.py` 代码式特例（覆盖 20%）。解析优先级：代码 strategy > config url_rewrite > DefaultStrategy（不重写，tools=["webfetch"]）。
_Avoid_: fetch config, fetch handler, fetch adapter

**url_rewrite**:
config.json source 定义中的声明式 URL 重写规则。格式：`[{"match": "regex_pattern", "replace": "replacement_template"}]`。由通用 regex rewrite engine 执行，代码零 source 特化。
_Avoid_: url transform, url mapping, url conversion

**adaptive retry**:
按 source tier 分级的 fetch 重试策略。Tier 1-2 每工具重试 2 次，Tier 3-4 每工具重试 1 次。单条 URL 全局超时 60 秒。所有工具穷尽后标记 `fetch_failed: true`。
_Avoid_: retry policy, fetch retry, retry strategy

**search plan**:
Auto-generated plan (`.workdir/search_plan.json`) produced after scope→search gate passes. Based on goal_type route and search_directions, generates specific search tasks per direction × tier × source language. AI executes the plan rather than free-form searching.
_Avoid_: search strategy, search outline

**project root**:
The directory containing `.git/`. Used as the base for resolving all relative paths (output_dir, WORKDIR). Auto-detected by walking up from CWD. Falls back to CWD if not in a git repository.
_Avoid_: repo root, workspace root

**Artifacts**:
- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions, english_title?
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content, covered_directions?, vendor_affiliation?}
- **analysis.json** — Phase 3a output: topic, goal_type, sections (each with id, title, content, depth_strategy, key_insights, tensions, claims)
- **review_report.md** — Phase 3b output: subagent review findings
- **config.json** — Skill configuration: sources (4 tiers, each with language field), routes (10 goal_types), output_dir, default_report_language, default_depth, goal_type_defaults

## Relationships

- A **goal_type** determines required **source tiers** route, required sections in **analysis.json**, and **depth strategy** for each section via implicit mapping (goal_type × section id → strategy)
- A **Claim** belongs to a section in **analysis.json** and references URLs from **collected.json**
- **depth** drives minimum source count per search_direction; **depth strategy** drives per-section content organization; these are independent concerns
- **audience** does not drive deterministic logic
- **covered_directions** overrides **topic_coverage** token matching when present
- **precision: exact** requires **evidence_type: official_data** or **independent_benchmark**
- A **gate phase responsibility** determines which checks run at each pipeline transition; BLOCKERs caught at earliest stage
- **BLOCKER report checks** block final→cleanup; the 7 WARN report checks are advisory
- **Reference numbering** uses `{{ref:URL}}` markers in analysis.json; claim.source_urls must be a subset of content `{{ref:URL}}` markers in the same section
- **ref_marker_validity** and **claim_source_ref_coverage** are analysis-phase BLOCKERs ensuring URL consistency between analysis.json content and collected.json
- Source **language** field in config.json drives search plan task splitting (per source, not per tier)
- **deep-dive anchor** selection is performed by the orchestrator in **section plan**; each panoramic/exploratory section must have ≥ 2 anchors
- **false depth** is prohibited by **synthesis guard** and writing-guide content rules
- **source fidelity** replaces **fetched_content_depth**: gate now checks `.workdir/sources/` file existence rather than `fetched_content` field character count
- **fetched_content** field retains a 200-char index role; no longer a gate check target
- **FetchStrategy** determines per-source URL rewriting and tool fallback chain; config.json `url_rewrite` rules cover 80%, `fetch_strategies/*.py` cover remaining 20%
- **fetch router** resolves `get_fetch_strategy(source_config) → FetchStrategy`; priority: code strategy > config url_rewrite > DefaultStrategy
- **adaptive retry** by Tier: Tier 1-2 retry twice per tool, Tier 3-4 retry once; 60s global timeout per URL
- **source_file** in collected.json points to `.workdir/sources/{url_hash}.md`; subagents read original text via Read tool
- subagent prompt injects first 500 chars of each source + file paths; Numeric Claim Source Rule updated: exact numbers must be verified in original text files, not just injected summaries

## Route Decisions (ADR 0031)

Grilling session decisions on source routing. Rationale for each change from original config:

| route | original path | revised path | rationale |
|---|---|---|---|
| exploratory | [4,2] | [4,3,2] | +Tier 3 for industry trend perspective alongside community signals |
| tech_selection | [2,1] | [2,3,4,1] | docs→industry→community→academic; industry shows adoption trends, community reveals real-world pain points before academic validation |
| feasibility_assessment | [2,1] | [2,1,3] | docs→academic feasibility→industry cases; industry cases validate practical viability |
| competitive_comparison | [2,3,4,1] | [2,1,3,4] | academic benchmark data before community opinions; benchmarks are objective ground truth |
| background_check | [3,4,2,1] | [3,2,1,4] | official docs before community; background research needs authoritative sources first |
| market_analysis | [3,1,2] | [3,4,1,2] | +Tier 4 for early trend signals; community behavior (Reddit/HN/Zhihu) is the earliest market indicator |
| academic_research | [1] | [1], optional_tiers=[2] | main line stays Tier 1; optional Tier 2 for tech docs when reproducing experiments |

Unchanged routes: panoramic_understanding [4,3,1] optional_tiers=[2], fact_check [1,2,4], other [3,2,1].

New Tier 1 sources added for Chinese academic coverage:
- **Wanfang** (wanfangdata.com.cn): Chinese academic database, same Tier 1 as CNKI
- **CQVIP** (cqvip.com): Chinese academic database (维普), same Tier 1 as CNKI
- 国标 (gb688.cn) considered but excluded due to connection timeout issues
- Both Wanfang and CQVIP share CNKI's abstract-only access limitation; source_verification + precision mechanism handles "abstract has it, full text doesn't" naturally
