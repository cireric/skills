---
name: info-collector
description: >
  Collect, organize, and summarize structured information from web sources.
  Triggers on 帮我查查, 搜集资料, 整理, 调研, research, collect info, find information,
  gather data.
---

# Info-Collector Skill

Collect, organize, and summarize structured information from web sources.

## Usage

- **Trigger phrases**: 帮我查查, 搜集资料, 整理, 调研, research, collect info, find information, gather data
- **Slash command**: `/info-collector`
- **Output**: Markdown report in `<project_root>/<config.json:output_dir>` with YAML front matter

## Path Convention

All relative paths in this skill are relative to the **project root** (where `scripts/cli.py` is run from):

| Reference                                 | Actual location                                                                    |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| `<project_root>/.workdir/`                | `<cwd>/.workdir/` — e.g. `D:\Project\.workdir\`                                    |
| `<project_root>/<config.json:output_dir>` | `<cwd>/<output_dir>` — configured in `skills/info-collector/config.json`           |

## Setup Wizard

When `skills/info-collector/config.json` does not exist (first run), guide the user through setup:

1. **output_dir**: Ask where reports should be saved. Accept relative (resolved against project root) or absolute paths. Default: `./reports/`
2. **default_report_language**: Ask preferred report language (e.g., zh, en). This becomes the default for every research unless overridden in Phase 1. Default: `zh`
3. **default_depth**: Ask typical research depth (quick/standard/deep). Default: `standard`
4. **Source customization**: Show the 4-tier source list from config.json. Ask if user wants to add or remove sources per tier (e.g., add Dev.to to Tier 2, remove Medium from Tier 2)

After collecting answers, write `skills/info-collector/config.json` and confirm: "配置已写入 config.json"

**Re-running the wizard**: User can request setup wizard at any time by saying "重新配置" or "run setup wizard". This overwrites the existing `skills/info-collector/config.json`.

## Phase 1: Scope

1. **Interview** the user to determine:
   - Read `config.json` from `skills/info-collector/config.json` and verify `output_dir` is set; if missing, warn the user and ask for an output directory path
   - `topic` — what to research
   - `goal_type` — which of the 9 types (or "其他" for custom)
   - `depth` — quick | standard | deep
   - `audience` — CTO | engineer | researcher | general (influences framing and language)
   - `scope_description` — natural language summary
   - `search_directions` — 1+ specific directions to search. **Prefer English keywords** (e.g., "agentic coding frameworks" not "智能体编程框架") because CJK tokens match poorly against English source snippets. Chinese directions are allowed but may trigger topic_coverage WARN instead of BLOCKER due to tokenization limitations.
   - `report_language` — (optional) override `default_report_language` from config for this report (e.g., "en", "zh")

2. Write `scope.json` to `<project_root>/.workdir/scope.json`.

3. **Run gate**: `python scripts/cli.py proceed --from scope --to search`
   - If exit code != 0 → show errors, fix scope.json, retry.

## Phase 2: Search-Collect-Filter

1. **Get source recommendations**: `python scripts/cli.py source <goal_type>`

2. **Search**: Use `exa_web_search_exa` + `exa_web_fetch_exa` (primary),
   `playwright_browser_*` (supplementary). Use `site:` queries from recommended sources.
   Aim for ~3 search rounds (soft limit).

**Search language rule**: Search English-language sources using English queries even if the topic is in Chinese. Translate search keywords to English for `site:` queries on English domains (arxiv.org, github.com, stackoverflow.com, etc.). Use Chinese queries only for Chinese domains (cnki.net, zhihu.com, baidu.com, etc.). This ensures high-quality results from international sources regardless of topic language.

**Tier 4 search strategy**: Tier 4 sources (forums, personal pages, unverified) are not pre-configured in config.json. When deep research requires Tier 4 coverage, search broadly on Reddit (`site:reddit.com`), Hacker News (`site:news.ycombinator.com`), Dev.to (`site:dev.to`), and personal blogs. All Tier 4 findings must use strong qualifier language in the report ("an unverified source claims", "according to a forum post"). Do NOT present Tier 4 findings with the same authority as Tier 1 or Tier 2.

3. **Collect**: Add each result to `<project_root>/.workdir/collected.json`:

   ```json
   {
   	"url": "...",
   	"title": "...",
   	"snippet": "...",
   	"source_tier": 2,
   	"fetched_content": "..."
   }
   ```

4. **Run gate**: `python scripts/cli.py proceed --from search --to analysis`
    - Checks topic_coverage (BLOCKER), tier_coverage (WARN), per_direction_min_sources (WARN), and min_sources (WARN).
   - If BLOCKER → search more before proceeding.

## Phase 3: Report

### 3a: Build analysis.json

Synthesize findings from `<project_root>/.workdir/collected.json` into `<project_root>/.workdir/analysis.json`.

**⚠️ Content quality is the #1 priority.** The `content` field is rendered as-is in the final report by reporter.py. If the content is thin, the final report will be thin. Write as if you are writing the final report section.

#### Step 1: Plan sections

Read collected.json and scope.json. Decide the sections (id, title) based on goal_type requirements (see section_coverage check in gateway.py). Write the section plan but do NOT write content yet.

#### Step 2: Write each section's content independently (parallel)

For **each section**, delegate an independent agent call to write the `content` field as **full, engineer-grade Markdown**:

1. **One section per agent call** — never write all sections in a single call. This prevents token-limit compression and ensures each section gets full output capacity.
2. **Write content FIRST, extract claims AFTER** — within each call, first write the complete Markdown narrative (tables, comparisons, detailed parameters, architecture breakdowns), then extract structured claims from what you wrote.
3. **Embed allowed URL list in every subagent prompt** — extract all URLs from `collected.json` and include them in the prompt as the **only** valid `source_urls`. Any `source_url` not in this list will be caught by the `analysis→review` gate's url_traceability check and block progression. Format:

   ```
   ## Allowed source URLs (use ONLY these in source_urls)
   - https://example.com/article1
   - https://example.com/article2
   ...
   ```

4. **Specify output path with `.workdir/` prefix in every subagent prompt** — subagents must write their output to `<project_root>/.workdir/`, NOT the project root. Include this instruction explicitly:

   ```
   ## Output path
   Write your section JSON to: <project_root>/.workdir/analysis_section_<id>.json
   Do NOT write to the project root.
   ```
3. **Content must include**:
   - **Structured tables** for any multi-dimensional comparison (framework features, benchmark scores, protocol specs, pricing, etc.). Tables are the primary way engineers extract information — prefer tables over paragraphs for comparisons.
   - **Specific numbers with context** — not "scores around 70%" but "Claude Opus 4.5: 80.9% on Verified, ~45-48% on Pro, ~33pt gap"
   - **Architecture details** — not "uses AsyncGenerator" but "AsyncGenerator core loop, ~4,683 lines, 43+ built-in tools, 5-layer permission model (from full-auto to per-action approval), DeepImmutable state management"
   - **Concrete examples** — not "supports parallel agents" but "git worktrees isolate each agent's working directory, branch, and staging area; `/apply-worktree` rebase/merges changes back"
4. **Content length guidance**: Each section's content should be 500-2000 words of substantive analysis. If a section has less than 300 words, it is almost certainly too thin — check if tables or details are missing.
5. **Use sub-headings (###) within content** to organize complex sections. Example: a "Framework Comparison" section should have ### sub-headings per framework.
6. **No top-level headings in content**: Content must not start with `# ` or `## `. All headings must be `### ` or below. The section `title` itself serves as the `## ` level — content is nested under it.
7. **Concreteness self-check**: Before finalizing each section's content, verify:
   - Every number has context (not "70% accuracy" but "70% on MNIST, 65% on CIFAR-10 under 5-shot conditions")
   - Every entity has a specific name (not "a framework" but "LangChain v0.3")
   - Comparisons use tables, not paragraphs
   - Each claim has its source URL adjacent (inline or footnote within the content)

