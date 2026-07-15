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
A scope.json field that informs AI behavior without driving deterministic code logic. Currently: audience, decision_questions. Contrast with goal_type (drives 5+ code-level behavior differences) and depth (drives per-direction source counts).
_Avoid_: advisory field

**depth**:
Search depth (quick, standard, deep). A behavior-driving field — drives per-direction minimum source count in search gate (quick=1, standard=3, deep=5) and search plan generation.
_Avoid_: research level, thoroughness

**summary**:
The text content field in analysis.json sub-structures (key_insights, tensions, claims). Replaces the heterogeneous `text`/`description` fields with a single unified name. A summary is a concise statement — of an insight, a tension, or a claim.
_Avoid_: text, description, content (for sub-structure fields)

**sources**:
The source reference list field in analysis.json sub-structures (key_insights, tensions, claims). Replaces the heterogeneous `source_urls`/`sources` naming with a single unified name. Each entry is a URL string matching a collected.json entry.
_Avoid_: source_urls, source_refs, references (for sub-structure field name)

**decision_questions**:
Optional hint field in scope.json: list of 2-3 questions the research should help answer (e.g., "Should we adopt domestic RISC-V for MCU scenarios?"). Helps Phase 1 focus research intent. Does not drive deterministic code logic.
_Avoid_: research questions, key questions

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
Each pipeline gate checks only its own phase's concerns. `_gate_analysis` (analysis→review) checks analysis-phase BLOCKERs only (including `ref_marker_validity`, `claim_source_ref_coverage`, `entity_number_conflict`), plus `source_verification_check` (INFO level, never BLOCKER) which writes back `source_verification` and `verified` on claims deterministically. `_gate_review` (review→review self-loop: requires `review_report.md` to exist; review→final: runs advisory gateway checks + repair loop re-merge + blocks on `review_report_exists` BLOCKER + repair loop status). Report checks run as CLI post-step in `cmd_report`, not as a pipeline gate (ADR 0056). See ADR 0025, ADR 0027, ADR 0028, ADR 0056.
_Avoid_: gate scope, gate coverage, per-gate filtering

**report_checks**:
The deep module that validates the final report file. Interface: `run_report_checks(report_path) → list[CheckResult]`. Owns 10 checks: 3 BLOCKER (dangling refs F1, orphaned defs F2, front matter 9) + 7 WARN (refs visibility, table delimiters, heading levels, duplicate headings, unclosed code blocks, empty sections, overlong lines). Called by `cmd_report` as a post-generation step; BLOCKER-level failures prevent report from being saved (ADR 0056). See ADR 0026.
_Avoid_: report gateway, report validator, final gate checks

**BLOCKER report checks**:
The 3 report-level checks that block report saving in `cmd_report`: `report_dangling_refs` (in-text citation with no source definition), `report_orphaned_defs` (source definition with no in-text citation), `report_front_matter` (missing or malformed YAML front matter). Upgraded from WARN in ADR 0026.
_Avoid_: hard report checks, mandatory report checks

**review_report_exists**:
Review gate BLOCKER check that verifies `review_report.md` exists and is non-empty. Review is mandatory (ADR 0028, minimum: degraded inline review). Missing or empty review_report.md blocks the review→final transition. Checked by `_gate_review`, not by `_gate_final`.
_Avoid_: review check, review gate check

**english_title**:
An optional field in scope.json providing an English title for the research topic. Required (BLOCKER) when `topic` contains non-ASCII characters. Used as the report filename base, ensuring filenames are ASCII-only.
_Avoid_: english name, translated title

**false depth**:
Using analytical language to wrap listed content and create an illusion of depth. Three patterns: pseudo-synthesis (causal language without causal evidence), name-as-analysis (mentioning an entity + one-sentence description without evaluation), action-platitude ("readers need to understand X" without actionable guidance). Pseudo-synthesis is hard-prohibited; name-as-analysis requires ≥ 2 analytical entries per section; action-platitude is prohibited.
_Avoid_: shallow analysis, fake analysis

