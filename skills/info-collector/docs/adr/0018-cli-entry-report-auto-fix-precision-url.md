# ADR 0018: 四项低复杂度优化——CLI 入口、report 自动推断、精度自动修正、URL 自动过滤

- **Status**: Accepted
- **Date**: 2026-06-18
- **Context**: info-collector skill

## Context

2026-06-18 的 "Agentic Coding 趋势" deep 调研实战暴露了 12 个问题（详见复盘报告），经分析后分为低复杂度（4项）和中复杂度（4项）两层。本 ADR 记录低复杂度的 4 项改进。

## Decisions

### 1. CLI 入口：加 `__main__.py` + 修 SKILL.md 命令路径

- 新增 `scripts/__main__.py`，使 `python -m scripts` 可直接运行
- SKILL.md 中所有 `python scripts/cli.py` 改为 `python -m scripts.cli`
- Path Convention 章节增加 PYTHONPATH 设置说明

**原因**：cli.py 使用相对导入，无法直接 `python scripts/cli.py` 运行。SKILL.md 中的命令与实际不符，每次调研都要试错。

### 2. report 命令 `--quality` fallback 改进

- `_detect_quality()` 在 verdict 不可解析时，检查 verdict 区域是否包含 "pass" 关键词，有则返回 `"passed"`，否则 fallback `"degraded"`

**原因**：审查子智能体可能写出非标准格式的 verdict（如 `**pass**` 在表格中而非独立行），或 agent 重写 review_report.md 为简化版。原逻辑一律 fallback degraded 过于保守。

### 3. `_sanitize_sections()` 增加精度自动修正

- 当 `evidence_type in (third_party_estimate, qualitative_trend, expert_opinion)` 且 `precision=exact` 时，自动降级为 `range`
- 在 `_sanitize_sections()` 中执行，先于 schema 校验和 gate 检查

**原因**：subagent 经常不遵守精度规则，导致 `precision_inflation` gate 反复 BLOCK。自动修正比手动修补更可靠——先修正再验证，减少 gate 循环次数。

### 4. `_sanitize_sections()` 增加 URL 自动过滤

- 新增 `collected_urls` 参数，传入 collected.json 的归一化 URL 集合
- 过滤 claim.source_urls 中不在 collected.json 的 URL，保留有效部分（不全删）
- 如果过滤后 source_urls 为空，保留原样（让 gate 报 BLOCKER 而非静默丢数据）

**原因**：subagent 的 allowed URL 列表约束是软约束，LLM 经常使用未在 collected.json 中的 URL。自动过滤比 BLOCKER 更可操作——先清理再验证。

## Alternatives Considered

1. **精度自动修正放在 gateway.py 而非 proceed.py**：gate 应只检查不修改，sanitization 是修正动作，放在 proceed.py 的 `_sanitize_sections()` 更合理（已有字段映射、裁剪等修正逻辑）。
2. **URL 过滤后全删 claim**：过于激进，可能丢失有价值的声明。保留有效 URL 让 gate 验证剩余部分。
3. **精度自动修正发出 WARN**：sanitization 已有 silent 修正的先例（section_id→id, sources→source_urls），精度降级也属于同一类别。

## Consequences

- CLI 入口对 agent 更友好，减少试错
- report 命令 quality 推断更鲁棒
- precision_inflation BLOCKER 频率降低（自动修正后不再触发）
- url_traceability BLOCKER 频率降低（自动过滤后无效 URL 被移除）
- gate 检查仍然执行，自动修正只是减少不必要的 BLOCKER 循环
