# ADR 0002: exploratory goal_type 使用宽松 section_coverage 检查

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

`_REQUIRED_SECTION_IDS` 只定义了 6 个 goal_type 的必需 sections。`panoramic_understanding`、`exploratory`、`background_check`、`other` 这 4 个 exploratory 类型没有映射，fallback 到 `["overview", "details"]`。

AI 生成的 analysis.json 自然不会创建 `details` section（它是一个无意义的占位符），导致 review→final gate 的 section_coverage BLOCKER。

## Decision

对 exploratory 类型（panoramic_understanding, exploratory, background_check, other），section_coverage 只检查：
1. 存在 `overview` section
2. 至少有 1 个其他 section

不限制 section ids。

## Alternatives Considered

1. **为每个 goal_type 定义 required sections**：如 panoramic_understanding → [overview, methodology]。但 exploratory 的本质是探索，sections 应由 AI 根据主题自由决定，预设 ids 是过度约束。
2. **完全移除 section_coverage**：exploratory 类型不做任何 section 检查。但 overview 是最基本的组织要求，保留此检查有价值。

## Consequences

- AI 可以为 exploratory 类型自由创建有意义的 section ids
- gate 仍确保最低结构完整性（有 overview）
- 不再需要为 `details` 等 placeholder section 打补丁