**Claim**:
A statement in analysis.json with structured metadata: summary, sources, evidence_type, confidence, precision, metric_type, source_verification, verified, source_metadata.
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
Metadata about a claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type (official_report, independent_test, production_case, survey, vendor_benchmark, analyst_forecast, vendor_survey, vendor_blog). Rendered as a structured table in the report.
_Avoid_: test metadata, benchmark metadata

**source_type**:
Field inside a claim's `source_metadata` describing **benchmark/test provenance**, NOT the authority of the publishing venue. Eight valid values: official_report, independent_test, production_case, survey, vendor_benchmark, analyst_forecast, vendor_survey, vendor_blog. `vendor_benchmark` means the number was produced by the vendor's own benchmark (inherently suspect). The verifier only flips a `vendor_benchmark` + `exact`/`range` claim to indirect when the source venue is itself non-authoritative (tier ≥ 3); an authoritative venue (tier ≤ 2, e.g. an arXiv paper) mislabeled as `vendor_benchmark` is NOT flipped. Invalid values are auto-fixed via `_SOURCE_TYPE_ALIASES` (e.g. `independent_benchmark` → `independent_test`) or downgraded to `survey` (ADR 0058).
_Avoid_: conflating source_type with venue authority; tagging academic papers as vendor_benchmark

**single_source_ratio**:
Axis-B multi-source corroboration metric: ratio of claims whose `sources` has fewer than `_MIN_SOURCES` (2). WARN threshold is depth-dynamic via `single_source_ratio_threshold(depth)`: quick → not checked, standard → >70%, deep → >50%. Surfaces when a report relies on single-source claims; repair_hints suggest Tier1–3 sources from config.json toolbook.
_Avoid_: single-source rate, source diversity ratio

**Chinese community source**:
Tier 4 UGC sources in Chinese: Zhihu (zhihu.com) and Weibo (weibo.com). Both carry `language: "zh"` and rely on exa (exa_web_fetch_exa / exa_web_search_exa) as the primary fetch path because autonomous fetch (webfetch/playwright) is unreachable in the no-egress environment. Weibo is best-effort (login-wall / anti-bot may yield fetch_failed); Zhihu is the dependable Chinese-community voice.
_Avoid_: Chinese source, CN community source

**review_status**:
Renamed from `quality`. Front matter field in the final report indicating the review outcome: `passed` or `degraded`. The `unreviewed` option has been removed — review is mandatory, minimum level is degraded (inline review by the same agent). The rename avoids implying that "passed" means all content is verified.
_Avoid_: quality, report quality, unreviewed

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
Removed (ADR 0042). Previously checked that collected sources cover all search_directions. Removed because Phase 1 directions cannot anticipate topics discovered during search; locking directions narrows search horizon. Directions discussed during Phase 1 interview remain in conversation context as implicit guidance, but are not enforced by gate.
_Avoid_: direction coverage, search coverage

**covered_directions**:
Removed (ADR 0042). Previously an optional field in collected.json entries declaring which search_directions a source covers. No longer needed because search_directions are not gate-enforced; directions exist only as Phase 1 interview context.
_Avoid_: matched directions, direction tags

**tier_coverage**:
search→analysis gate check that verifies collected.json contains at least one source from each tier in the goal_type's route. Required tiers missing → BLOCKER (search_gate.py:116, ADR 0042); optional tiers missing → INFO (search_gate.py:122-127). panoramic_understanding's Tier 2 is now required (ADR 0049).

**direction (collected field)**:
ADR 0052 field on each `collected.json` entry: the `scope.search_directions` value the source serves, or `"other"` for discoveries outside declared directions. Agent-assigned during free search (agent knows its search intent). Enables the user-declared breadth contract without narrowing horizon (ADR 0042 compatible).
_Avoid_: facet, topic, coverage tag

