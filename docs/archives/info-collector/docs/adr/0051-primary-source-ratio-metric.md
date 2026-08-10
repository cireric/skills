# primary_source_ratio WARN metric

v2 社区评价偏倚 HF + HN，漏掉 Reddit/Zhihu/市场新闻——典型单一社区 bias。当前无机器可核查信号暴露对单一 tier / 社区平台的过度依赖。`single_source_ratio` 已覆盖"单来源 claim 比例"，但不覆盖"来源集中度/层级分布"。

## Decision

在 `ClaimValidator.check()` 新增 `primary_source_ratio`（**WARN**，建议级，不阻塞）：

- 计算 claims 中 `sources` 解析到 Tier 1/2 的比例（`primary_ratio`）。
- 同时暴露**社区/平台集中度**：claims 的来源落在单一平台（如仅 huggingface.co）的比例过高时 WARN。
- WARN 阈值按 depth 动态（standard >70% 单社区/单平台依赖、deep >50%），与 `single_source_ratio` 同轴的建议级信号。

## Consequences

机器可核查的来源集中度/层级分布信号（扩展 `single_source_ratio` 轴）。仅 WARN，不阻塞，与 `single_source_ratio` 同为建议级。不取代任何旧 ADR。需改动：`scripts/claim_validator.py`（新增 `_check_primary_source_ratio`，注册进 `check()`）。

保持 **WARN 而非 BLOCKER**：单平台/单权威源主导在小众或权威源主导的题目属合理，硬 BLOCKER 会假阳性逼 agent 造假源或空转重搜。根因修复靠 Phase 2 搜索指引的跨层来源分散要求，本指标仅作报警 + repair 指向 config toolbook。

Status: accepted
