# Deep Research 技术研究总纲：原理批判 · 工程价值甄别 · DSH 插件可行性

> 状态：蒸馏版（Supersedes 三份输入文档成为权威综合视图）
> 日期：2026-08-27
>
> **本文是什么**：把下列三份文档蒸馏为一份高价值技术研究文档，回答三个问题——① Claude Deep Research 的原理经得起怎样的批判性审视？② 其中哪些工程设计价值是 `dsh-deep-research` 应当吸收的？③ 这些经验在 DSH 插件形态下落地的可行性如何？
>
> **输入清单（各自角色）**：
> | 输入 | 角色 |
> | --- | --- |
> | `claude-deep-research-principles.md` | 原理抽象层：将 Claude Research 抽象为 Agent Operating Pattern（11 条编号原理 + 7 条可迁移原则），并提供事实边界警示 |
> | `claude-research-improvement-plan.md` | 改进提案层：六条工作流（A 结构化引用 / B 复杂度路由与预算 / C 检查点恢复 / D 来源独立性 / E 分层综合 / F 评测门禁）及数据模型 |
> | `_archive/claude-research-analysis.md` | 平台对照层（已归档）：Claude 机制 → DSH 设施映射表 + 平台前提条件 |
>
> **证据基座**（critical 分析与可行性判断的事实来源，均在本仓库内核验过）：
> - Anthropic 官方工程博客存档：`dsh-deep-research/docs/references/anthropic/multi-agent-research-system.md`
> - Cookbook 双提示词存档：`dsh-deep-research/docs/references/anthropic/research_lead_agent.md`、`research_subagent.md`
> - CHANGELOG（含 verifier 误报缺陷史）：`dsh-deep-research/docs/references/anthropic/claude-code-CHANGELOG-full.md`
> - 平台接缝逐条核验（文件：行号级）：`dsh-deep-research/docs/references/platform-seam-verification.md`
> - 方法论对比（v1→v2 设计出处）：`dsh-deep-research/docs/references/methodology-comparison.md`
> - 实现：`dsh-deep-research/src/`（23 用例 vm 回归测试本机复跑通过）

---

# 第一部分 原理批判：Claude Deep Research 的真实成色

## 1.1 经得起批判的内核

先承认站得住的部分，再动手拆。以下三条是这个架构真正的贡献，质疑不动摇：

1. **Retrieval ≠ Investigation**。传统搜索/RAG 从已知知识库里取相关内容；Deep Research 在开放世界中主动探索未知、并根据新信息改路径。这个范式区分本身成立，也与官方「multi-step search dynamically finds relevant information」的自述一致。
2. **上下文分区（Context Partitioning）是多代理的第二重身份**。Multi-agent 不只是并行计算模型，也是 Context Scaling 模型——每个子代理在自己的局部上下文深挖、只回传压缩后的 findings，这是对抗上下文溢出与信息稀释的结构性手段。「搜索的本质是压缩」这句官方论断把架构选择提到了第一原理高度。
3. **八环闭环节拍器通用有效**：Understand → Decompose → Delegate → Explore → Observe → Evaluate → Re-plan → Synthesize → Verify。它与 AI-SDLC 同构，可作为一切长程 agent 系统的节拍参考。

## 1.2 七条批判性审查

### C1 效果归因混杂：「架构的胜利」有多少其实是「预算的胜利」

官方内部评测称多代理比单 Opus 高 90.2%，但同时公开另一组数据：BrowseComp 评测中**仅 token 用量一项就解释 80% 的性能方差**，其余两个解释变量是工具调用次数与模型选择。这两组数字放在一起构成对自我叙事的反驳——多代理系统很大程度上是**一种把 token 预算可并行地花出去的方式**，而非独立的智能增益。缺失的关键对照实验是「同等 token 总预算的单代理」基线。

**工程含义**：做任何 deep-research 实现时，必须先把成本治理做成一等公民（见第三部分工作流 B），否则你交付的不是架构优势，而是一台不确定回报的烧钱机器。

### C2 同步编排的结构性瓶颈——官方亲口承认

