---
name: info-collector
description: >
  Invoke via /info-collector only. Structured research pipeline that produces
  a panoramic map with traceable sources — a starting point for deep research,
  not a citable authority.
---

# Info-Collector Skill

## 目标

产出可溯源的高质量研究报告。不是"通过门" — 门是方向盘，帮你找到方向，不是检查站拦你通过。

## 两个核心门

所有 gate 检查项本质上回答两个问题：

1. **覆盖度** — 该看的都看了吗？
2. **可信度** — 说的都有据吗？

门不通过时，你会收到具体修复指令（repair_hints）。执行修复 → 重新检查 → 循环，直到通过或达到重试上限。

## 约定

- **`.workdir/` 位于项目根目录**（即 `.git/` 所在目录）。CLI 通过 `--workdir` 参数接收项目根目录路径，缺省时自动向上查找 `.git/` 所在目录。运行 CLI 时传 `--workdir=项目根目录`，或确保 CWD 为项目根目录。

## 架构约束

1. **source file 由 fetch 工具写入，agent 不碰。** 你可以决定抓哪些 URL、用什么搜索策略，但 source file 的内容只能来自 fetch 工具的原始输出。
2. **评判基础设施不可修改。** gate 的判定逻辑、config.json 的来源定义和路由是只读的 — 等同于 autoresearch 的 prepare.py。
3. **子 agent 输出必须符合 JSON schema。** 你可以自由决定是否用子 agent、怎么分任务，但子 agent 的输出必须符合 `references/subagent-template.md` 定义的 JSON schema。**硬约束：派生子 agent 时，必须把 `references/subagent-template.md` 全文（EXACT 字段表 + 反例置顶）作为子 agent system prompt 的前置内容；仅让子 agent 看概述会触发 schema 漂移（字符串数组、错字段名）。**

## 执行自由

除了架构约束外，建议你自由决定执行方式：

- 搜索顺序、搜索策略、搜索深度 — 你决定
- 分析结构、写作风格、报告组织 — 你决定
- fetch 方式（batch-fetch / 逐条 fetch / 混合）— 你决定
- 子 agent 委托方式（是否用、怎么分任务）— 你决定

唯一的标准是：覆盖度和可信度门通过。

## 流程

### Phase 0: Pre-check

检查 `.workdir/` 是否有残留。有 → 问用户是否删除。

### Phase 1: Scope

面试用户确定研究范围。写入 `scope.json`。

必填：topic, goal_type, scope_description。CJK topic 还需 english_title。
可选：depth, audience, report_language, search_directions (fallback reference, ADR 0046), decision_questions (hint field, 2-3 questions the research should help answer)。

完成后跑门：`python -m scripts.cli proceed --from scope --to search`

### Phase 2: Search-Collect-Filter

自由搜索、发现、抓取原文。无需遵守 search_plan。搜索策略由你决定。source file 必须通过 fetch 工具写入。

**方向标注（ADR 0052）**：每条抓取的来源在写入 `collected.json` 时须带 `direction` 字段——取值为某个 `scope.search_directions`，或 `"other"`（搜索中发现、未归入任何声明方向）。`search→analysis` 门会 BLOCK 缺 `direction` 或某声明方向零来源的 entry。先用 `direction` 标注再写 collected.json，不要事后补。

搜索策略建议：
- **语言匹配**：对中文源（CNKI、Zhihu 等）用中文关键词搜索，对英文源用英文关键词。当 topic 包含中文实体名（如"玄铁"、"芯来"），中文搜索可能获得更精确的结果。
- **实体发现驱动**：搜索过程中发现新实体时，主动追加搜索（而非只在 gate repair 时被动补充）。
- **广度优先**：搜索阶段优先覆盖广度，先快速确认源的存在性和相关性（snippet 足够判断），再批量 fetch。
- **兜底参考**：自由搜索无结果时，参考 scope.json 的 search_directions + config.json 的 source 列表作为兜底搜索方向。
- **Exa fallback**：当 fetch 返回 content_insufficient 或 fetch_failed 时，用 exa 重新抓取后 pipe 给 CLI（`python -m scripts.cli fetch <url> --from-stdin`）。
- **多平台社区覆盖（缺陷1 修复）**：当 goal_type 路由期望 Tier 4 社区信号时，社区源须覆盖 **≥2 个平台**（如 HuggingFace + Reddit/HN，或 Reddit + Zhihu/Weibo），不要只抓单一平台——这正是 v2 的 HF-only 缺陷。`facet_coverage` 会在单一平台时 WARN，repair_hints 指向 config.json 的 site_query。
- **来源跨层分散（缺陷2 修复）**：避免单一平台 / 单一权威源主导。尽量跨 Tier 分散（Tier1 论文/标准 + Tier2 文档/开源 + Tier3 行业 + Tier4 社区）。单平台占比过高会在 analysis 阶段触发 `primary_source_ratio` WARN。

