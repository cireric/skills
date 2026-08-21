# ADR-0001: 复盘工作流与账本闭合的精化决策

**Status:** Accepted
**Date:** 2026-08-19
**Supersedes:** none（本 skill 首份 ADR；记录一次 grill 再审的不可逆决策，不取代任何既有决策）

## Context

`charlie-munger-review` 已实现一版「决策复盘 postmortem」（结果已显现才复盘）。一次 /grill-me 再审 session 对其工作流、判断框架、分析规则逐条重验，产出一组要落地到 `SKILL.md` + 4 个 `references/*.md` + `config.json` 的精化决策。本 ADR 固化为不可逆快照，防止后续改动悄然翻案。

## Decisions

1. **穷尽扫描 / 分层呈现 / 预算 grill 三层切分**（并发约束与「穷尽决策树」诉求的和解）
   - 穷尽 = **内部判定层**：agent 必过 24+2 偏误 × 20 模型 × 反演死法，不许为省 token 跳过任何一项；「扫过但排除」记 `biases_screened_out`，使穷尽可审计。
   - 分层 = **对外呈现层**：默认只铺核心集（`scan_scope` 控制），边缘项收纳「按需展开」区。
   - 预算 = **交互 grill 层**：Phase 2b + 3 全程问题上限 = `max_total_questions`，足够信号即早停。
2. **未走路径枚举入 Phase 1**：收集时新增第 4 问「决策树岔口枚举」，穷尽 counterfactual 分支，落盘 `paths_not_taken`（survivorship-bias / second-order-thinking 的结构化强制执行）。
3. **未决分歧闭环**：Phase 3 反假设对抗「第 2 次坚持 + 理由」收手时，把未定归因分歧落盘 `unresolved_disagreements`；Phase 0 读回作待验假设（与 `lessons` 同权重闭环），`history` 命令同时列出未决清单。
4. **对冲偏误 = lollapalooza 的镜像信号**：异向 ≥2 条偏误命中不计 lollapalooza，改标 `opposing_biases`（两个方向同时拉你 = 内耗强信号）。
5. **核心/边缘分层切法**（config 可调，非硬编码）：偏误核心 13 + 元偏误 2、边缘 11；模型核心 5、边缘 15。
6. **模型补视角挑法**：Phase 2c 挑 1-2 个最相关学科模型 + 1 个最不相关学科模型（相关压主因，陌生照盲区）。
7. **反假设对抗替代假设来源**：5 对相关性 seed 表优先，表外按「同族 → 邻近 → 必检 2 条」生成规则兜底。
8. **安全协议边界样例**：情绪低落（去毒舌保留追问）vs 危机信号（停止角色转交）各给明确触发样例，宁可误判降级不可漏判。
9. **config 新增**：`max_total_questions`（默认 20）、`scan_scope`（默认 `"core"`）。
10. **维持项**：severity 三档「去掉偏误后决策是否反转」、教训格式「当 X 信号时做 Y 而非 Z」、「结果已显现」判定 + 长期尾效应分档、grill L1→L2→L3、24 条偏误保真、2 条元偏误、必检 2 条（能力圈 + 反演）——均维持不改。

## Rationale

- 三层切分使「穷尽决策树」与「预算早停」从互斥变为互补：穷尽思考、选择性追问，两者各有落点，审计靠 `biases_screened_out`。
- 未走路径与未决分歧都服务于「账本长期对账」这一差异化卖点（固定框架 + 累积账本），把一次性 grill 升级为跨次校验。
- 对冲偏误补足了 lollapalooza「只记同向、丢弃异向」的盲区，避免一半诊断价值流失。
- 分层 + 生成规则分别解决「全量随取贵且稀释注意力」与「固定表赶不上组合数」两个可复现性短板。

## Deferred

- **闭环缺口（Q1=C，未落地）**：事前评审半场（决策日志 + 反演清单 + 事后对账触发）另立专题，本次只验复盘半场。
- **influence-association**：暂列边缘，营销/推荐场景高发，留观察后议是否升核心。
- **OBSERVABLE_SKILLS 注册**：三维度评估 3/3 全高、应加入，但集合定义在 plugin 层、不在本仓库；此处仅记录待办。
- **docs/adr / tests / CONTEXT.md 补齐**：本 ADR 之外的结构化补齐（tests 对纯 prompt skill 暂不适用）另议。