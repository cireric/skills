# ADR 0009: 移除跨会话迭代机制

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

SKILL.md 描述了跨会话迭代机制——用户提供上一版报告路径，AI 做增量搜索。但该机制增加了 skill 复杂度（parent 字段、dedup 逻辑、版本自增），且实际使用场景有限——"补充更新"可以通过重新调研实现。

## Decision

移除跨会话迭代机制：
- 从 SKILL.md 中删除 Cross-Session Iteration 章节
- 从 reporter.py 中移除 `parent` 参数
- 从 cli.py 中移除 `--parent` 参数
- 从 CONTEXT.md 中移除相关术语

## Alternatives Considered

1. **保留现状**：等待实际使用反馈。但机制复杂度与使用频率不成比例。
2. **增加增量质量 gate**：跨会话迭代时检查新增来源比例。增加更多复杂度。

## Consequences

- Skill 简化，维护成本降低
- 用户每次调研都是独立的，无状态
- 如果未来需要"补充更新"，可以新开调研并手动引用旧报告
