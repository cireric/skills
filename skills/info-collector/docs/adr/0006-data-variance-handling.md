# ADR 0006: 数据矛盾处理——AI 指引 + gate 检查

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill, ISS-003 from independent review

## Context

同一框架的 SWE-bench Verified 分数在不同来源间差异可达16-35点（如 Devin: 54% vs 75%）。AI 处理方式是选择一个数字或呈现范围，但不解释差异原因（版本、scaffold、测试日期不同）。

## Decision

1. **AI 指引**：在 SKILL.md 的 Phase 3a 指引中增加——当同一指标存在多个冲突数据点时，必须呈现为范围并注明差异来源（模型版本、scaffold 配置、测试日期）。不允许选择单一数字而不解释。

2. **gate 检查**：在 precision_inflation 检查中增加逻辑——如果同一 section 内两个 claims 的 metric_type 相同但数值冲突（差异超过合理范围如5%），且 precision 为 exact，则 BLOCKER。AI 必须改为 precision: range 并在 content 中解释差异。

## Consequences

- 报告中的数据矛盾会被显式标注，不再出现"选择一个数字"的情况
- gate 层面阻止未解释的数据矛盾通过