Lead 以同步方式等待整批子代理返回：不能中途纠偏、子代理之间不能协作、整个系统被最慢的一个卡住。官方博客原文把异步执行列为未来方向。这意味着该架构**天然放弃了流式中控**这一类高级形态；凡宣称「动态适应」者，适应粒度只是批次之间，不是任务之中。

**工程含义**：不要试图在同步引擎上模仿假异步；正确的对策是把控制权收回放在轮间边界（dsh 的 gap 队列跨轮续研正是如此），并用末端分层综合缓解长尾。

### C3 「嵌入式伸缩规则」是脆弱启发式，且有失控前科

Anthropic 自述早期失效模式：简单查询开出 50 个子代理、对不存在的来源无限搜索、子代理重复同一方向。这些不是边缘案例，而是把努力度决策交给模型自发判断的必然代价——**模型不能可靠地自评努力度**。修补手段是把缩放规则写进提示词，但提示词规则（简单题 1 代理/比较题 2–4/复杂题 10+）依然是无强制力的软约定。同源的衍生缺陷：人类测试发现子代理系统性偏好 SEO 内容农场胜过学术 PDF——提示词加了一句「prioritize peer-reviewed sources」，但对治结构性偏置靠的是一句提示词吗？

**工程含义**：伸缩应当从「提示词里的礼貌请求」升级为「运行时契约」（显式 BudgetPlan + 硬限额），来源质量应从「提示词偏好」升级为「结构化注册表 + 分层计量」。这正是第三部分 B 与 D 的立项理由。

### C4 引用 ≠ 正确：CitationAgent 解决的是归因，不是支撑精度

CitationAgent 把 claim 映射回来源，产出可点击链接——但它验证的是「这条链接被引过」，弱判定才是关键：「页面内容是否真的支持该表述」。第三方文章估测错配率 5–10%（此数字本身低置信，见 C7），且官方产品从未承诺消除。结论是一个概率问题而非布尔问题：**任何「已验证」标签都必须以机器实际核验过的范围来定义**（例如：页面可达 + 定位摘录存在 + 判定 supports），超出这个范围声称 verified 就是过度承诺。CHANGELOG 里 verifier 曾有「误报 all claims refuted」的真实缺陷史（L1208），进一步证明验证子系统自身也需要边界与降级语义。

**工程含义**：引用核验要拆成两个独立职责——支撑审计（supports/contradicts/mentions 判定）与覆盖度决策（哪些 claim 需要复核），避免单一 prompt 身兼两职互相污染（第三部分 A 的设计原则之一）。

### C5 压缩链的信息损耗：把「传话游戏」搬到多代理里

研究过程是一棵层层压缩的信息树：网页 → 子代理摘要 → lead 综合 → 报告。每一跳都在丢弃细节，而官方也承认直连搬运会产生「game of telephone」损耗——其对策是让子代理产物直接写入文件系统、只回传轻量指针。但这只解决了「多一跳转述」的问题，没有解决「压缩目标函数不对齐」的问题：子代理不知道最终报告需要哪一层粒度的细节，过早压缩丢失的证据在末端无法复原。

**工程含义**：原始证据与压缩产物要双轨保存（dsh 的 per-round 证据落盘正是这个思路），末端综合阶段允许按 ID 回拉细粒度材料，而不是只吃压缩副本（第三部分 E）。

### C6 评测问题是「房间里的大象」

多代理路径不确定性导致传统断言式测试失效，官方转向 LLM-as-judge + rubric + 人工兜底。诚实的评价是：LLM judge 可扩展但需要校准（多次采样、与人判对照），它把评测难题转换成了元评测难题。真正拉开工程成熟度差距的不是编排代码，而是**评测集与发布门禁**——这方面所有实现都还在半山腰。

**工程含义**：质量闭环必须是路线图的一等部分（第三部分 F），起步规模可以很小（官方也是从约 20 个查询起步）。

### C7 证据可信度需要分层：一手事实与营销噪声必须分开采信

关于 Claude Research 的三类叙述可信度不同：