**direction_tagging**:
SearchGate BLOCKER (ADR 0052) that fires only when `scope.search_directions` is non-empty: every collected entry must carry a non-empty `direction`. Enforces the breadth contract at the search→analysis gate.
_Avoid_: direction_coverage, facet tagging

**direction_coverage**:
Dual check (ADR 0052). SearchGate BLOCKER (when search_directions present): every declared direction must have ≥1 collected entry tagged to it — the hard floor. Analysis-phase WARN claim-anchor (`artifact_checks.check_direction_coverage`): a direction with collected sources but no claim referencing them warns (anti-gaming backstop).
_Avoid_: topic_coverage (removed, ADR 0042), facet_coverage

**facet_coverage**:
Analysis-phase WARN safety net (ADR 0050), orthogonal to the user-declared direction contract. Goal_type-aware fixed core facet set (panoramic/exploratory: technical_architecture, model_product_family, cost_economics, market_industry_impact, community_ecosystem, reported_limitations; narrower set for other goal_types). Derived from source tiers + claim content (not preset user directions, preserving ADR 0042). Community facet requires ≥2 platforms; reported_limitations requires a limitations claim.
_Avoid_: direction_coverage, topic_coverage

**primary_source_ratio**:
ClaimValidator WARN metric (ADR 0051) exposing source concentration: (1) fraction of claims resting on ≥1 Tier 1/2 source; (2) fraction of claims citing a single platform. Deepens `single_source_ratio` with a tier/platform-skew axis. Advisory only.
_Avoid_: single_source_ratio (different axis: claim source count)

**reported_limitations**:
facet_coverage facet (ADR 0050) for the subject's self-reported shortcomings (e.g., SimpleQA lag, R1-Zero repetition/readability). WARN-level; if present, its sources should be Tier 1/2 (WARN if not). Phase 1 interview should prompt the user to declare "limitations" as a search_direction → enters the hard direction contract (ADR 0052). Guards against all-praise bias.
_Avoid_: limitations, weaknesses

**community_ecosystem**:
facet_coverage facet (ADR 0050) spanning HuggingFace + Reddit/HN + Zhihu/Weibo (Chinese community, see CONTEXT.md) + market news (Tier 3). Satisfied only when sources span ≥2 distinct platforms — closes the v2 single-platform (HF-only) gap.
_Avoid_: Chinese community source (a Tier 4 source type, not the facet)
_Avoid_: source diversity, tier balance

**SearchGate**:
The deep module that validates whether the search phase produced sufficient material to proceed to analysis. Owns collected_exists, collected_schema, min_sources, tier_coverage, source_fidelity checks. topic_coverage, search_plan_compliance, domain_concentration, and tier_task_completion removed (ADR 0042). Interface: `SearchGate(workdir, config).check() → list[CheckResult]`. Internal helpers (tokenization, stop-word filtering, per-direction counting) removed with topic_coverage.
_Avoid_: search validator, search quality checker, search gate checks

**section plan**:
Phase 3a Step 1 output: `{id, title, depth_strategy, order?, deep_dive_topics: [{topic}]}`. Serves as a reference template — agent may add, remove, merge, or split sections. deep_dive_topics suggest anchors worth arguing with 3+ sources (advisory, not enforced). source_hints removed (ADR 0043) — subagent prompt injects all collected.json sources with title + source_file + snippet, letting subagent self-select relevant sources. depth_strategy determines per-section content organization rules (overview, deep_dive, comparison, methodology). `order` is an optional integer for explicit reading position in the final report; if omitted, the merge step infers position from `_REQUIRED_SECTION_IDS` for the goal_type, falling back to id-lexicographic order. Sub-structures (key_insights, tensions, claims) use unified `{summary, sources}` base pattern (ADR 0045).
_Avoid_: section outline, section schema

