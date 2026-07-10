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

## 架构约束

1. **source file 由 fetch 工具写入，agent 不碰。** 你可以决定抓哪些 URL、用什么搜索策略，但 source file 的内容只能来自 fetch 工具的原始输出。
2. **评判基础设施不可修改。** gate 的判定逻辑、config.json 的来源定义和路由是只读的 — 等同于 autoresearch 的 prepare.py。
3. **子 agent 输出必须符合 JSON schema。** 你可以自由决定是否用子 agent、怎么分任务，但子 agent 的输出必须符合 `references/subagent-template.md` 定义的 JSON schema。

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
可选：depth, audience, report_language, search_directions (optional, used only as conversation context)。

完成后跑门：`python -m scripts.cli proceed --from scope --to search`

### Phase 2: Search-Collect-Filter

自由搜索、发现、抓取原文。无需遵守 search_plan。搜索策略由你决定。source file 必须通过 fetch 工具写入。

完成后跑门：`python -m scripts.cli proceed --from search --to analysis`

门不通过 → 根据 repair_hints 补充 → 重跑门（最多 3 次）。repair_hints 会从 config.json 的 source 列表生成具体的搜索建议。

### Phase 3: Analysis + Review

分析 collected.json，写 analysis.json。建议参考 `references/writing-guide.md`（品味指南）。

完成后跑门：`python -m scripts.cli proceed --from analysis --to review`

门不通过 → 根据 repair_hints 修正 → 重跑门（最多 2 次）。

**审查**：gate 通过后，自动启动一轮 review subagent。subagent 写 review_report.md，你读取后选择性修复 analysis.json，然后重跑门。

subagent 失败时降级为自审。

### Phase 4: Report

生成最终报告，渲染验证。

格式检查全部为 WARN — 不阻塞流程，但建议修复。

## 参考文档

- `references/writing-guide.md` — 品味指南（false depth、synthesis guard、precision rules）
- `references/search-strategy.md` — 搜索策略建议
- `references/subagent-template.md` — 子 agent 输出 JSON schema
- `references/GATES.md` — gate 系统参考
- `references/cli-reference.md` — CLI 命令参考
- `references/REVIEW_PROMPT.md` — review subagent 提示词

## CLI Commands Reference

见 `references/cli-reference.md`。
