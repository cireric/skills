# ADR 0010: depth 驱动 per-direction 最少来源数

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

SKILL.md 说 depth 是 hint field（不影响 code-level 行为），但实际运行中搜索深度完全由 AI 自行决定，没有质量保证。deep 深度的调研可能搜索不足（只搜了1-2个来源/方向），quick 深度的调研可能过度搜索。

## Decision

depth 从 hint field 升级为 code-level 行为驱动因素：

- 在 search→analysis gate 中增加 `per_direction_min_sources` 检查
- 检查逻辑：对每个 search_direction，在 collected.json 的 title+snippet 中命中的来源数 >= N
- N 由 depth 决定：quick=1, standard=3, deep=5
- 不满足时为 WARN（不是 BLOCKER，因为某些方向可能确实来源稀少）

## Consequences

- depth 有实际行为影响，不再只是 hint
- CONTEXT.md 中 depth 的定义需要从"hint field"改为"behavior-driving field"
- 需要更新 CONTEXT.md 中 hint field 的定义（audience 仍是 hint，depth 不再是）