#### Step 3: Assemble analysis.json

Merge all sections into a single analysis.json. **This step is JSON merge only — never rewrite or rephrase section content.** Each section's `content` and `claims` fields are taken verbatim from the subagent outputs. If content needs improvement, go back to Step 2 and re-delegate that section.

```json
{
	"topic": "...",
	"goal_type": "tech_selection",
	"audience": "engineer",
	"sections": [
		{
			"id": "comparison",
			"title": "Comparison",
			"content": "Full Markdown narrative with tables, details, and sub-headings...",
			"claims": [
				{
					"text": "Claim statement",
					"source_urls": ["https://..."],
					"evidence_type": "official_data | independent_benchmark | third_party_estimate | qualitative_trend | expert_opinion",
					"confidence": "high | medium | low",
					"precision": "exact | range | qualitative",
					"source_metadata": {
						"test_conditions": "Brief description of test methodology and hardware",
						"test_date": "2026-Q1",
						"source_type": "vendor_benchmark | independent_test | production_case | survey"
					}
				}
			]
		}
	]
}
```

Every claim MUST have at least one source_url linking to a URL in collected.json.

**Content 必须保证来源可追溯：**

- **每项量化声明（benchmark 数字、百分比等）必须附带来源标识**：内联 URL、引用编号 `[1]` 映射到附录、或直接以链接形式给出
- **Benchmark 数据必须附测试环境摘要**：至少包含硬件、OS、运行时版本、测试日期
- 附录或每个来源名必须在报告中有对应的完整 URL 可点击