**section order**:
The reading order of sections in the final report, determined during merge by `_sort_sections()`. Two regimes: (1) **Quantitative goal_types** (have entries in `_REQUIRED_SECTION_IDS`): `order` field > `_REQUIRED_SECTION_IDS` position > id-lexicographic. (2) **Exploratory goal_types** (no entry): `order` field > id-lexicographic. For exploratory reports, the `order` field is the sole mechanism for correct ordering — without it, sections default to id-lexicographic (which placed "overview" after "community_evaluation"). The orchestrator must instruct subagents to assign `order` values in the section plan. ADR 0060.
_Avoid_: section sequence, section arrangement

**ClaimValidator**:
The deep module that validates claim quality in analysis.json against collected.json. Owns claim_metadata, precision_inflation, source_metadata, metric_type_homogeneity, claim_dedup, entity_number_conflict, ref_marker_validity, claim_source_ref_coverage, and source_verification_check checks. Interface: `ClaimValidator(workdir, goal_type).check() → list[CheckResult]`. Reads analysis.json + collected.json once; shared helpers (number normalization, source text matching, data variance) are private to its implementation. See ADR 0027, ADR 0028.
_Avoid_: claim checker, claim gate, claim quality checker

**source fidelity**:
`.workdir/sources/` 目录中原文文件的存在率和非空率。替代 `fetched_content_depth` 作为 search→analysis gate 的 BLOCKER 检查。阈值：如果 >30% 的 collected entry 没有对应的原文文件（文件不存在或为空且未标记 `fetch_failed: true`），则 BLOCKER。`fetch_failed: true` 的 entry 豁免检查，但豁免率本身受上限约束（如 >50% 豁免则 WARN）。Shallow 阈值 2000 chars（>30% 则 BLOCKER），thin 阈值 5000 chars（WARN）。
_Avoid_: fetch quality, content depth, fetch completeness

**source_file**:
collected.json entry 中新增的字段，值为 `.workdir/sources/` 下对应原文文件的相对路径（如 `"sources/abc123.md"`）。与 `url_hash` 一一对应。subagent 通过此字段定位原文文件。
_Avoid_: source path, content file

**UrlRewriter**:
代码策略实现的 Protocol，仅负责 URL 重写（`rewrite_url(url) → str`）。两种实现：`fetch_strategies/*.py` 代码式特例（如 ArxivStrategy、GithubStrategy）和 `url_rewrite` 声明式规则（config.json）。代码策略不再包含 `tools()` 和 `retries()`——这些由 config.json 统一提供（ADR 0038）。
_Avoid_: url rewriter strategy, rewrite handler

**FetchStrategy**:
Fetcher 消费的完整策略接口：`rewrite_url` + `tools` + `retries`。由 `get_fetch_strategy()` 组合返回：当 UrlRewriter 存在时，组合 UrlRewriter + config tools/retries 为 ComposedStrategy；否则走 ConfigRewriteStrategy 或 DefaultStrategy。config.json 是 tools 顺序的单一权威源（ADR 0038）。
_Avoid_: fetch config, fetch handler, fetch adapter

**url_rewrite**:
config.json source 定义中的声明式 URL 重写规则。格式：`[{"match": "regex_pattern", "replace": "replacement_template"}]`。由通用 regex rewrite engine 执行，代码零 source 特化。
_Avoid_: url transform, url mapping, url conversion

**adaptive retry**:
按 source tier 分级的 fetch 重试策略。Tier 1-2 每工具重试 2 次，Tier 3-4 每工具重试 1 次。单条 URL 全局超时 60 秒。所有工具穷尽后：若存在浅内容（< shallow_threshold），保存最佳浅内容并标记 `content_insufficient: true`；若所有工具均失败（返回 None），标记 `fetch_failed: true`（ADR 0038）。
_Avoid_: retry policy, fetch retry, retry strategy

