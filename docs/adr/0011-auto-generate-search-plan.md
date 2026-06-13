# ADR 0011: 自动生成搜索计划

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

当前 AI 自由搜索，导致三个问题：1) 搜索查询过于宽泛（长句而非关键词）；2) 不按 route tier 顺序搜索；3) 未充分利用 site: 限定范围。

## Decision

在 scope→search gate 通过后，基于 route 和 search_directions 自动生成搜索计划：

1. 读取 config.json 中 goal_type 对应的 route（如 panoramic_understanding 的 [4, 2, 1]）
2. 对每个 search_direction × route tier 组合，生成搜索任务：
   - 查询：将 search_direction 翻译为英文关键词（用于英文 tier）或中文关键词（用于中文 tier）
   - site 限定：使用该 tier 的 source 的 site_query
   - 预期来源数：由 depth 决定
3. 将搜索计划写入 `.workdir/search_plan.json`
4. AI 按计划执行搜索，而非自由搜索

## Consequences

- 搜索策略系统化，不再依赖 AI 自律
- 搜索计划可审计（search_plan.json）
- 搜索查询更精确（关键词而非长句）
- site: 限定确保来源层级覆盖
