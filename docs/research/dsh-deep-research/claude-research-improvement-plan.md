# Claude Research 对照下的改进技术方案

- 状态：提案（Proposal）
- 日期：2026-08-27
- 适用版本：`dsh-deep-research` v2
- 关联：`docs/spec/dsh-deep-research.md`、`docs/adr-architecture.md`、`docs/references/methodology-comparison.md`

## 1. 摘要

`dsh-deep-research` 已具备完整的深度研究骨架：答案空间规划、分轮并行研究、三态证据、盲区侦察、综合、强制验证及有界修复环。本文将下一阶段工作收敛为五条工程主线：

1. 用可定位的结构化引用记录取代自由文本来源；
2. 按查询复杂度分配代理、工具与时间预算；
3. 以持久检查点支持恢复、重试和故障诊断；
4. 用来源去重、来源多样性和冲突图提高多源证据的独立性；
5. 建立真实 Web 端到端评测与质量发布门禁。

目标不是复制 Claude 的闭源实现，而是保留本项目的可审计研究机制，同时补齐引用可验证性、生产可靠性和质量度量。

## 2. 背景与现状

### 2.1 Claude Research 可借鉴的工程原则

Anthropic 对其 Research 系统描述为 orchestrator-worker 架构：LeadResearcher 规划并并行委派研究任务，子代理独立搜索和归纳，Lead 决定是否继续研究，最后交给 CitationAgent 将报告声明与文档支撑位置对齐。该架构强调动态研究循环，而不是静态一次检索。

可迁移的原则如下：

- **按复杂度伸缩 effort**：简单问题少派代理，复杂开放问题增加并行度和工具预算；
- **声明级引用核验**：核验“来源是否支撑具体表述”，而不只判断链接是否相关；
- **外部化长程状态**：保存计划和阶段性结果，避免上下文截断或任务中断后从头开始；
- **评测驱动迭代**：同时衡量事实正确性、引用支撑性、覆盖度、来源质量和工具效率；
- **可观测与可恢复**：记录工具失败、决策路径和检查点，支持诊断与继续执行。

### 2.2 当前实现的基础

当前静态 workflow 已实现以下能力：

- Planner 输出 `scope`、`dimensions`、带关键词和验收标准的 `questions` 及 `coverage_gaps`；
- Researcher 以 `confirmed / uncertain / gaps` 三态返回证据，并将高优缺口排入下一轮；
- 研究按 `min(maxParallel, maxItemsPerCall)` 切片，受 `depth + 1` 轮次与单代理预算限制；
- Synthesizer 仅消费结构化证据精简副本；Verifier 将承重声明分类为 `verified / unverified / refuted`，并驱动有限修订；
- 宿主在 run 结算后落盘计划、轮次证据、盲区、报告、验证与审查产物。

因此，改进重点应放在证据数据模型、运行时控制和质量闭环，而不是增加无明确职责的新角色。

## 3. 目标、非目标与设计原则

### 3.1 目标

| 编号 | 目标 | 成功标准 |
| --- | --- | --- |
| G1 | 让每个承重声明可机器核验 | 报告承重声明均有 `claimId`，且能关联一个或多个可定位引用 |
| G2 | 让成本与复杂度相匹配 | 每次 run 在开始前产生预算计划，执行中记录实际消耗与降级原因 |
| G3 | 让长任务可恢复 | 中断后可从最近完成轮次恢复，不重复已成功的研究项 |
| G4 | 让“多源”代表独立证据 | 同源转载不重复计数，报告能呈现来源集中度与冲突 |
| G5 | 让质量改进可量化 | 建立真实 Web 评测集、离线回归和发布阈值 |

### 3.2 非目标

- 不改变 `deep_research` 作为唯一对外工具入口；
- 不要求 workflow 沙箱直接获得文件系统能力；
- 不承诺对付费墙、登录态、私有数据源做通用抓取；
- 不以“更多 agent”本身作为质量目标。

### 3.3 设计原则

1. **证据先于文笔**：报告中的事实必须可回溯至结构化证据。
2. **不确定性显式化**：无法访问、无法定位、来源冲突均进入状态与报告，不静默忽略。
3. **预算是运行时契约**：代理数、工具调用、时长和证据规模均可观察、可限制。
4. **渐进增强**：新 schema 必须兼容旧 run 产物读取，并允许分阶段启用。
5. **可靠性优于表面完成**：恢复失败或验证不可用时诚实交付降级状态。

## 4. 目标架构

```text
请求
  │
  ├─ Intake / Complexity Router ──► budget plan
  │
  ├─ Planner ──► plan + dimensions + acceptance + coverage gaps
  │
  ├─ Research rounds ──► Evidence Store ──► Source Registry
  │                         │                    │
  │                         └─ checkpoint ◄──────┘
  │
  ├─ Dimension synthesis ──► claim graph ──► report synthesis
  │
  ├─ Citation audit ──► claim-level verification ──► bounded revision
  │
  └─ artifacts + metrics + evaluation trace
```