**Fetcher**:
Fetch pipeline 的执行引擎。读取 FetchStrategy 配置，编排工具 fallback 链（requests+markdownify → Playwright），清洗内容，写 source 文件，返回 JSON 元数据。接口：`Fetcher(workdir, config).fetch(url, tier) → FetchResult`。与 FetchStrategy 的关系：FetchStrategy 是声明式配置，Fetcher 是执行器。
_Avoid_: fetch executor, fetch runner

**fetch CLI**:
`python -m scripts.cli fetch <url>` 子命令。两种模式：autonomous（CLI 自主抓取 via requests/Playwright）和 pipe（agent 用 exa 抓取后 pipe 内容给 CLI 做后处理）。返回 JSON 元数据供 agent 构建 collected.json entry。是 agent 与 Fetcher 之间的接口。
_Avoid_: fetch command, fetch tool

**pipe mode**:
CLI fetch 的 `--from-stdin` 模式。agent 在外部调用 exa/webfetch，将内容 pipe 给 CLI。CLI 跳过清洗和自主抓取，只做写文件、算 hash、返回元数据。用于 CLI 无法直接调用 exa（无 API key）的场景。
_Avoid_: stdin mode, agent-fetch mode

**content_insufficient**:
FetchResult 中的布尔标志。当抓取内容 < shallow_threshold（默认 2000 chars）时为 true。信号 agent 尝试替代抓取路径（通常是 exa via pipe mode）。与 `fetch_failed` 互补：`content_insufficient=true` + `fetch_failed=false` 表示获取到了部分内容，agent 可选择重试或使用浅内容（ADR 0038）。
_Avoid_: shallow fetch, truncated content

**fetch_defaults**:
config.json 顶层配置块。提供 fetch 全局默认值：source_dir、shallow_threshold、playwright_enabled、playwright_channel、playwright_timeout。source 级 `fetch` 块可覆盖 per-source 设置（如 tools）。`max_characters` 已删除（ADR 0038，YAGNI，与"存全文"决策矛盾）。
_Avoid_: fetch config, fetch settings

**search plan**:
Removed (ADR 0042). Agent searches freely; config.json sources serve as repair hints when search gate BLOCKERs fire, not as a pre-search plan.
_Avoid_: search strategy, search outline

**search gate repair routing**:
When search gate fires a BLOCKER, it queries config.json for the missing dimension's source list and emits concrete repair hints (e.g., "tier 2 零覆盖 → try site:github.com, site:en.wikipedia.org"). config.json's role shifts from "pre-search plan template" to "post-search repair toolbook" (ADR 0042).
_Avoid_: gate fix hints, repair suggestions

**信任边界 (trust boundary)**:
The validation point between an untrusted producer (subagent) and a trusted artifact (section_file). Subagent output must pass two-layer validation before being written to section_file: (1) structural validation (JSON legality, field types, enum values, non-empty sources); (2) semantic validation (URLs in sources must exactly match collected.json entries). Validation failure triggers retry (max 2) with full structured error report injected into prompt. 3 failures → BLOCK pipeline, orchestrator manual rewrite. Orchestrator rewrite also fails → incomplete section. Introduced by ADR 0053.
_Avoid_: output validation gate, intake check

**repair loop**:
The cycle of (detect issue → apply fix → re-validate) for review findings. After review subagent produces review_report.md + fix_list.json, a review-fix subagent processes issues and outputs fix_report.json (per-issue fixed/skipped status). If BLOCKER-level issues remain, a lightweight review (same subagent, targeted prompt checking only the original BLOCKER issues) verifies fixes. Max 2 repair rounds. BLOCKER all fixed + lightweight review confirmed → passed; otherwise → degraded. Introduced by ADR 0055.
_Avoid_: review-fix cycle, fix loop

