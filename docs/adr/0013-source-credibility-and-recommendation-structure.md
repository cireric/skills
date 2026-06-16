# ADR 0013: 来源可信度标注与推荐结构独立检查

- **Status**: Accepted
- **Date**: 2026-06-15
- **Context**: info-collector skill

## Context

### 来源可信度不可见

调研报告引用多个来源，但最终 report 中来源的权威性无法一眼判断。读者需要自己点开每个链接评估质量。需要一种低认知负担的方式让来源质量可见。

同时，AI 在搜索阶段缺乏来源质量的自省机制：即使搜到了高质量（Tier 1/2）来源，也可能在撰写时大量依赖低质量（Tier 3/4）来源，导致报告可信度下降。

### 推荐结构缺乏约束

`tech_selection` 和 `competitive_comparison` 类型的报告要求有推荐结论，但 AI 经常产出笼统的推荐（"most engineers should use Cursor + Claude Code"），缺乏对比依据和反面排除说明。

设计 spec 要求检查 recommendation section 的结构完整性，原计划嵌入 `check_section_coverage` 中。

## Decision

### 1. 来源星级标注

在 report 的参考文献区，对每个来源基于其 `source_tier` 添加星级标签：

| Tier | 标签 |
|------|------|
| 1 | ★★★☆ Tier 1 |
| 2 | ★★☆☆ Tier 2 |
| 3 | ★☆☆☆ Tier 3 |
| 4 | ☆☆☆☆ Tier 4 |

标签由 `reporter.py` 中的 `_TIER_LABELS` 字典定义，在内联引用行中附加显示（如 `[1]: https://... — Title (★★★☆ Tier 1)`）。

### 2. 来源层级均衡门禁（`check_source_tier_balance`）

新增 gate check，在 search→analysis gate 序列中运行：

- **触发条件**：仅对定量目标类型（`tech_selection`, `competitive_comparison`, `numerical_forecast`）
- **检查逻辑**：在 `analysis.json` 中被引用的所有来源 URL 中，有 `source_tier` 标注的来源里 Tier 1+2 占比是否 >= 30%
- **级别**：`WARN`（非 BLOCKER，因为某些领域可能确实缺乏高质量来源）
- **阈值**：`_TIER_BALANCE_THRESHOLD = 0.30`

此门禁用于引导 AI 在搜索和写作阶段主动倾斜到高质量来源，而非事后问责。

### 3. 推荐结构独立检查（`check_recommendation_structure`）

新增独立 gate check（非嵌入 `check_section_coverage`）：

- **触发条件**：仅对 `tech_selection` 和 `competitive_comparison`
- **检查逻辑**：
  - recommendation section 必须包含 Markdown 对比表格（`|`）
  - 必须包含"不推荐"或"not recommended"说明
- **级别**：`WARN`

#### 设计偏差 #2：独立函数而非嵌入 check_section_coverage

原 spec 要求将推荐结构验证嵌入 `check_section_coverage`，但实际实现为独立的 `check_recommendation_structure`。

原因：
1. **单一职责**：`check_section_coverage` 负责验证章节是否存在，不应对章节内部结构做深度检查。推荐结构检查是对内容的语义约束，属于不同抽象层级。
2. **避免语义矛盾**：`check_section_coverage` 使用 `level="BLOCKER"`（因为缺失必要章节是不可接受的），但如果它检查推荐结构细节并返回 `level="BLOCKER", passed=True`（章节存在但结构不完整→WARN），就产生了 `BLOCKER + passed=True` 的语义矛盾。独立函数可以使用 `level="WARN"`，语义自洽。

## Consequences

- 读者能一眼判断每个来源的权威层级（★★★☆ → ★☆☆☆）
- AI 在定量报告中有激励去使用高质量来源，因为门禁会提示低 Tier 1+2 比例
- 推荐结构更规范：对比表格 + 不推荐说明成为强制要求（WARN 级别）
- 门禁之间的职责边界更清晰：章节存在性 vs 推荐结构性质量
- 需要更新 SKILL.md 中的推荐结构模板和来源定级说明