其中 `Evidence Store`、`Source Registry`、checkpoint 和 artifacts 均由宿主侧实现；workflow 脚本只消费所需的结构化快照和指针，从而保持 VM 沙箱边界不变。

## 5. 工作流 A：结构化引用与声明级验证（P0）

### 5.1 问题

现有 `confirmed` 证据仅包含 `claim`、`source` 和 `confidence`。`source` 是自由文本，因此无法稳定完成 URL 去重、原文定位、来源类型识别、访问时间记录及“此来源是否真的支持此表述”的审计。

### 5.2 数据模型

新增版本化证据 schema。所有字段均为 JSON 可序列化数据。

```ts
type SourceTier = 'primary' | 'authoritative' | 'secondary' | 'low'
type SupportRelation = 'supports' | 'contradicts' | 'mentions'

interface CitationRecord {
  citationId: string
  url: string
  canonicalUrl?: string
  title?: string
  publisher?: string
  publishedAt?: string
  accessedAt: string
  locator?: string                 // 段落、章节、页码、表格或时间戳
  supportingQuote?: string         // 最小必要摘录，不保存整页内容
  sourceTier: SourceTier
  retrievalStatus: 'fetched' | 'unreachable' | 'blocked' | 'partial'
  contentHash?: string
}

interface ClaimRecord {
  claimId: string
  text: string
  dimension: string
  confidence: 'high' | 'medium' | 'low'
  citations: Array<{
    citationId: string
    relation: SupportRelation
    note?: string
  }>
  status: 'confirmed' | 'uncertain' | 'refuted'
}
```

### 5.3 流程

1. Researcher 对每条 confirmed claim 产出最少一个 `CitationRecord`；无法提供 URL 或定位时，默认降入 `uncertain`。
2. 宿主规范化 URL、计算 canonical URL 和内容 hash，并写入 `Source Registry`。
3. Synthesizer 只接收 `ClaimRecord`、必要引用元数据和冲突摘要；报告使用 `claimId` 关联引用。
4. 新增 `citation-audit` 阶段：逐个抽查报告承重 claim，验证页面可达性、定位存在性和 claim-support 关系。
5. Verifier 保留覆盖度、过度自信与修订决策职责；Citation audit 专注来源支撑，避免单一 prompt 承担两种任务。

### 5.4 兼容与降级

- 为现有 `source: string` 增加适配器：若字符串为 URL，则生成 `CitationRecord`；否则标记 `partial` 并将 claim 置为 `unverified`。
- 旧产物保持可读；新产物在根部加 `schemaVersion: 2`。
- 没有 `web_fetch` 时，audit 不得生成 `verified`，只能输出 `unverified` 及原因。

### 5.5 验收指标

- `citation_coverage = 有至少一条可定位引用的承重 claim / 承重 claim 总数`；
- `support_precision = audit 判定 supports 的引用 / 被抽查引用`；
- `primary_source_ratio = primary citations / 全部 citations`；
- 高风险主题默认要求 `citation_coverage >= 0.95`，否则报告显式降级。

## 6. 工作流 B：复杂度路由与全局预算（P0）

### 6.1 问题

当前 `depth`、`maxParallel` 和 `searchBudget` 已可约束执行，但主要来自固定配置或调用参数；系统缺少对“这个问题是否值得启动完整深度研究”的显式判断，也没有贯穿整次 run 的成本账本。

### 6.2 Intake Router

在 Planner 之前运行低成本 Router，输出：

```ts
interface BudgetPlan {
  mode: 'quick_fact' | 'comparison' | 'investigation' | 'report'
  risk: 'normal' | 'high'
  maxAgents: number
  maxToolCalls: number
  maxRounds: number
  maxWallTimeMs: number
  minimumSourceTiers: SourceTier[]
  requireCitationAudit: boolean
  rationale: string[]
}
```

建议初始策略：

| 模式 | 适用情形 | agents | 单代理工具调用 | 验证 |
| --- | --- | ---: | ---: | --- |
| `quick_fact` | 单一、低风险事实 | 1 | 3–10 | 可选轻量 |
| `comparison` | 少量对象对比 | 2–4 | 10–15 | 抽查关键差异 |
| `investigation` | 多维、时效或争议问题 | 4–8 | 15–20 | 强制 citation audit |
| `report` | 高价值研究报告 | 6–12 | 按总预算分配 | 强制审计 + 审查 |

高风险（医疗、法律、金融、监管）自动提升一手来源要求、引用覆盖率阈值和 verifier 抽样比例。

### 6.3 预算账本与调度

宿主维护 `RunBudgetLedger`：

