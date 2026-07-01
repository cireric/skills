# ADR 0005: claim 增加 verified 字段 + 加强审查 prompt

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill, ISS-002 from independent review

## Context

独立审查发现 "Cursor Composer 2.5基于Kimi K2.5开源底座" 被错误归因到 Airbnb 博客，实际来源是 CSDN。当前 url_traceability gate 只检查 URL 存在于 collected.json，不验证 URL 内容确实支持该 claim。

## Decision

1. 在 claim schema 中增加 `verified` 布尔字段（默认 false）。
2. 审查 subagent 必须逐个将 claim 的 verified 设为 true（确认 source_url 内容确实支持该 claim）。
3. gateway.py 新增 `check_claim_verified`：review→final gate 检查所有 claim 的 verified 为 true。未标记的 claim 为 BLOCKER。
4. 加强 REVIEW_PROMPT.md：增加"验证每个 claim 的 source_url 内容确实支持该 claim"的明确指令。

## Consequences

- 来源归属错误在 gate 层面被阻断，不再依赖 AI 自律
- 审查工作量增加（逐个验证），但质量提升
- url_traceability 仍保留（检查 URL 存在性），verified 检查是更严格的补充
- 执行方式已强化：逐条验证 + 验证摘要写入 review_report.md，禁止 replaceAll 批量操作。详见 ADR 0027
