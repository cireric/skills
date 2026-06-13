# ADR 0004: info-collector 增加 metric_type 字段 + gate 检查基准数据同质性

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill, ISS-001/ISS-003 from independent review

## Context

独立审查发现报告将 SWE-bench Verified、Pro、Terminal-Bench 三种不同测试条件的分数混合到同一张"基准数据"表格中，误导读者认为它们可比。Devin 的 PR merge rate (67%) 也被错误放在 SWE-bench Verified 列中。

AI 倾向于"信息丰富"，把所有数字塞一张表，但对于工程师受众，不同指标的混排是致命的。

## Decision

在 analysis.json 的 claim schema 中增加 `metric_type` 字段，值为枚举：`swe_bench_verified`, `swe_bench_pro`, `terminal_bench`, `pr_merge_rate`, `refactoring_safety`, `custom`。

gateway.py 新增 `check_metric_type_homogeneity`：如果一个 section 内的 claims 包含不同 `metric_type` 的量化数据，且这些 claims 被渲染在同一张 Markdown 表格中（通过 `render_group` 字段或 section 约定），则 BLOCKER。

## Consequences

- 基准数据表格只能包含同一 metric_type 的数据
- 不同测试条件的分数必须分表或明确标注
- 增加 claim schema 复杂度，但结构化程度提升
