# collected.json `direction` field for breadth coverage

info-collector 的"覆盖度"被操作化为源数量 + 层级存在性（SearchGate），而非话题维度覆盖。ADR 0042 删除了 `topic_coverage`/`covered_directions`/`search_plan`（怕预设方向窄化视野），但由此报告可过所有门却缺整面（市场冲击、基准、模型谱系、已声明局限）——正是 v2 的情况。复盘（docs/research/info-collector-retrospective.md）确认广度缺口 root cause 与 ADR 0042 同源：管线只有 tier 计数与源数量约束，无方向/维度覆盖约束。

## Decision

在 `collected.json` 每条 entry 新增 **`direction` 字段**（取值 = `scope.search_directions` 之一，或 `"other"` 表示搜索中发现、未归入任何声明方向）。强制机制落在 gate 而非 schema 硬校验，以兼容现有测试与自由发现：

- **`direction_tagging`**（SearchGate，BLOCKER，仅当 `scope.search_directions` 非空时启用）：每条 collected entry 必须有非空 `direction`。
- **`direction_coverage`**（SearchGate，BLOCKER，仅当 `scope.search_directions` 非空时启用）：每个声明方向须有 ≥1 条 `direction` 等于该方向的 entry。
- 分析阶段 `check_direction_coverage` 降级为 **WARN claim-anchor**：对某方向已有 collected entry 时，若该方向无 claim 引用对应来源，则 WARN（防空标签糊弄），不阻塞。

`direction` 为 agent 自赋标签（agent 本就知道每次搜索对应哪个方向），确定性强、零 LLM 判断。`"other"` 保留 ADR 0042 的自由发现空间（不窄化视野）。

## Consequences

`search_directions` 从"fallback reference（ADR 0046 的 WARN 建议）"升级为**用户声明的主契约**（硬约束），与 ADR 0042 不冲突——ADR 0042 删的是*预设*方向强制，本方案是*用户自己声明*的契约。不取代 ADR 0042。与 ADR 0050（派生 facet 安全网）正交：A（用户声明）为主契约，B（系统 facet）为安全网。schema 校验（`validate_collected`）仅做软校验（`direction` 若存在须为字符串），不硬要求，避免破坏既有 collected 构造。

Status: accepted