| 层级 | 内容举例 | 采信策略 |
| --- | --- | --- |
| 高可信 | 官方博客中的自曝型数据：15× token、同步瓶颈、SEO 偏置、token=80% 方差 | 直接作为设计输入（自曝不利信息的组织更有可能说实话） |
| 中可信 | 90.2% 内部评测、BrowseComp 归因分析 | 引用时注明「内部评测、基线与评测集未公开」 |
| 低可信 | 第三方文章的产品快照：3–15 分钟时长、配额数、模式命名、5–10% 错配率、套餐价格 | 仅作场景佐证，不作工程依据——版本迭代会使其迅速过期 |

principles 文档 §29.3 给出的提醒（稳定的架构原则 ≠ 当前版本的产品实现细节）应当升格为硬纪律：**凡是随产品版本漂移的字段，一律不许进入设计约束**。

## 1.3 批判后的重新定义

- Deep Research **是**：一个用可并行的算力扩容换取覆盖率的长程调查系统；一套把「拆解→并行→循环→压缩→验证」制度化的操作系统骨架。
- 它**不是**：正确性保证器（Multi-Agent 是放大器，放大好的检索也放大坏的偏差）；RAG 的替代品（适用域不同）；便宜的解决方案（15× 成本决定了它只为高价值任务开工）。
- 它的**适用边界**（官方与第三方一致确认）：广度优先、多独立方向、可交叉验证的任务受益最大；快速事实、编码协作、实时行情、强主观判断四类场景明确不该用。

---

# 第二部分 价值甄别：dsh-deep-research 吸收什么、放弃什么

## 2.1 现状盘点：已吸收且局部超越的价值（保持不动）

| # | Claude 价值 | dsh-deep-research v2 现状 | 判定 |
| --- | --- | --- | --- |
| 1 | Problem Decomposition | 答案空间规划：scope + dimensions + 关键词 + **验收标准**——比 Claude 的临场拆解多了前置的「什么样的证据算回答」定义 | ✅ 已超越，保持 |
| 2 | Parallel Exploration | `parallel()` 切片并发（受 ITEM_CAP 硬上限保护）、跨轮续研不丢队列 | ✅ 已吸收，保持 |
| 3 | Independent Context | 每个 `agent()` 独立上下文 + 只回传三态证据（confirmed/uncertain/gaps） | ✅ 已吸收，保持 |
| 4 | Memory 外置防截断 | 宿主侧七类产物落盘 + 指针交付，正文不进对话 | ✅ 已吸收（且更早落实了官方附录的 filesystem-handoff 建议），保持 |
| 5 | Effort Scaling（参数面） | depth 三档 + LIMIT(depth) 每代理预算 + maxParallel/maxTotalAgents 封顶 | ✅ 参数面已具备（自动面缺口见下） |

## 2.2 真正的缺口：值得吸收的五项（对应改进方案 A/B/C/D/E/F）

| 缺口 | Claude 侧依据 | 我们的差距 | 吸收判定 |
| --- | --- | --- | --- |
| **G-A 声明级结构化引用** | CitationAgent 架构级闸门 | 三态证据有了，但 `source` 是自由文本字符串——URL 无规范形、无定位锚、无抓取状态，「是否真支撑此表述」无法机器审计 | ⭐ 最高价值：这是从「有引用感」到「可审计引用」的分水岭 |
| **G-B 复杂度路由 + 预算契约** | 官方缩放规则 + quota 产品实践 | depth 靠调用方给定，没有「这个问题值不值得开满火力」的低成本前置判断，也没有贯穿 run 的成本账本 | ⭐ 最高性价比：直接攻击 C1/C3 两处批判点（烧钱墙 + 启发式失控） |
| **G-C 检查点与恢复** | 官方「错误后从断点恢复而非从头重来」生产原则 | 产物只在 run 结算后落盘；长任务中途取消/崩溃后已完成轮次作废 | 高价值：后台长任务的旗舰场景恰恰最怕半途作废 |
| **G-D 来源独立性与冲突呈现** | 官方来源质量教训 + 多源验证卖点 | 仅有提示词级 A/B/C/D 分级；无 URL 去重、无同源转载合并、无冲突并列结构——「多源」可能是伪交叉验证 | 高价值：把「多源」变成计量的对象而不是修辞 |
| **G-E 分层综合 / 末端上下文治理** | 官方 game-of-telephone 对策的延伸 | 所有轮次的全量证据仍整体送进 Synthesizer/Verifier，多维多轮时末端必然成为瓶颈 | 中价值：机械改动小、收益可直接测量 |

