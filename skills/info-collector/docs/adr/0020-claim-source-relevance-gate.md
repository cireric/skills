# ADR 0020: source_url 内容相关性 gate check

- **Status**: Implemented
- **Date**: 2026-06-18
- **Context**: info-collector skill

## Context

审查（review）阶段发现 source mismatch 问题：claim 的 `source_urls` 指向的 `fetched_content` 不包含 claim 中的关键数字/实体。例如 claim 写"85% 开发者使用 AI 编码工具"，source_urls 指向 Anthropic 报告，但该报告的 fetched_content 中没有 85% 这个数字。

当前 `check_url_traceability()` 仅验证 URL 存在于 collected.json，不验证内容相关性。这导致 source mismatch 只能通过 review subagent 人工发现，而无法在 gate 阶段自动检测。

## Decision

在 `gateway.py` 中新增 `check_claim_source_relevance()` check，作为 WARN 级别 gate（非 BLOCKER），对 claim 与 source fetched_content 的相关性做启发式检查。

### 算法设计

1. 遍历 analysis.json 中所有 claims
2. 对每条 claim，提取其 text 中的数字（`_number_found_in_source` 复用）
3. 检查这些数字是否出现在 claim 的任一 source_url 对应的 `fetched_content` 中
4. 若 claim text 中的数字不在任何 fetched_content 中 → WARN

### 阈值与级别

- **WARN 级别**：不阻塞流程，仅在 gate 输出中提示
- **不设 BLOCKER**：数字相关性检查存在误报风险（数字可能以不同格式出现，如"9.8B"vs"98亿"）
- 与现有 `check_precision_inflation()` 互补：precision_inflation 检查 evidence_type 与 precision 的合规性；source_relevance 检查数字是否在源中

### 实现细节

```python
def check_claim_source_relevance(workdir: Path) -> CheckResult:
    # 1. 读取 analysis.json 和 collected.json
    # 2. 构建 url -> fetched_content 映射
    # 3. 遍历每个 section 的 claims
    # 4. 对含数字的 claim，检查数字是否在 fetched_content 中
    # 5. 返回 CheckResult(name="claim_source_relevance", level="WARN", ...)
```

### 复用

- `_number_found_in_source()` — 已有函数，从 `check_precision_inflation` 中提取
- `_normalize_numbers()` — 已有函数
- URL 映射逻辑 — 与 `check_url_traceability` 相同

## Implementation Steps

1. **提取公共函数**：将 `_number_found_in_source` 和 `_normalize_numbers` 移至 `lib/numbers.py`（或保留在 gateway.py 中仅添加 import）
2. **实现 `check_claim_source_relevance()`**：约 40-50 行
3. **添加到 `run_all()`**：在 `check_precision_inflation` 之后
4. **编写测试**：`TestCheckClaimSourceRelevance` 类，6-8 个场景
5. **更新现有测试 fixture**：确保有 `fetched_content` 字段

## Alternatives Considered

1. **BLOCKER 级别**：过于激进，误报会阻塞流程。首次部署应 WARN 积累数据，后续根据误报率决定是否升级。
2. **token overlap 而非数字匹配**：token overlap 误报率更高（"coding" 在所有源中都会匹配）。数字是更精确的信号。
3. **embedding similarity**：需要额外依赖和 API 调用，成本过高。

## Consequences

- 新增一个 WARN check，提高 source mismatch 的早期发现率
- 对已有的测试 fixture 影响：需确保 collected.json 有 fetched_content（S1 已部分解决）
- 若误报率低，后续可升级为 BLOCKER
