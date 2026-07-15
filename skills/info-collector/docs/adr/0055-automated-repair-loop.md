# Automated repair loop for review findings

v3 运行中 review 子代理发现 12 条问题，人工只修复了约 7 条，遗漏术语一致性、测试条件缺失、entity_number_conflict 等。review_status 最终为 degraded。根因是 review→fix→re-validate 闭环缺失：修复依赖人工逐条编辑（受限于上下文窗口和注意力），且 gate 不检查"review 发现的问题是否全部修复"。

## Decision

引入 **repair loop**：review 发现问题后，自动化修复 + 验证闭环。最多 2 轮。

### 1. Review 子代理双输出

review 子代理同时输出：
- **review_report.md** — 人类可读的 review 结果（现有格式不变）
- **fix_list.json** — 机器可消费的结构化修复指令，格式：
  ```json
  [
    {
      "issue_id": 1,
      "type": "context_twist",
      "severity": "BLOCKER",
      "section": "technical_architecture",
      "description": "Source says 'improved in narrow case X' but report presents as 'improved generally'",
      "recommendation": "Add qualifier: 'in the specific case of X'"
    }
  ]
  ```

### 2. Review-fix 子代理

读取 fix_list.json + analysis.json + collected.json + scope.json，逐条处理 review 发现，修改对应 section 的 content/claims/key_insights/tensions。输出：
- 修复后的 section 文件
- **fix_report.json** — 逐条修复状态：
  ```json
  [
    {"issue_id": 1, "status": "fixed"},
    {"issue_id": 2, "status": "skipped", "reason": "source file lacks data, cannot fix"}
  ]
  ```

### 3. 闭环验证：方案 Z

修复后不直接信任子代理自报，而是增加轻量 review 验证：

1. 检查 fix_report.json：BLOCKER 级 issue 全 fixed → 进入轻量 review
2. **轻量 review**：同一 review 子代理，prompt 限定为"只检查以下 N 个 BLOCKER 问题是否已修复"（不做全量 review）
3. 轻量 review 确认全修好 → passed
4. 仍有 BLOCKER 未修 → 第 2 轮修复
5. 2 轮耗尽仍有 BLOCKER → degraded

### 4. passed/degraded 判定标准

| 条件 | review_status |
|---|---|
| 所有 BLOCKER 级 issue 已修复 + 轻量 review 确认 | passed |
| 仍有 BLOCKER 级 issue 未修复（2 轮耗尽） | degraded |
| 只有 WARN 级 issue 未修复 | degraded（可接受） |

### 5. section 重写与 review 修复合并（3c）降级为 P2

信任边界（ADR 0053）消除结构损坏导致的重写需求，语义问题由 repair loop 处理。3c 的双目标（重写 + 修复）干扰风险真实存在，降级为 P2。

## Consequences

review 修复自动化，degraded 可升级为 passed。修复子代理调用增加 1-2 次 + 轻量 review 1-2 次，但总修复时间减少。软依赖 ADR 0053 + ADR 0054——不实施也能工作，但 section 结构损坏和 URL 不匹配会增加修复轮次消耗。不取代任何旧 ADR。

Status: accepted