完成后跑门：`python -m scripts.cli proceed --from search --to analysis`

门不通过 → 根据 repair_hints 补充 → 重跑门（最多 3 次）。repair_hints 会从 config.json 的 source 列表生成具体的搜索建议。

### Phase 3: Analysis + Review

分析 collected.json，写 analysis.json。建议参考 `references/writing-guide.md`（品味指南）。

**避免重复劳动（supplement-1 缺陷修复）**：`analysis→review` 门要求多节报告必须由独立 subagent 写出 `analysis_section_{id}.json`（`check_subagent_delegation`，BLOCKER）。**不要先写单体 analysis.json 再拆**——直接让每个 subagent 写出对应的 `analysis_section_{id}.json`，最后合并为 analysis.json。否则门会 BLOCK 并要求返工。

**信任边界验证（ADR 0053）**：子代理输出写入 section_file 前经过信任边界验证（结构验证 + 语义验证）。验证失败时，回注完整结构化验证报告并重试（最多 2 次）。3 次验证全失败 → BLOCK 管道，你需要手动重写该 section。手动重写也失败 → section 标记为 `status: "incomplete"`，review_status 必然为 `degraded`。

**合并自动化（ADR 0054）**：当 `.workdir/` 下存在 `analysis_section_*.json` 但不存在 `analysis.json` 时，`proceed --from analysis --to review` 会自动合并 section 文件为 analysis.json，无需手动跑合并脚本。合并只执行一次。合并后会自动检查 URL 一致性（与 collected.json 比对），不匹配的 URL 输出 WARN。

完成后跑门：`python -m scripts.cli proceed --from analysis --to review`

门不通过 → 根据 repair_hints 修正 → 重跑门（最多 2 次）。

**审查**：gate 通过后，自动启动一轮 review subagent。subagent 同时输出 `review_report.md`（人类可读）+ `fix_list.json`（结构化修复指令，ADR 0055）。你读取 review_report.md 后决定是否进入 repair loop。

**Repair Loop（ADR 0055）**：review 发现问题后，启动 review-fix subagent 处理 `fix_list.json`，输出修复后 section 文件 + `fix_report.json`。修复后运行轻量 review（同一 subagent，prompt 限定只检查原 BLOCKER 问题是否已修复）。最多 2 轮修复。判定标准：所有 BLOCKER 级 issue 修复 + 轻量 review 确认 → `passed`；否则 → `degraded`。

subagent 失败时降级为自审。

### Phase 4: Report

生成最终报告，渲染验证。

格式检查全部为 WARN — 不阻塞流程，但建议修复。

**管线终点（supplement-2 缺陷修复 / ADR 0029）**：流程在 `post_final` 终止，**不存在 `final→cleanup` 转换**（`_VALID_TRANSITIONS_SET` 不含该转换）。报告生成后无需也不应执行 `proceed --from final --to cleanup`——该命令会报 `Invalid transition`。如需清理中间目录 `.workdir/`，用独立的 `python -m scripts.cli clean` 命令（手动，非管线阶段）。

## 参考文档

- `references/writing-guide.md` — 品味指南（false depth、synthesis guard、precision rules）
- `references/search-strategy.md` — 搜索策略建议
- `references/subagent-template.md` — 子 agent 输出 JSON schema
- `references/GATES.md` — gate 系统参考
- `references/cli-reference.md` — CLI 命令参考
- `references/REVIEW_PROMPT.md` — review subagent 提示词
- `references/REVIEW_FIX_PROMPT.md` — review-fix subagent 提示词
- `references/LIGHTWEIGHT_REVIEW_PROMPT.md` — 轻量 review 提示词

## CLI Commands Reference

见 `references/cli-reference.md`。
