# ADR 0065: Decommission info-collector skill

**Status**: Accepted

**Date**: 2026-08-05

**Supersedes**: info-collector skill (skills/info-collector/) — 整个 skill 标记为 Deprecated，保留为历史归档

## Context

info-collector 在 ~2 个月内积累 64 个 ADR、4,395 行 Python、9,752 行测试。三轮根因分析收敛到以下判断：

### 1. 永不收敛的优化 treadmill

设计定位是 "research starting point，不是 citable authority"（ADR 0028），但实际优化目标是 "零缺陷"——这是矛盾。starting point by definition 有缺陷，用户就是来 verify 的。为错误的 KPI 优化，所以永远到不了终点。

证据：同一问题在 constraint ↔ freedom 之间反复震荡——
- search_directions：ADR 0010/0017 加约束 → ADR 0042 删 → ADR 0052 重新加为 BLOCKER
- review 阻塞：ADR 0005 BLOCKER → ADR 0028 降级 advisory → ADR 0055/0056 加回 BLOCKER
- Phase 4 cleanup：ADR 0021/0026 加 → ADR 0029 删 → 检查移到 cmd_report post-step，依然在

### 2. 90% 重造轮子

与替代方案对比——
- fetcher / batch_fetch / fetch_router / fetch_strategies：重造 webfetch + exa 的轮子，Matt Pocock / omo / Anthropic 都有原生方案
- search_gate / 7 个 check：LLM 自判 + grill-me 类 skill 引导就够，gate 只拉低 throughput
- report_checks（dangling refs 等）：markdownlint 的活
- deep_dive phase：ADR 0064 自己承认 deep-research 是空壳才合并，合并后只是把空壳搬进来
- trust_boundary / repair_loop / claim_validator 的大部分：全是 AI-verifying-AI，违反 ADR 0028 的核心原则

### 3. 核心 IP 与 pipeline 强耦合，无法独立抽取

info-collector 真正有独特价值的部分是 `source_verification` 三级别（confirmed / absent / indirect）由确定性代码计算。但深入可行性分析后发现——

- 价值在**数据流端到端贯通**（结构化 claims + 关联源文件 + 数字匹配 + 标记），不在算法本身
- 算法（数字匹配 + tier 规则）很简单，但脱离结构化输入就无处发力
- 轻量级 research skill（Matt Pocock / omo ulw-research）产出非结构化 markdown，不产出 claims[] 结构
- 要让它们调用 source_verification，必须先让它们产出结构化 claims——等于重建 info-collector

**结论**：source_verification 不是独立工具，是 pipeline 的一个阶段。无法抽出来给别的 skill 用。

### 4. 替代方案已经成熟

- 轻量调研：Matt Pocock research skill
- 重量级调研：Anthropic deep-research、omo ulw-research、GitHub 开源 deep-research 生态（见 docs/references/github-deep-research-opensource.md）
- 这些方案在 info-collector 开始时可能还不成熟，现在已足够好

## Decision

退役 info-collector skill。具体处置：

1. **SKILL.md 顶部标记 Deprecated** — 给出退役理由、替代方案指向、归档位置
2. **source_verification 逻辑归档为 prompt 模板**（`references/source-verification-protocol.md`）— 零维护成本，任何 research skill 的 agent 读到就能用；牺牲确定性，但符合 starting point 定位（用户本来就要 verify）
3. **writing-guide.md 的 false depth / synthesis guard / precision rules 提炼为通用写作指南**（`docs/research/research-writing-guide.md`）— 这些是真杠杆，可以独立于 info-collector 存在
4. **整个 skill 目录原地保留为历史归档** — 不移动、不删除，ADR 链完整保留
5. **未来调研用技术方案整理到 `docs/research/research-tooling-options.md`** — 轻量 / 重量级调研的替代路径

## What is NOT preserved

- 确定性 source_verification 的代码实现（~220 行）— 放弃。理由：与结构化 claims pipeline 强耦合，独立存在无意义；prompt 模板能达到 ~70% 效果，对 starting point 定位足够
- 11 个 claim_validator check + 15 个 artifact_checks + 7 个 search_gate check + 6 个 deep_dive_gate check — 全部放弃。理由：大部分是 AI-verifying-AI 反模式，违反 ADR 0028 原则
- trust_boundary / repair_loop / deep_dive phase — 全部放弃。理由：同上

## Consequences

### Positive

- 终止永不收敛的优化 treadmill — 不再为"零缺陷 starting point"这个矛盾目标加 gate
- 释放维护负担 — 4,395 行代码 + 9,752 行测试不再需要维护
- 知识资产保留 — 64 个 ADR、writing-guide、source-verification 协议全部归档可查
- 转向更成熟的替代方案 — Anthropic deep-research / omo ulw-research / GitHub 生态

### Negative

- info-collector 用户的迁移成本 — 当前若有在用的 pipeline run，需要切换到替代方案
- 确定性 source_verification 能力丢失 — prompt 模板只是近似，不再有 100% 准确的数字匹配验证
- skill 本身的"学习价值"丢失 — 若作为 skill 设计的练手载体，归档后不再迭代

### Neutral

- ADR 链作为历史决策保留 — 未来若重新评估结构化 claims 验证，可回溯这些设计决策
- info-collector 的目录结构作为"如何不设计 research skill"的反例参考

## Lessons for future skill design

1. **定位与实施必须一致** — "starting point" 定位下不该建 quality-gated report 规模的 infrastructure
2. **AI-verifying-AI 是反模式** — 如果核心原则是"LLM 不可信"，就不该用 LLM 验证 LLM
3. **杠杆点在 prompt，不在 gate** — writing-guide 这种事前引导价值 5-10 倍于事后 gate
4. **设定退出条件** — 任何 skill 都该有"够用"标准，否则会陷入 accretion
5. **先评估替代方案** — 造轮子前先查生态是否已有成熟方案
6. **允许"删除"的肌肉** — 没有"试过 X 没用，删了"的 ADR 类型，复杂度只增不减

## References

- 根因分析对话记录：本会话
- 替代方案调研：[docs/research/research-tooling-options.md](../../../../docs/research/research-tooling-options.md)
- 通用写作指南：[docs/research/research-writing-guide.md](../../../../docs/research/research-writing-guide.md)
- source_verification prompt 模板：[references/source-verification-protocol.md](../../references/source-verification-protocol.md)
- GitHub 开源 deep-research 调研：[docs/references/github-deep-research-opensource.md](../../../../docs/references/github-deep-research-opensource.md)
- 相关 ADR：ADR 0028（重新定位为 starting point）、ADR 0029（gate philosophy shift）、ADR 0042（删除 search_plan）、ADR 0064（合并 deep-research）