**Goal-type 差异化追溯要求：**

| goal_type                                                                   | 最低追溯要求                                                   |
| --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `tech_selection`, `competitive_comparison`, `feasibility_assessment`        | 每项 benchmark 数据标注来源 URL + 测试环境（CPU/OS/版本/日期） |
| `academic_research`                                                         | 正式引用格式（如 `[1]` 附录映射）                              |
| `exploratory`, `market_analysis`, `background_check`, `fact_check`, `other` | 每个声明至少附带来源 URL 或引用编号                            |
| `panoramic_understanding`                                                   | 每段主要结论至少一个来源链接                                   |

**Tier-aware source citations in content:**

Different source tiers require different language in body text to accurately reflect their evidentiary weight:

| Source Tier | Citation Language Rule | Example |
|-------------|----------------------|---------|
| Tier 1 (official docs, standards body) | Cite as authoritative | "According to OpenAI's official documentation..." |
| Tier 2 (industry reports, established media) | Cite with source attribution | "A 2025 Gartner report estimates..." |
| Tier 3 (blogs, tutorials, community posts) | Use qualifier: "according to a blog post", "a community analysis suggests" | "A community benchmark on Reddit suggests..." |
| Tier 4 (forums, personal pages, unverified) | Use strong qualifier: "an unverified source claims", "according to a forum post" | "An unverified forum post claims..." |

Never present Tier 3 or Tier 4 findings with the same authority as Tier 1 or Tier 2. The citations in body text must let readers assess evidentiary weight at a glance.

**Precision rules for claims:**

- `evidence_type: "third_party_estimate"` or `"qualitative_trend"` → MUST NOT use `precision: "exact"` (gate BLOCKER)
- `precision: "exact"` → MUST have `evidence_type` of `"official_data"` or `"independent_benchmark"`
- Benchmark numbers from different test conditions → use `precision: "range"` and annotate in `source_metadata.test_conditions`

**Methodology section:** For quantitative goal_types (`tech_selection`, `competitive_comparison`, `feasibility_assessment`, `market_analysis`, `academic_research`), include a section with `id="methodology"` in analysis.json. This section must describe:

- Data sources and their test conditions
- Limitations of cross-source comparisons
- Date range of data collection

#### Step 3.5: Run concreteness check

After assembling analysis.json, run the gateway check to catch content issues before drafting:

`python scripts/cli.py gateway`

- If BLOCKER → fix analysis.json and re-run gateway
- If clean → proceed to 3b

This catches issues like missing methodology sections, precision violations, and content quality problems early.

#### Recommendation structure (for `tech_selection` / `competitive_comparison`)

For `tech_selection` and `competitive_comparison` goal types, the report must include a structured recommendation section with three components written in the `content` field of analysis.json (no separate schema fields).

**推荐矩阵 (Recommendation Matrix):**

A comparison table that scores each option against key criteria:

| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Performance | 30% | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Cost | 25% | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Ecosystem | 25% | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Learning Curve | 20% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

Scores must be justified with evidence from the report body. Use emoji scales (⭐/★), numeric (1-5), or descriptive (Strong/Moderate/Weak). Include a weight column when criteria have different importance.

**关键决策因素 (Key Decision Factors):**

A numbered list of the most important factors users should consider when choosing:

1. **Factor name** — Explanation supported by evidence from comparison sections
2. **Factor name** — Explanation supported by evidence from comparison sections

Each factor must reference specific data rather than general impressions.

**不推荐场景 (Not-Recommended Scenarios):**

Explicitly state when each option should NOT be chosen:

- **Option A** — 不推荐用于 X 场景，因为... (Not recommended for X scenario because...)
- **Option B** — 不推荐用于 Y 场景，因为...
- **Option C** — 不推荐用于 Z 场景，因为...

This section must use explicit "不推荐" or "not recommended" language so readers can quickly identify unsuitable options. Place it under a section with `id: "recommendation"` (or as part of `id: "comparison"` if space is tight).

