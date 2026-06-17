# ADR 0016: reset 子命令——管道阶段重置

- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: info-collector skill

## Context

info-collector 的管道状态由 `.workdir/` 中的 artifact 文件存在性推导（`detect_current_phase()`）。如果用户中途修改了某个 artifact（如改 scope.json 的 topic），后续 artifact（collected.json、analysis.json）与修改后的 scope.json 不一致，但管道无法自动感知。

当前唯一的清理手段是 `clean` 命令，它删除整个 `.workdir/`。用户必须从头开始，即使后续 artifact（如 analysis.json）是完整的。

两种残留场景：
- **场景 A**：单个 artifact 损坏（如 analysis.json 缺少 sections）。Gate 已能拦截（`validate_analysis()` 返回错误）。
- **场景 B**：artifact 之间内容不一致（用户改了 scope.json，collected.json 是旧数据）。Gate 不一定拦住——topic_coverage 可能恰好通过。

## Decision

### 新增 `reset --phase <X>` CLI 子命令

和 `clean` 并列的独立子命令。语义：删除目标阶段及之后产生的所有 artifact，让管道回到目标阶段之前。

| `reset --phase` | 删除的文件 | 回到的阶段 |
|---|---|---|
| `scope` | scope.json, search_plan.json, collected.json, analysis.json, review_report.md | pre_scope |
| `search` | collected.json, analysis.json, review_report.md | post_scope |
| `analysis` | analysis.json, review_report.md | post_search |
| `review` | review_report.md | post_analysis |

### 不在 `proceeds()` 内做自动一致性校验

原因：
1. Gate 已经覆盖了结构校验（`validate_scope`、`validate_collected`、`validate_analysis`）
2. "内容变更"无法通过校验自动检测——合法的 scope.json 修改不会触发任何错误
3. 在 `proceeds()` 开头加校验会让同一份数据被校验两次（proceeds 前置 + gate 内部）

### 不修改 `detect_current_phase()`

原因：它只做文件存在性检查，这是正确的行为。文件存在 = 该阶段已完成，无论内容如何。内容问题由 gate 和 `reset` 分别解决。

## Alternatives Considered

1. **`proceeds()` 开头自动校验所有已存在 artifact**：会导致校验逻辑在两处执行（前置 + gate），且无法检测"内容变更"这种意图差异。
2. **`detect_current_phase()` 返回 `inconsistent` phase**：改变了返回值域，所有调用方需处理新状态，改动面大。且"不一致"的判断标准难以定义（结构损坏？内容变更？）。
3. **扩展 `clean` 为 `clean --phase <X>`**：语义上 `clean` = 全删，加 `--phase` 让它的含义变模糊。独立子命令更清晰。

## Consequences

- 用户可以用 `reset --phase scope` 精确回退到某个阶段，不必从头开始
- `clean` 仍然是"核弹"选项，一次性删除所有内容
- `detect_current_phase()` 和 gate 逻辑保持不变，新功能是增量添加
- `search_plan.json` 随 scope 级别的 reset 一起删除（它是 scope→search gate 的产物）