（F 真实 Web 评测门禁同样值得吸收，但其性质是**持续运营投入**而非单次工程设计，放入第三部分单独讨论。）

## 2.3 有意不吸收的四项（记录为边界，不记为欠账）

1. **完全开放式 re-planning**。Claude 允许 lead 临场改写整个研究方向；我们刻意收敛为「结构化 gap 队列 + 轮次上界 + 边际增益零即停」。代价：牺牲了「发现公司 A 其实属于集团 B」式的意外转折捕获能力。换来：整套编排逻辑是静态脚本，可整段进 vm 回归、成本有硬上界、失败模式可枚举。这是一笔**已结算的交易**，报告里如实标注此边界即可。
2. **Extended thinking 显式控制**。引擎 `agent()` 仅支持 `label/phase/schema/provider/model`，thinking/effort/isolation 一律抛 `UNSUPPORTED_OPTION`——平台不可达，维持提示词层 OODA 纪律。
3. **MCP 工具自适应 / tool-testing agent**。属于宿主生态运维能力，插件不越权接管。
4. **企业内部源接入（Google Workspace 式）**。取决于组合级工具世界，属部署配置而非插件代码范围。

同时明确反向输出：dsh 侧有一批 Claude 原生不具备的设计——验收标准先行、盲区显式化与定向侦察、EIG 边际增益收敛、三态证据纪律、五角色模型成本分层、静态脚本可回归性、诚实降级交付。本次改进不是单向移植，而是**双向流动后的合流**。

---

# 第三部分 平台可行性：六项工程经验在 DSH 插件上的落地分析

## 3.0 平台事实基座（全部已在 `platform-seam-verification.md` 核验，11 项假设 10 成立 / 1 修正）

与可行性直接相关的七条硬约束：

1. workflow 脚本沙箱仅暴露 `agent/parallel/pipeline/phase/log/args` 六个全局——**无 fs、无网络、无 crypto**；
2. `agent()` 选项仅五项，budget/thinking 类选项不存在——**预算只能走 args 与提示词**；
3. 单次 `parallel()/pipeline()` 有 `maxItemsPerCall`(默认4096) 硬上限，超限致命 ITEM_CAP；
4. 引擎原生发出六个 Cordis 事件（`workflow/start|phase|log|agent-start|agent-end|end`）——**宿主可在运行中感知进度**；
5. 后台 job 终态只有 `completed|killed|failed`（无 cancelled），完成通知由 tool-jobs 投递归属会话；
6. 子代理默认继承父组合完整工具注册表——`tool-web` 加载即有 `web_search/web_fetch`；
7. schema 仅支持 JSON Schema 子集，嵌套 object 必须显式 `additionalProperties:false`（类型层编译约束）。

一个反复出现的设计铁律由此推出：**「脚本做调度，宿主做基础设施」**——一切涉及 fs/hash/网络规范化的事，归宿主进程；脚本内只有纯计算与 LLM 编排。

## 3.1 工作流 A：声明级结构化引用与引用审计（P0）——可行性 ★★★★☆

**机制**：`RESEARCHER_SCHEMA.confirmed[]` 升级为携带 `CitationRecord`（url/title/publishedAt/accessedAt/locator/supportingQuote/sourceTier/retrievalStatus），Synthesizer 只消费 `ClaimRecord` 及引用指针；新增 citation-audit 阶段独立于 verifier（verifier 保留覆盖度与修订决策职责）。