- 已创建/已完成 agents；
- 每代理工具调用、耗时、失败类型；
- 每轮新增独立 claim、来源和覆盖维度；
- 剩余总预算与取消原因。

调度规则：

1. 不在启动时耗尽 agents；预留至少 20% 给高价值 follow-up 与引用核验。
2. 达到预算时，优先完成已启动任务、citation audit 和高风险维度，而不是派发新宽度任务。
3. 若两轮连续没有新增独立高质量来源或覆盖增量，提前收敛。
4. 每次预算拒绝均写入 artifacts，以便报告解释未研究部分。

### 6.4 验收指标

- 95% 的 run 具有完整 `BudgetPlan` 和账本；
- 简单查询的中位工具调用数下降，同时质量 rubric 不回退；
- 达到预算的 run 都有机器可读的未完成原因；
- 超出 `maxAgents`、`maxToolCalls` 或时间预算的次数为零。

## 7. 工作流 C：检查点、恢复与可观测性（P1）

### 7.1 问题

产物最终会落盘，但长任务若在中途取消、进程重启或工具反复失败，已完成的研究轮次无法作为正式恢复点复用。

### 7.2 Checkpoint 设计

在每个完成阶段以及每个研究轮次结束后，宿主原子写入：

```json
{
  "schemaVersion": 1,
  "runId": "...",
  "phase": "research",
  "completedRounds": 2,
  "plan": {},
  "pending": [],
  "itemRecords": [],
  "sourceRegistryRef": "sources.json",
  "budgetLedger": {},
  "attempts": {},
  "createdAt": "..."
}
```

规则：

- 使用临时文件写入后 rename，避免半写入 checkpoint；
- 每项研究任务以稳定 `itemId` 和输入 hash 标识，恢复时仅重跑失败/失效项；
- 记录工具错误类别：超时、限流、403、404、解析失败、模型结构化输出失败；
- 允许显式 `resumeRunId`，并校验配置、脚本和 schema 的兼容性；
- 不将取消视为成功：恢复后的报告须标记哪些内容来自旧 checkpoint、哪些是本次新取证。

### 7.3 可观测性

新增无敏感正文的事件指标：

- `research/item_started`、`research/item_finished`、`research/item_failed`；
- `source/fetched`、`source/blocked`、`source/duplicate`；
- `claim/created`、`claim/audited`、`claim/refuted`；
- `budget/consumed`、`budget/exhausted`；
- `checkpoint/written`、`run/resumed`。

### 7.4 验收指标

- 模拟中断后，恢复 run 不重复执行已成功 item；
- checkpoint 损坏时安全回退到上一个有效版本；
- 每类失败均在 artifacts 和汇总指标中可见；
- 恢复后的报告可完整追溯到原始与新增证据。

## 8. 工作流 D：来源独立性、去重与冲突图（P1）

### 8.1 问题

多个网页可能引用同一新闻稿、公告或数据库。若只按 URL 数量计算来源，容易得到“多源但同源”的伪交叉验证；当前问题去重也主要发生在研究任务文本层面。

### 8.2 Source Registry

宿主维护来源注册表：

- URL 规范化：去除追踪参数、处理 canonical URL；
- 内容 hash：相同正文或高度相似转载合并；
- `originId`：尽可能识别最初公告、论文、数据集或采访；
- 主题、语言、出版时间、来源 tier 和可访问状态；
- 被哪些 `claimId` 使用。

### 8.3 Claim Graph

对每条声明构建边：

```text
Claim ──supports────► Citation
Claim ──contradicts─► Citation
Citation ──derives-from─► Origin
```

综合规则：

1. 同一 `originId` 的多篇转载只计为一个独立支持来源。
2. 存在高质量冲突证据时，报告必须并列呈现，不得只选择支持当前结论的来源。
3. 单一来源承重结论降低 confidence，并在报告中标记“单源”。
4. 按领域设置来源多样性目标，例如监管事实优先官方公告、学术结论优先原论文/数据集。

### 8.4 验收指标

- 每个 claim 可计算 `independentSourceCount`；
- 报告展示单源、高度集中和冲突未解的关键结论；
- 转载样本中，同一 origin 的重复计数接近零；
- 新增 source diversity 不应显著降低 citation support precision。

## 9. 工作流 E：分层综合与上下文控制（P1）

### 9.1 问题

当前已经对证据做精简，但所有轮次的 `evidenceState` 仍会整体送入 Synthesizer 和 Verifier。深度研究在多轮、多维度时，最终阶段仍可能成为上下文瓶颈。

### 9.2 方案

