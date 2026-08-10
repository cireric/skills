# ADR 0008: source_metadata 强制填写 + reporter.py 防御性渲染

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

最终报告中的测试环境表格出现空行——AI 未填写 source_metadata.test_conditions，reporter.py 照原样渲染空值。

## Decision

1. **gate 强制填写**：对于 evidence_type 为 `official_data` 或 `independent_benchmark` 的 claim，source_metadata.test_conditions 不能为空。review→final gate 检查，违者为 BLOCKER。

2. **reporter.py 防御性渲染**：如果 source_metadata 字段为空，跳过该行不渲染，而非渲染空行。

## Consequences

- 官方/基准数据的 claim 必须附带测试条件
- reporter.py 不再产生空行表格