**平台吻合度**：
- CitationRecord 字段全为基本类型 + 字符串枚举，schema 子集完全容纳——只需牢记嵌套对象补 `additionalProperties:false`；
- 引用审计 = audit 子代理持 `web_fetch` 抽查可达性 + 定位存在性 + supports 判定——子代理默认继承全局工具世界（事实 6），常见部署天然可用；
- 降级语义已预演过：verifier 带 fetch 才允许 verified，不带则退化为弱校验 + `unverified` 标注（B1 双态兼容模式原样复用）。

**关键取舍（诚实声明）**：
- 运行中（in-run）去重只能做**语法级**规范化（小写 host、剔除追踪参数等纯字符串运算，vm 内可行）；重定向跟随与内容 hash 属网络/crypto 操作，只能在 run 结算后由宿主对产物执行。因此「引用唯一性」在运行时是尽力而为，在产物层是严格保证；
- schema 变宽推高弱模型结构化输出失败率——对策沿用现有纪律：失败项一律降级为 `uncertain`（绝不编造引用），并靠 vm 回归覆盖适配器分支。

**主要成本**：多一个 agent 阶段的 token 开销（可用抽样率控制）；prompt 开发与回归用例扩充。**结论：强烈建议做，P0 排首位**——它是 G-D 的地基，也是「诚实降级」纪律从证据层延伸到引用层的完成步。

## 3.2 工作流 B：复杂度路由 + 预算账本（P0）——可行性 ★★★★★

**机制**：Planner 之前插入 Intake Router（启发式分类即可起步，用户 depth 参数永远保留为手动覆盖），产出 BudgetPlan `{mode, maxAgents, maxToolCalls, maxRounds, minimumSourceTiers, requireCitationAudit}`；宿主维护 RunBudgetLedger 记录消耗与拒绝原因。

**平台吻合度**（这是六项中贴合度最高的）：
- **硬预算有现成强制点**：`maxTotalAgents` 直接是引擎 `start()` 的原生参数——超额发生在引擎层面，不是君子协定；轮次与切片本来就是脚本内循环边界；
- Router 输出经 `args` 传入脚本——事实 2 的标准通道；
- 消耗计量：`result.agentsStarted` 提供总量事实，`workflow/agent-start|agent-end` 事件提供宿主侧记账源（事实 4）；
- 20% 余量留给 follow-up/审计、连续零增益提前收敛——纯脚本内调度逻辑，现有 EIG 收敛机制的直接扩展。

**必须声明的平台边界**：引擎不发工具调用级事件，**单代理工具调用数只能是软预算**（由 `LIMIT(depth)` 式提示词承载）；硬预算维 度仅代理总数 / 轮次 / 时钟。这不是实现缺陷而是引擎观测面现状，报告如实标注即可。

**结论：必做，P0 且实现成本最低**——一次启发式分类 + 一个账本数据结构，换来的是把 C1（烧钱墙）和 C3（启发式失控）同时变成受管理的运行时事实。

## 3.3 工作流 C：检查点与恢复（P1）——可行性 ★★★☆☆

**机制难点先行**：run 无法暂停——单次 workflow 从 `start()` 到 result 结算是原子的，取消即杀死整棵树。因此「resume」的真实语义只能是**新 run 继承旧 run 的完结状态**。

**组合方案（全部落在已核验接缝内）**：
1. **轮级增量持久化**：脚本在各轮边界 `log(JSON.stringify(roundEvidence))`——把 log 钩子用作结构化数据通道（事实 4/7 的既有行为面），宿主监听后原子写 checkpoint（临时文件 + rename）。副产品是后台模式的实时进度可读性显著增强；
2. **恢复注入**：工具新增可选 `resumeRunId` 入参；宿主校验脚本/schema 版本兼容性后加载 checkpoint，通过 `args.resume` 把已完成 item 清单连同其 findings 注入新 run；脚本按 `itemId + 输入 hash` 幂等跳过已完成项（question 文本与 keywords 决定 hash，天然稳定）;
3. **血统标注**：恢复产出的报告区分「继承自 checkpoint」与「本次新取证」两种来源，且取消永不算成功（kill 映射保持现状，恢复报告中显式出现 killed 来源）。