**incomplete section**:
A section in analysis.json marked `status: "incomplete"` after trust boundary validation failed 3 times and orchestrator manual rewrite also failed. The section's content is present but unreliable — readers should not cite claims from an incomplete section. An incomplete section necessarily results in `degraded` review_status, but `degraded` may also result from unresolved review issues without any incomplete section. Introduced by ADR 0053.
_Avoid_: broken section, failed section

**project root**:
The directory containing `.git/`. Used as the base for resolving all relative paths (output_dir, WORKDIR). Auto-detected by walking up from CWD. Falls back to CWD if not in a git repository.
_Avoid_: repo root, workspace root

**Artifacts**:
- **scope.json** — Phase 1 output: topic, goal_type, depth, audience, report_language, scope_description, search_directions (fallback reference, ADR 0046), decision_questions? (hint field), english_title?
- **collected.json** — Phase 2 output: array of {url, title, snippet, source_tier, fetched_content, covered_directions?, vendor_affiliation?}
- **analysis.json** — Phase 3a output: topic, goal_type, sections (each with id, title, content, depth_strategy, key_insights, tensions, claims)
- **review_report.md** — Phase 3b output: subagent review findings
- **fix_list.json** — Phase 3b output: structured fix list from review subagent (issue_id, type, severity, section, description, recommendation). Machine-consumable complement to review_report.md. Introduced by ADR 0055.
- **fix_report.json** — Phase 3c output: per-issue fix status from review-fix subagent (fixed/skipped+reason). Consumed by repair loop to determine passed/degraded. Introduced by ADR 0055.
- **config.json** — Skill configuration: sources (4 tiers, each with language field), routes (10 goal_types), output_dir, default_report_language, default_depth, goal_type_defaults

## Relationships