#### Anti-patterns (DO NOT)

- ❌ Writing all sections in a single agent call → token-limit compression makes content thin
- ❌ Writing claims before content → constraints thinking, produces checklist not narrative
- ❌ Using paragraphs where a table would be clearer → engineers scan tables, not walls of text
- ❌ Vague qualifiers without numbers → "significantly higher" is useless; "23% vs 80.9%, ~33pt gap" is useful
- ❌ Omitting architecture details because "the reader can look it up" → the report IS the lookup
- ❌ Content starting with `## Section Title` — top-level headings create structural conflicts with the report template
- ❌ Pronouns without antecedents — "它支持并行处理" → what is "它"? Name it explicitly every time
- ❌ Separating sources from claims — source URLs must be adjacent to their claims, not collected at the end

### Gate: proceed --from analysis --to review

Run: `python scripts/cli.py proceed --from analysis --to review`

- Validates analysis.json has topic, goal_type, non-empty sections, and url_traceability (all claim source_urls exist in collected.json).
- **YOU MUST ASK THE USER**: "启动独立审查？"

### 3b: Review

If user says **yes**:

1. Read `references/REVIEW_PROMPT.md` for the review prompt
2. Launch a subagent with that prompt
3. Subagent reads scope.json, collected.json, analysis.json
4. Subagent writes `<project_root>/.workdir/review_report.md` — **include the explicit `.workdir/` output path in the subagent prompt** to prevent writing to project root
5. Fix any issues found in analysis.json
6. **After fixing analysis.json, you MUST re-run the gate**: `python scripts/cli.py proceed --from analysis --to review` — this re-runs the validation checks on the updated analysis.json. Do NOT skip this step; fixes to analysis.json can introduce new violations (e.g., broken url_traceability, schema errors) that must be caught before proceeding.

If user says **no** → quality will be set to `unreviewed` at finalization.

### 3c: User confirmation + Final report

Show the review report (or degradation notice) to user and ask:

- User says **"可以了"** → Run: `python scripts/cli.py proceed --from review --to final`

  This runs gateway.py with 15 checks inside:
  - artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, metric_type_homogeneity, claim_metadata, claim_verified, source_metadata, content_concreteness, methodology_depth, recommendation_structure, source_tier_balance, claim_dedup
  - BLOCKER fails = stop and fix
  - WARN = noted but does not block

   Then generate final report (saves to `<project_root>/<config.json:output_dir>/` automatically):

   ```
   python scripts/cli.py report --quality <passed|degraded|unreviewed> --search-rounds N --source-count N --version V [--output DIR]
   ```

   - `--output DIR`: Override config.json `output_dir` for this report

  **最终报告必须包含：**
  - 来源 URL：报告中出现的每个来源名必须可追溯到完整 URL（内联链接或附录映射表）
  - 测试环境：包含至少一行说明各 benchmark 的硬件、OS、运行时版本和测试日期
  - 方法论文档：如适用 goal_type 的定量分析，方法论章节不可省略

  验证命令（手动检查）：

  ```
  grep -c "http" <project_root>/<config.json:output_dir>/<topic>_v<V>.md  # 应该有足够多的 URL
  ```

- User says **"XX 方面不够，再查查"** → Return to Phase 2:
  - Incremental search (do NOT reset scope.json)
  - Re-run Phase 3 (3a -> gate -> 3b -> 3c)
  - Version auto-increments

## Phase 4: Cleanup

1. Run: `python scripts/cli.py proceed --from final --to cleanup`
2. Ask user: "清除中间文件？"
   - Yes -> `python scripts/cli.py clean`
   - No -> `<project_root>/.workdir/` remains

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `proceed --from X --to Y` | Run phase transition gate |
| `gateway` | Run all gateway checks standalone (useful for debugging) |
| `report [flags]` | Generate final report from analysis.json |
| `source <goal_type>` | Show recommended sources for a goal_type |
| `clean` | Remove `.workdir/` |

## Quality Values

| Value      | Meaning                                        |
| ---------- | ---------------------------------------------- |
| passed     | Subagent review ran + gateway heuristics clean |
| degraded   | Gateway quality_heuristics fired WARN(s)       |
| unreviewed | User skipped subagent + gateway clean          |

## Important Rules

1. Always run `proceed` commands. Never skip a gate.
2. You MUST ask the user about review. Do not assume.
3. Do not reuse old scope.json for a different topic.
4. For "补充" iteration: preserve scope.json, increment version, re-ask review.