**风险与缓解**：checkpoint 写失败的 item 下次重跑——幂等键保证结果覆盖同位安全，浪费有上界；陈旧来源（距离上次取证超过阈值）默认重查或标注 stale；敏感研究数据复用 workspace 权限边界并最小化原文落盘。**主要成本**：六项中工程量最大（宿主监听器、版本兼容矩阵、幂等键协议、恢复语义测试四件套）。**结论：值得做但要排在 A/B 之后**——它的收益兑现在「旗舰级长任务」上，而这类任务的体量恰恰由 B 的路由决定。

## 3.4 工作流 D：来源独立性 / 去重 / 冲突图（P1）——可行性 ★★★☆☆（与 A 共享基建后 ★★★★☆)

**机制**：宿主 Source Registry 做 URL 规范化 + 内容 hash + originId 推断；claim graph 计 `independentSourceCount`；综合规则强制「冲突并列呈现、单源承重降置信度」。

**分期建议**（削减其前期复杂度的关键是识别出它与 A 共用基建）：
- 一期随 A 交付：提示词层 sourceTier 纪律 + in-run 语法级去重 + 报告层的冲突并列要求（改的是综合规则，成本近乎为零）；
- 二期独立交付：宿主侧真正的内容 hash 与 origin 合并（作用于落盘产物与指标），以及「同一 origin 多篇转载只计一个独立来源」的计量口径修正。

origin 推断从规则法起步（registrable domain + 标题相似度 + 发布时间窗），不上 LLM——避免用模型解决可以用确定性规则解决的问题。**结论：一期搭车、二期缓行**。

## 3.5 工作流 E：分层综合 / 末端上下文治理（P1）——可行性 ★★★★★

**机制**：维度级 `EvidenceCard` → 维度综合产出 `DimensionBrief` → 最终 Synthesizer 只消费 briefs + 按 ID 回拉的 claim/citation 指针。

**平台吻合度**：`pipeline()` 组合子天然支持这种两段流（事实 7 的既有设施）；DimensionBrief 仍是受支持的 schema 形态；「表格/时间线保留为 JSON 工件、报告引用工件 ID」与既有产物布局无缝对接。

**唯一注意点**：多一轮 LLM 往返是实打实的成本，必须用验收指标证明「综合输入 token 显著下降且覆盖率/支撑精度不回退」才准上线——这点改进方案 §9.3 已经内置。**结论：改动最小、验证最容易，适合夹在 P0 与 C 之间先走**。

## 3.6 工作流 F：真实 Web 评测与发布门禁（P2）——可行性 ★★★☆☆（性质：持续运营）

**机制**：三层测试金字塔——VM 回归（已有 23 用例）/ 受控 Web 集（稳定权威页 + 已知答案）/ 开放 rubric 集 + 对抗集（转载链、404、付费墙、SEO 农场、冲突来源）；rubric 覆盖 factual accuracy、citation support precision、coverage、primary-source ratio、uncertainty honesty 等；触发条件绑定到 `src/script.ts`、提示词、schema、模型路由的任何改动。

**现实约束**：需要稳定的联网测试环境与持续的评测集策展人力；LLM judge 需要固定 rubric + 小样本人判重叠校准，不能让单一 judge 当唯一真值。**结论：值得做、必须做、但不能急于求成**——官方自己都是从约 20 条查询的小集合起步的；把它挂进 npm scripts 门禁体系即可渐进收紧。P2 的定位准确。

## 3.7 路线图整合（依赖驱动的排序）

```text
Phase 1 (P0)   ┌─ A 一期: 结构化引用 schema + citation-audit 阶段
               └─ B: Intake Router + BudgetPlan + RunBudgetLedger
                      （B 顺带给后续所有工作流提供预算约束框架）
Phase 2 (P1)   ┌─ E: DimensionBrief 分层综合（机械改造，先于 C）
               ├─ D 一期搭 A 的车: tier 纪律 + 语法去重 + 冲突并列
               └─ C: checkpoint 写入 + resumeRunId 恢复协议
Phase 3 (P1→P2)├─ D 二期: Source Registry 内容级合并 + 独立来源计量
               └─ F: 评测集滚动建设 + rubric judge 校准 + 发布门禁收紧
```

