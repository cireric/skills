# ADR 0007: 来源层级覆盖 gate

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill, ISS-011 from independent review

## Context

panoramic_understanding 的 route 是 [4, 2, 1]（社区→文档→学术），但 gate 不检查是否真的搜索了每个 tier 的来源。AI 可能只在 Tier 3-4 搜索，跳过 Tier 1（学术/官方）来源，导致安全合规等深度主题覆盖不足。

## Decision

在 search→analysis gate 中增加 `tier_coverage` 检查：

- 读取 config.json 中 goal_type 对应的 route（如 panoramic_understanding 的 [4, 2, 1]）
- 检查 collected.json 是否包含每个 route tier 的至少1个来源（通过 `source_tier` 字段匹配）
- 如果某个 tier 缺少来源，发出 WARN（不是 BLOCKER，因为某些主题在特定 tier 可能确实无来源）

## Consequences

- AI 被提醒搜索未覆盖的 tier，减少覆盖盲区
- WARN 而非 BLOCKER 保持灵活性——某些 tier 确实可能无相关来源