1. 研究结束后，按 dimension 构建 `EvidenceCard`：已验证 claim、冲突、待验证项、关键 citations 和覆盖率。
2. 先进行维度级综合与局部审计，生成简短的 `DimensionBrief`。
3. 最终 Synthesizer 仅消费 `DimensionBrief` 与必要 claim/citation 指针；需要细节时按 ID 拉取。
4. Citation audit 针对最终报告的承重 claim 做选择性验证，不重读全部原始证据。
5. 表格、时间线和数值证据保留为 JSON/CSV 工件，报告引用工件 ID 而不是复制大段内容。

### 9.3 验收指标

- 最终综合输入 token 量相对全量证据输入显著下降；
- 维度覆盖率与 citation coverage 不降低；
- 报告中每个关键结论仍能回溯到原始 `ClaimRecord` 与 `CitationRecord`。

## 10. 工作流 F：真实质量评测与发布门禁（P2）

### 10.1 评测分层

| 层级 | 内容 | 目的 |
| --- | --- | --- |
| 单元/脚本回归 | schema、队列、切片、恢复、预算、审计状态机 | 保证编排正确性 |
| 受控 Web 集 | 可稳定访问的权威网页和已知答案 | 衡量事实与引用准确性 |
| 开放研究 rubric 集 | 开放主题，由人工与 LLM judge 打分 | 衡量覆盖、来源质量和表达 |
| 对抗集 | 转载链、过期页面、404、付费墙、SEO 内容、冲突来源 | 衡量诚实降级与鲁棒性 |

### 10.2 评分 rubric

- factual accuracy；
- citation support precision；
- citation coverage；
- dimension coverage；
- primary-source ratio；
- uncertainty honesty；
- source diversity；
- 工具调用、时延和 token/成本效率。

### 10.3 发布门禁

任何改动 `src/script.ts`、角色提示词、证据 schema、工具描述或模型路由时：

1. 运行既有 VM 回归与 smoke；
2. 运行受控 Web 集；
3. 与基线比较 rubric 指标；
4. 若 citation support、覆盖度或不确定性诚实度超过允许回退阈值，则阻止发布；
5. 由人工抽检高风险样本和失败样本。

## 11. 交付计划

### 阶段 1：引用基础（2–3 个迭代）

- 定义 `CitationRecord`、`ClaimRecord` 和 schema version；
- 实现 URL 规范化及 Source Registry；
- 新增 citation audit prompt、产物和基础回归；
- 报告支持 claim ID 与引用定位。

### 阶段 2：运行时治理（2 个迭代）

- 实现 Intake Router、`BudgetPlan` 与账本；
- 在 workflow 参数中透传预算计划；
- 加入预算事件、提前收敛与未完成说明。

### 阶段 3：可靠性与规模（2–3 个迭代）

- 实现阶段/轮次 checkpoint、恢复和幂等 item；
- 实现失败分类、retry policy 与 source cache；
- 实现去重、origin 推断和 claim graph；
- 引入分维度 EvidenceCard/DimensionBrief 综合。

### 阶段 4：评测与门禁（持续）

- 构建受控 Web 集和对抗集；
- 接入 rubric judge、人工抽检与指标面板；
- 将关键阈值接入 CI/发布流程。

## 12. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| schema 变复杂导致子代理结构化输出失败 | 分版本适配、严格 JSON schema、失败降为 uncertain、回归覆盖 |
| citation audit 成本过高 | 只审计承重 claim；按风险与置信度分层抽样；缓存已抓取内容 |
| canonical/origin 判断误合并 | 保留原 URL 列表与合并理由；允许 audit 拆分；对高风险来源人工抽检 |
| checkpoint 含敏感研究数据 | 复用 workspace 权限边界；最小化落盘原文；提供清理策略 |
| 复杂度路由误判 | 允许用户覆盖 depth/预算；记录路由理由；将误判样本加入 eval 集 |
| LLM judge 自身不稳定 | 使用固定 rubric、多次采样/校准、与人工判定对照，不将单一 judge 作为唯一真值 |

## 13. 完成定义

当以下条件同时满足时，本提案可视为完成：

1. 承重声明以 claim ID 和结构化 citation 交付，且可生成覆盖率与支撑率；
2. 每次 run 均有可观察的复杂度、预算和消耗记录；
3. 研究可从安全 checkpoint 恢复，且不会重复已完成的工作；
4. 来源注册表可识别 URL 重复与主要同源转载，并在报告中显示关键冲突；
5. 存在真实 Web 与对抗性评测，关键质量指标成为发布门禁；
6. 所有新行为具备 VM 回归、宿主桥测试与降级语义测试。

## 14. 参考材料

- Anthropic，《How we built our multi-agent research system》存档：`docs/references/anthropic/multi-agent-research-system.md`；
- Claude 与 dsh 方法论对照：`docs/references/methodology-comparison.md`；
- 当前产品规格：`docs/spec/dsh-deep-research.md`；
- 当前架构决策：`docs/adr-architecture.md`；
- 当前脚本与测试计划：`src/script.ts`、`docs/test-plan.md`。