排序逻辑：先立「质量地板」（引用可审计）与「成本天花板」（预算契约），再动「吞吐结构」（分层综合），然后才是重工程的可靠性（恢复），评测门禁全程并行累积、持续收紧。

---

# 第四部分 蒸馏结论：这份研究沉淀出的五条工程定律

1. **预算即契约**。当效果方差主要由 token 解释时，把努力度从「提示词里的好习惯」升级为「运行时可观测、可限制、可解释的硬约束」，是所有 deep-research 系统的第一道工程门槛。（对应：B）
2. **验证要分层且诚实**。归因、支撑核验、覆盖度决策是三种不同职责；每个「已验证」标签只能覆盖机器实际核验过的范围，其余显式降级——**宁可交付带伤的诚实，也不交付完美的伪装**。（对应：A + 三态纪律）
3. **文件指针优于对话搬运**。原始证据与压缩产物双轨落盘，交付紧凑指针；末端综合允许按 ID 回拉，不给「传话游戏」留位置。（对应：E + 既有 artifacts 设计）
4. **控制权放在轮间，代价标在边界上**。接受同步批处理引擎的现实，把动态性收敛到结构化的轮间恢复点上；放弃的能力（开放 re-planning、thinking 控制）要写成已结算的交易而不是悬而未决的债。
5. **评测闭环决定成熟度上限**。编排代码终会被复制，评测集与发布门禁才是不可复制的资产；从小样本起步、与人判重叠校准、绑定发布流程渐进收紧。（对应：F）

**一句话总纲**：
> Claude Deep Research 展示了一类长程系统的形态上限，我们的工作不是缩小与它的距离，而是用**机制设计的确定性**补足**启发式系统的波动性**——把它的骨架变成可审计、可预算、可恢复、可评测的工程制品。

---

# 附录

## A. 三份输入文档的去留说明

本文是三份输入文档之上的综合决策层，最终布局如下：`claude-deep-research-principles.md` 与 `claude-research-improvement-plan.md` **原地保留**——前者仍是原理层的自学教材，后者仍是实施级别的工程规格（其 A–F 数据模型与验收指标继续权威）；`claude-research-analysis.md` 作为第一次可行性论证的**历史记录移入 `_archive/`**，其内容已被本文件更完整地覆盖；原始网页存档同在 `_archive/article.html`，可复核的正文纯文本为顶层 `article.txt`。分工总览：**原理层 → 实施层 → 论证层（已归档）→ 综合决策层（本文件）**。

## B. 本次结论的平台证据索引（fast lookup）

| 主张 | 出处（文件：行号） |
| --- | --- |
| 沙箱仅六个全局、无 fs/网络 | `platform-seam-verification.md` §3；runtime.ts:98-113 |
| `agent()` 五选项白名单 | `platform-seam-verification.md` §4；runtime.ts:39-41 |
| ITEM_CAP 上限 4096 致命 | `platform-seam-verification.md` §5；worker-thread/index.ts:119 |
| 六个 workflow 事件 | `adr-platform-caps.md` 事实 10 |
| jobs 终态无 cancelled | `platform-seam-verification.md` §11.2（NEEDS-REVISION 项） |
| 子代理继承全局工具世界 | `platform-seam-verification.md` §9；child-agent.ts:168,174 |
| schema 子集与 additionalProperties 硬约束 | `adr-platform-caps.md` 事实 4 |
| verifier 误报缺陷史 | `claude-code-CHANGELOG-full.md`（L1208，方法论文档 §2.3 摘录） |
| token=80% 方差 / 15× / 同步瓶颈自述 | `multi-agent-research-system.md`（Benefits/Synchronous execution 章节） |

*核验时效声明：以上平台断言绑定当前 harness checkout；升级后须重跑核验清单（断言自带行号，可机械复核）。*