- A **goal_type** determines required **source tiers** route, required sections in **analysis.json**, and **depth strategy** for each section via implicit mapping (goal_type × section id → strategy)
- A **Claim** belongs to a section in **analysis.json** and references URLs from **collected.json** via its **sources** field
- **depth** drives minimum source count per search_direction; **depth strategy** drives per-section content organization; these are independent concerns
- **audience** does not drive deterministic logic; **decision_questions** does not drive deterministic logic — both are hint fields
- **summary** and **sources** are the unified field names across key_insights, tensions, and claims sub-structures (ADR 0045)
- **covered_directions** overrides **topic_coverage** token matching when present — removed (ADR 0042), both concepts no longer exist
- **precision: exact** requires **evidence_type: official_data** or **independent_benchmark**
- A **gate phase responsibility** determines which checks run at each pipeline transition; BLOCKERs caught at earliest stage
- **BLOCKER report checks** block the final gate (review→final); the 7 WARN report checks are advisory
- **review_report_exists** blocks review→final; review is mandatory (ADR 0028)
- **Reference numbering** uses `{{ref:URL}}` markers in analysis.json; claim.sources must be a subset of content `{{ref:URL}}` markers in the same section
- **ref_marker_validity** and **claim_source_ref_coverage** are analysis-phase BLOCKERs ensuring URL consistency between analysis.json content and collected.json
- Source **language** field in config.json is used by **search gate repair routing** to suggest language-appropriate sources when a direction has zero coverage
- **search gate repair routing** uses config.json as a post-search repair toolbook: when a BLOCKER fires (topic_coverage, tier_coverage, min_sources), gate queries the relevant tier's source list and emits concrete site_query suggestions
- **search plan** is removed (ADR 0042); agent searches freely without a pre-search plan
- **deep-dive anchor** selection is performed by the orchestrator in **section plan** as advisory suggestions; agent may add anchors beyond the plan. Each panoramic/exploratory section must have ≥ 2 deep-dive anchors (enforced by gate, not by plan)
- **false depth** is prohibited by **synthesis guard** and writing-guide content rules
- **source fidelity** replaces **fetched_content_depth**: gate now checks `.workdir/sources/` file existence rather than `fetched_content` field character count. Includes snippet overlap heuristic: if >30% of source files have >80% of their content covered by the snippet, BLOCKER (summary-not-full, ADR 0040).
- **fetched_content** field is derived from the written source file (first 200 chars of the file); populated in Step 2.3 after discovery in Step 2.2. During Step 2.2, `fetched_content` is `""` and `source_file` is `null` (ADR 0039).
- **UrlRewriter** is the code strategy Protocol — only `rewrite_url()`, no `tools()` or `retries()` (ADR 0038)
- **FetchStrategy** is the Fetcher-facing Protocol — `rewrite_url` + `tools` + `retries`; always composed from UrlRewriter + config, or config-only, or DefaultStrategy
- **fetch router** resolves `get_fetch_strategy(source_config) → FetchStrategy`; composes UrlRewriter (if code strategy exists) with config tools/retries as ComposedStrategy (ADR 0038)
- config.json is the single source of truth for **tools** order; code strategies cannot override it
- **adaptive retry** by Tier: Tier 1-2 retry twice per tool, Tier 3-4 retry once; 60s global timeout
- **Fetcher** reads **FetchStrategy** for URL rewrite and tool order; FetchStrategy is declarative, Fetcher is executable
- **fetch CLI** is the agent-facing interface to **Fetcher**; agent calls CLI, CLI calls Fetcher. Two modes: single-URL (`fetch <url>`) and batch (`batch-fetch --from-stdin`).
- **batch-fetch CLI** processes multiple URLs in one call (ADR 0041). Accepts JSON array of `{url, content, tier?}` via stdin, writes source files via `Fetcher.save_piped()`, updates collected.json automatically. Eliminates agent's opportunity to summarize (the correct path is the easy path). Also has `--pending` mode to list URLs that still need fetching.
- **pipe mode** bypasses **Fetcher**'s autonomous fetch; agent provides content, CLI does post-processing only (skip cleaning)
- **content_insufficient** triggers agent to switch from autonomous path to pipe path (exa); `content_insufficient=true` + `fetch_failed=false` means partial content was saved (ADR 0038)
- **fetch_defaults** in config.json provides global defaults including `playwright_enabled`; source-level `fetch` blocks override per-source; `--no-playwright` CLI flag > `playwright_enabled` config > `True` default
- **source_file** in collected.json points to `.workdir/sources/{url_hash}.md`; subagents read original text via Read tool
- subagent prompt injects source_file path + title only (no preview); subagent MUST use Read tool on source files to access original text before writing claims
- **信任边界** validates subagent output before writing to section_file: structural validation (schema) + semantic validation (URL match against collected.json). `ref_marker_validity` and `claim_source_ref_coverage` remain as defense-in-depth at gate level (ADR 0053, ADR 0054)
- **repair loop** closes the review→fix→re-validate cycle: review-fix subagent + fix_report.json self-report + lightweight review verification. Max 2 rounds. BLOCKER all fixed → passed, otherwise → degraded (ADR 0055)
- **incomplete section** (`status: "incomplete"`) implies `degraded` review_status, but `degraded` does not imply incomplete section — degraded may also result from unresolved review issues in the repair loop

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

Unchanged routes: fact_check [1,2,4], other [3,2,1]. (panoramic_understanding changed to [2,1,3,4] by ADR 0049 — Tier 2 now required, supersedes ADR 0031's panoramic row.)

New Tier 1 sources added for Chinese academic coverage:
- **Wanfang** (wanfangdata.com.cn): Chinese academic database, same Tier 1 as CNKI
- **CQVIP** (oa.cqvip.com): Chinese academic database (维普) OA platform, open access without login
- **CBOA** (cboa.cqvip.com): 维普旗下 OA 开放获取平台, 5500万篇全文无需登录, Tier 1 as CNKI
- 国标 (gb688.cn) considered but excluded due to connection timeout issues
- CNKI/Wanfang require institutional login for full text; CQVIP (OA) and CBOA provide free full-text access
