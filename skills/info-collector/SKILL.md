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
| `<project_root>/<config.json:output_dir>` | `<cwd>/<output_dir>` — configured in `.opencode/skills/info-collector/config.json` |

## Setup Wizard

When config.json does not exist (first run), guide the user through setup:

1. **output_dir**: Ask where reports should be saved. Accept relative (resolved against project root) or absolute paths. Default: `./reports/`
2. **default_report_language**: Ask preferred report language (e.g., zh, en). This becomes the default for every research unless overridden in Phase 1. Default: `zh`
3. **default_depth**: Ask typical research depth (quick/standard/deep). Default: `standard`
4. **Source customization**: Show the 4-tier source list from config.json. Ask if user wants to add or remove sources per tier (e.g., add Dev.to to Tier 2, remove Medium from Tier 2)

After collecting answers, write config.json and confirm: "配置已写入 config.json"

**Re-running the wizard**: User can request setup wizard at any time by saying "重新配置" or "run setup wizard". This overwrites the existing config.json.

## Phase 1: Scope

1. **Interview** the user to determine:
   - Read `config.json` from `.opencode/skills/info-collector/config.json` and verify `output_dir` is set; if missing, warn the user and ask for an output directory path
   - `topic` — what to research
   - `goal_type` — which of the 9 types (or "其他" for custom)
   - `depth` — quick | standard | deep
   - `audience` — CTO | engineer | researcher | general (influences framing and language)
   - `scope_description` — natural language summary
   - `search_directions` — 1+ specific directions to search
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

Synthesize findings from `<project_root>/.workdir/collected.json` into `<project_root>/.workdir/analysis.json`:

```json
{
	"topic": "...",
	"goal_type": "tech_selection",
	"audience": "engineer",
	"sections": [
		{
			"id": "comparison",
			"title": "Comparison",
			"content": "Synthesized analysis...",
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

**Precision rules for claims:**

- `evidence_type: "third_party_estimate"` or `"qualitative_trend"` → MUST NOT use `precision: "exact"` (gate BLOCKER)
- `precision: "exact"` → MUST have `evidence_type` of `"official_data"` or `"independent_benchmark"`
- Benchmark numbers from different test conditions → use `precision: "range"` and annotate in `source_metadata.test_conditions`

**Methodology section:** For quantitative goal_types (`tech_selection`, `competitive_comparison`, `feasibility_assessment`, `market_analysis`, `academic_research`), include a section with `id="methodology"` in analysis.json. This section must describe:

- Data sources and their test conditions
- Limitations of cross-source comparisons
- Date range of data collection

**Narrative writing**: Write full Markdown narrative in each section's `content` field. Tables, emphasis, transitions, and structured formatting are all valid. The `content` field is rendered as-is in the final report, so write it as you would want the final report section to read.

### 3b: Generate draft

Write a draft report to `<project_root>/.workdir/draft/report.md`.

**Draft 必须保证来源可追溯：**

- **每项量化声明（benchmark 数字、百分比等）必须附带来源标识**：可以是内联 URL、引用编号 `[1]` 映射到附录、或直接以链接形式给出
- **Benchmark 数据必须附测试环境摘要**：至少包含硬件、OS、运行时版本、测试日期
- 附录或每个来源名必须在报告中有对应的完整 URL 可点击

**Goal-type 差异化要求：**

| goal_type                                                                   | 最低追溯要求                                                   |
| --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `tech_selection`, `competitive_comparison`, `feasibility_assessment`        | 每项 benchmark 数据标注来源 URL + 测试环境（CPU/OS/版本/日期） |
| `academic_research`                                                         | 正式引用格式（如 `[1]` 附录映射）                              |
| `exploratory`, `market_analysis`, `background_check`, `fact_check`, `other` | 每个声明至少附带来源 URL 或引用编号                            |
| `panoramic_understanding`                                                   | 每段主要结论至少一个来源链接                                   |

**Draft positioning**: The draft is a review-readable rendering of analysis.json. Review fixes should target analysis.json (not the draft file). The final report is rendered by reporter.py from the reviewed analysis.json, so all corrections must be reflected in analysis.json to appear in the final output.

### Gate: proceed --from draft --to review

Run: `python scripts/cli.py proceed --from draft --to review`

- Validates analysis.json schema and draft/report.md existence.
- **YOU MUST ASK THE USER**: "启动独立审查？"

### 3c: Review

If user says **yes**:

1. Read `references/REVIEW_PROMPT.md` for the review prompt
2. Launch a subagent with that prompt
3. Subagent reads scope.json, collected.json, analysis.json
4. Subagent writes `<project_root>/.workdir/review_report.md`
5. Fix any issues found

If user says **no** → quality will be set to `unreviewed` at finalization.

### 3d: User confirmation

Show the review report (or degradation notice) to user and ask:

- User says **"可以了"** → Run: `python scripts/cli.py proceed --from review --to final`

  This runs gateway.py with 10 checks inside:
  - artifact_exists, url_traceability, section_coverage, analysis_schema, quality_heuristics, precision_inflation, metric_type_homogeneity, claim_metadata, claim_verified, source_metadata
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
  - Re-run Phase 3 (3a -> 3b -> gate -> 3c -> 3d)
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
