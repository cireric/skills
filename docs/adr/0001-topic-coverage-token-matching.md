# ADR 0001: topic_coverage gate 使用分词匹配

- **Status**: Superseded
- **Date**: 2026-06-13
- **Superseded-by**: 0012
- **Context**: info-collector skill

## Context

search→analysis gate 的 `topic_coverage` 检查将 `scope.json` 的 `search_directions` 作为关键词，在 `collected.json` 的 `title + snippet` 中做 `\b` 全词匹配。

当 AI 或用户在 `search_directions` 中写入自然语言描述（如"主流agentic coding框架对比：Claude Code, Cursor Agent..."），gate 无法匹配 collected.json 中的英文内容，导致 BLOCKER。

## Decision

使用 jieba 对每个 search_direction 分词，过滤停用词后逐词检查。所有词在 collected.json 中出现算该 direction 被覆盖。

添加 jieba 作为 info-collector 的运行时依赖（首个非测试 pip 依赖）。

## Alternatives Considered

1. **SKILL.md 文档约束**：要求 search_directions 必须写英文关键词。简单但脆弱——AI 倾向自然语言，无法强制。
2. **正则分词**：英文按空格/标点，中文按单字。无外部依赖但中文分词质量差（"框架"拆成"框""架"）。
3. **可选依赖 + fallback**：jieba 存在则用，否则正则。增加代码复杂度但最健壮。

## Consequences

- 新增 jieba 依赖，打破"stdlib only"原则
- 中文分词质量提升，gate 误报率下降
- scope.json 可自由使用中文自然语言描述 search_directions
