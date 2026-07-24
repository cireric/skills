# Deepworker Agent 优化需求设计文档

> **来源**: deepworker.md (cireric/workflows) + Hephaestus (oh-my-openagent) 对比分析 + 模型通用性拷问
> **创建日期**: 2026-07-23
> **文档版本**: v2.0
> **状态**: Draft

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [模型能力适配层](#2-模型能力适配层)
3. [现状分析](#3-现状分析)
4. [设计原则](#4-设计原则)
5. [流程重设计](#5-流程重设计)
6. [各阶段详细设计](#6-各阶段详细设计)
7. [QA Gate 体系设计](#7-qa-gate-体系设计)
8. [Subagent 生态设计](#8-subagent-生态设计)
9. [Opencode 配置设计](#9-opencode-配置设计)
10. [变更清单](#10-变更清单)
11. [风险与缓解](#11-风险与缓解)
12. [附录](#12-附录)

---

## 1. 背景与动机

### 1.1 问题陈述

当前 deepworker (v1) 采用 7 阶段严格状态机 + 11 条回退路径 + 每阶段强制 Exit Declaration 的设计。实际使用中暴露以下问题：

| 问题 | 表现 | 根因 |
|------|------|------|
| **流程过重** | 简单任务也要走完 7 阶段，Exit Declaration 消耗大量 token | 流程重量在"过程控制"而非"结果验证" |
| **回退成本高** | 回退时全量重做阶段，2 次无进展即升级 | 缺乏增量补充机制 |
| **ORACLE ATTACK 固定开销** | 每次任务必跑 3 轮 Oracle，即使任务无歧义 | Oracle 作为独立阶段而非按需机制 |
| **LLM 遵循率低** | 严格模板格式在 prompt 中难以可靠执行 | 依赖 LLM 自律而非工具强制 |
| **缺少意图门控** | 用户说"看看这个 bug"，agent 只看不改 | 无 Intent Classification |
| **机制绑定强模型** | 三尝试协议、Drift detection 等依赖模型自律，弱指令遵循模型上失效 | 未区分"任何模型都能做"与"依赖强指令遵循"的机制 |

### 1.2 参考基准

Hephaestus (omo) 的 GPT-5.5 提示词验证了一个关键假设：**"轻流程 + 重 QA Gate"比"重流程 + 轻 QA"更可靠**。其证据：

- Manual QA Gate 按交付物类型定义验证方式，可执行性强
- 三尝试失败协议强制换方法，避免同一思路上反复
- Operating Loop 短循环（Explore→Plan→Implement→Verify→QA）符合实际编码节奏
- Success Criteria 清单比复杂 pass condition 更简洁有效

**但**：Hephaestus 的机制是针对 GPT-5.4/5.5/5.6 专门调优的（每个 GPT 版本有独立 prompt 变体）。deepworker v2 的目标是通用模型（GLM-5.x / DeepSeek-V4-Pro / Kimi-k3 等），不能原封照搬。

### 1.3 优化目标

| 指标 | v1 (当前) | v2 (目标) | 改善幅度 |
|------|----------|----------|---------|
| 阶段数 | 7 | 5 | -29% |
| 回退路径 | 11 条 | 3 条 | -73% |
| Exit Declaration | 每阶段强制完整模板 | 结构化输出（1-3 行） | token -60% |
| Oracle 开销 | 每次任务 3 轮 | 按需（3 次失败后强制） | 简单任务 -100% |
| Steps budget | 66 | 50 | -24% |
| QA 强度 | 双层但抽象 | 三支柱 + 按类型验证 | 可执行性 +↑ |
| 模型通用性 | 隐式绑定 GPT | 显式 Tier 1/2/3 机制分级 | 通用模型可用性 +↑ |

### 1.4 目标模型

deepworker v2 不绑定特定模型供应商，设计需兼容以下模型系列：

| 模型 | 关键特征 | 对 agent 设计的影响 |
|------|---------|-------------------|
| GLM-5.1/5.2 | 100K+ context 下 accuracy 退化（论文自述），需 keep-recent-k 策略 | 不能假设超长上下文下推理一致 |
| DeepSeek-V4-Pro | 引入 XML tool-call 格式（`|DSML|`），与 JSON tool schema 可能不兼容 | Subagent 交互需验证兼容性 |
| Kimi K3 | thinking history 缺失或中途换模型会导致质量不稳定 | Subagent 机制需保留完整 thinking blocks |
| GPT-5.5/5.6 | 指令遵循最强，工具调用最可靠，偏好精简 prompt | 上界参考，v2 机制应向下兼容 |

---

## 2. 模型能力适配层

### 2.1 核心发现

通过对比 GLM-5.x / DeepSeek-V4-Pro / Kimi K3 / GPT-5.5 的能力差异，得出关键结论：

- **非 GPT 模型的核心弱点不是"笨"，而是"不听话"**——能力足够但纪律性不足
- **GPT 系列在"指令遵循 + 工具调用 + 长上下文一致性"三维度上显著领先**，这是 Hephaestus 所有机制的前提条件
- **Kimi K3 有独特的 thinking history 依赖**——如果 opencode 的 subagent 机制不能完整传递 thinking blocks，K3 质量会不稳定
- **DeepSeek-V4 的 XML tool-call 格式**与 opencode 的 JSON tool schema 可能不兼容
- **GLM-5 在超长上下文下需要 keep-recent-k 策略**，与"保留完整上下文"假设冲突

### 2.2 机制分级

v2 的每个机制按"对模型能力的依赖程度"分为三级：

| Tier | 含义 | 通用模型可用性 | 策略 |
|------|------|--------------|------|
| **Tier 1** | 任何合格 LLM 都能做 | 直接可用 | 保持原设计 |
| **Tier 2** | 依赖中等指令遵循，需工具强制替代自律 | 需外部机制辅助 | 用 todowrite 等工具使决策外部可见、可审查 |
| **Tier 3** | 依赖强指令遵循或长上下文推理 | 需降级或替代 | 拆为单步迭代、减少并行负荷 |

### 2.3 各机制分级结果

| 机制 | Tier | 理由 | 适配措施 |
|------|------|------|---------|
| Intent Gate 意图表 | 1 | 简单映射表，任何模型都能做 | 无 |
| Manual QA Gate 按类型验证 | 1 | 定义了具体工具和步骤，模型只需执行 | 无 |
| Success Criteria 清单 | 1 | 5 条可观察条件，模型逐条检查 | 无 |
| 并行 explore subagent | 2 | 需模型正确使用 `run_in_background` + 收集结果 | Subagent 启动检查表（布尔逻辑驱动） |
| Exit Declaration 简化 | 2 | 需模型判断何时"关键决策点" | 改为固定结构化输出，非条件触发 |
| Assumptions Check | 3 | 4 项并行检查对模型认知负荷高 | 拆为 2 轮迭代，Round 2 条件触发 |
| 三尝试失败协议"换根本不同方法" | 3 | 依赖模型自我判断"不同方法"vs"微调" | todowrite 外部计数 + method-category |
| Drift detection 每步对照 PLAN | 3 | 依赖模型主动回忆 PLAN 并对比 | todowrite header 锚定 + 用户可观察 |

---

## 3. 现状分析

### 3.1 Deepworker v1 流程

```
UNDERSTAND → DISCOVER → ORACLE ATTACK → PLAN → EXECUTE → VERIFY → QA GATE → Done
     ↑           ↑            ↑                    ↑        ↑        ↑
     └───────────┴────────────┴────────────────────┴────────┴────────┘
                         11 条回退路径
```

### 3.2 Hephaestus 流程

```
Intent Gate → Discovery & Retrieval → Operating Loop → Done
                                      ┌──────────────────────────────┐
                                      │ Explore → Plan → Implement → │
                                      │ Verify → Manual QA           │
                                      └──────────────────────────────┘
                                           (短循环，可多轮)
```

### 3.3 关键差异对比

| 维度 | deepworker v1 | Hephaestus | v2 取向 |
|------|-------------|-----------|---------|
| **流程结构** | 线性 7 阶段 + 回退表 | 3 层（Intent→Discovery→Loop） | 5 阶段 + 快速通道 |
| **歧义处理** | 5 模式扫描 + Deep Scan + Gap Analysis | Intent Gate 意图表 + Assumptions Check | 两者融合，Assumptions Check 拆 2 轮迭代 |
| **Oracle** | 独立阶段，强制 3 轮 | 按需咨询，3 次失败后强制 | 按需 + 失败强制 |
| **TDD** | 强制 default，direct 仅限封闭列表 | 无 TDD 要求，"Default to not add tests" | step 级判定 + 封闭列表 + 快速降级 |
| **验证** | VERIFY(静态) + QA GATE(功能) 分离 | lsp_diagnostics + Manual QA Gate | 合并为 VERIFY & QA GATE |
| **Exit Declaration** | 每阶段强制完整模板 | 无 | 结构化输出（1-3 行） |
| **回退** | 11 条显式路径 | 就地修复 + 3 次失败协议 | 3 条路径 |
| **并行** | sub-agent 并行（默认） | 激进并行（所有独立调用） | 继承激进并行 |
| **模型依赖** | 隐式绑定 GPT 级指令遵循 | 针对 GPT-5.4/5.5/5.6 专门调优 | 显式 Tier 1/2/3 机制分级 |

### 3.4 v1 保留项 vs 新增项 vs 简化项

| 类别 | 具体内容 |
|------|---------|
| **保留** | Ambiguity Scan 5 模式、TDD default rule（step 级判定）、Constraint anchor、Post-Edit Verification、Deletion Declaration、Staged Area Check |
| **新增** | Intent Gate（来自 Hephaestus）、Manual QA Gate 按类型验证表（来自 Hephaestus）、三尝试失败协议 + todowrite 外部计数（来自 Hephaestus + 通用化）、Success Criteria 清单（来自 Hephaestus）、快速通道、Subagent 启动检查表、模型能力适配层（Tier 1/2/3）、todowrite Plan Anchor header、todowrite Failure Log |
| **简化** | Exit Declaration → 结构化输出、ORACLE ATTACK → 按需 + 失败强制、Deep Ambiguity Scan 4 项 → 2 轮迭代 Assumptions Check、Gap Analysis → 合入 Assumptions Check、回退路径 11 条 → 3 条、Steps 66 → 50、Drift detection → todowrite header 锚定 + 用户可观察、Consumer Identification → 分轻量（grep）和深度（subagent）两级 |
| **移除** | VERIFY 独立阶段（合入 VERIFY & QA GATE）、ORACLE ATTACK 独立阶段、UNDERSTAND 阶段的快速通道初判 |

---

## 4. 设计原则

### P1: 轻流程 + 重 QA Gate

流程的重量从"过程控制"转移到"结果验证"。阶段间松散过渡，只在关键决策点设卡。验证行为通过工具调用强制，而非通过模板格式约束。

**含义**：
- 去掉每阶段强制 Exit Declaration，改为结构化输出
- 强化 Manual QA Gate 为不可跳过的硬关卡
- 用 Success Criteria 清单替代复杂的 pass condition

### P2: 增量而非全量

回退时增量补充，不全量重做。新发现的信息追加到已有结论，而非重新执行整个阶段。

**含义**：
- DISCOVER → UNDERSTAND 回退时，只补充新歧义
- EXECUTE 循环内就地修复，不回退到 PLAN
- 假设列表追加而非重建

### P3: 按需而非强制

高成本操作（Oracle、完整 Exit Declaration、Deep Ambiguity Scan）按需触发，而非每次任务都执行。

**含义**：
- Oracle 在 3 次失败后强制，而非每次任务必跑
- Assumptions Check Round 2 条件触发，简单任务可跳过
- Subagent 启动由布尔检查表决定，非主观判断

### P4: 可执行优于可声明

规则必须能通过工具调用或行为观察来验证，而非仅靠 prompt 文本约束。

**含义**：
- Manual QA Gate 定义按交付物类型的验证方式（可执行）
- Success Criteria 是可观察的行为（可验证）
- 三尝试失败协议通过 todowrite 外部计数（可追踪）
- Drift detection 通过 todowrite header 锚定（可观察）

### P5: 机制分级适配

机制的强制程度与模型能力匹配。Tier 1 机制直接可用，Tier 2 需工具辅助，Tier 3 需降级或替代设计。

**含义**：
- 不假设模型有 GPT 级指令遵循能力
- 依赖自律的机制必须有外部可观察的替代
- 判定条件用布尔逻辑而非主观判断

---

## 5. 流程重设计

### 5.1 v2 整体流程

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: UNDERSTAND                                         │
│   - Intent Classification (Hephaestus 意图表)               │
│   - Ambiguity Scan (5 模式)                                 │
│   - 2x effort difference → ask user                         │
│   输出：Intent + Goal + Ambiguity + Scope                    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: DISCOVER                                           │
│   Step 1: 定向读取 + Assumptions Check Round 1              │
│     - 直接读目标文件                                         │
│     - 重新评估 UNDERSTAND 歧义                               │
│     - 代码结构歧义                                           │
│     - 轻量 Consumer ID (grep)                                │
│     - Subagent 启动检查表                                     │
│     - 快速通道判定（一次性，基于代码证据）                     │
│   Step 2: 广搜 [条件触发]                                    │
│     - 启动 Explore/Librarian subagent                        │
│     - 深度 Consumer ID                                       │
│   Step 3: Assumptions Check Round 2 [条件触发]              │
│     - 跨函数一致性 + 调用链数据流一致性 + 运行时假设         │
│   输出：Facts + Consumer + Assumptions + Scope + fast-track  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: PLAN                                               │
│   - 文件列表 + 变更描述 + 依赖                               │
│   - TDD/direct 标注 (step 级判定)                            │
│   - 约束锚定                                                │
│   - 写入 todowrite (Plan Anchor header + steps)              │
│   输出：Execution Plan (结构化)                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: EXECUTE                                            │
│   ┌──────────────────────────────────────┐                  │
│   │  Implement → Post-Edit Verify        │                  │
│   │      ↑            │                  │                  │
│   │      └── 修复 ←───┘                  │                  │
│   └──────────────────────────────────────┘                  │
│   - todowrite 驱动 (Plan Anchor + Failure Log)               │
│   - TDD 纪律 (step 级 Red/Green/Refactor)                   │
│   - 三尝试失败协议 (todowrite 外部计数)                       │
│   - Drift detection (todowrite header 锚定)                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: VERIFY & QA GATE                                   │
│   Step 1: 全量静态检查                                       │
│     - Type safety / Tests / Style / Change scope / Build    │
│     失败 → EXECUTE                                          │
│   Step 2: Manual QA Gate                                    │
│     - Surface verification (按类型验证表)                    │
│     - Assumption 逐条验证                                    │
│     - Non-obvious combination path                          │
│     失败 → 按原因路由                                       │
│   Step 3: Success Criteria 清单                              │
│     - 5 条全部满足 + Forbidden stops 检查                    │
│   输出：Pass/Fail + evidence                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
                     Done
```

### 5.2 快速通道

快速通道判定在 DISCOVER Step 1 后一次性做出（不在 UNDERSTAND 阶段初判），基于代码证据而非纯语义推理。

**快速通道条件**（全部满足才适用，在 DISCOVER Step 1 后判定）：
- 单文件变更（Step 1 读取后确认）
- ≤3 步操作
- 无歧义（UNDERSTAND + Step 1 均未发现）
- 无跨函数共享概念（Step 1 代码分析后确认）
- Consumer ID 无意外发现（grep 引用数 ≤ 预期）

**快速通道流程**：
```
UNDERSTAND → DISCOVER(Step 1 only, 简写) → PLAN(简写) → EXECUTE → VERIFY & QA GATE(简写)
```

**简写规则**：
- DISCOVER：只做 Step 1 定向读取 + 轻量 Consumer ID，不做 Assumptions Check，不填 Subagent 检查表，不启动 subagent
- PLAN：可简写为 1-2 行
- VERIFY & QA GATE：只做全量静态检查 + happy path 验证，不做 assumption 逐条验证和组合路径测试

**为什么取消 UNDERSTAND 阶段的快速通道初判**：初判创建锚定效应——agent 倾向于维持初判以省力，即使 DISCOVER 证据暗示应升级为标准流程。一次性判定消除锚定效应，且判定基于代码证据更准确。

### 5.3 回退路径（3 条）

| # | 触发条件 | 路径 | 行为 |
|---|---------|------|------|
| 1 | EXECUTE 内单步验证失败 | 就地修复 → 重验证 | 不离开 Phase 4 |
| 2 | 3 次不同方法均失败（todowrite Failure Log 记录） | Oracle 咨询 → 再尝试 1 次 | Oracle 结果指导修复 |
| 3 | Oracle 后仍失败 | 问用户 1 个精确问题 | 最后手段 |

**与 v1 的关键区别**：不再回退到早期阶段（UNDERSTAND/DISCOVER/PLAN）。原因：
- 回退到早期阶段意味着全量重做，token 成本极高
- 实际中，理解错误在 EXECUTE 阶段通过 Oracle 咨询即可修正
- 如果确实需要重新理解，Oracle 会指出，此时再增量补充

### 5.4 循环终止

| 条件 | 行动 |
|------|------|
| Success Criteria 全部满足 | Done |
| Phase 4 循环 3 次无进展 | → Oracle |
| Oracle 后 1 次仍无进展 | → 用户 |
| Phase 5 VERIFY & QA GATE 2 次失败 | → Oracle → 用户 |

### 5.5 todowrite 使用范围

| 阶段 | 是否使用 todowrite | 理由 |
|------|-------------------|------|
| UNDERSTAND | 否 | 产出是信息，不是交付物；用结构化输出控制流程 |
| DISCOVER | 否 | 产出是发现，不是交付物；用结构化输出控制流程 |
| PLAN | **是** | 从"规划"到"执行"的转折点；写入 Plan Anchor header + steps |
| EXECUTE | **是** | 执行驱动 + 状态记录（Plan Anchor + Failure Log） |
| VERIFY & QA GATE | 否（读 todowrite） | 验证 EXECUTE 的交付物，不新增 todo items |

---

## 6. 各阶段详细设计

### 6.1 Phase 1: UNDERSTAND

**目的**：确定用户真实意图 + 识别歧义。纯语义推理，不做代码探索。

#### 6.1.1 Intent Classification（新增，来自 Hephaestus）

| 用户表面表达 | 真实意图 | 行动 |
|------------|---------|------|
| "你做了X吗？"（没做） | 现在做 X | 简短承认，做 X |
| "X怎么工作的？" | 理解后修复/改进 | 探索，然后行动 |
| "能看看Y吗？" | 调查并解决 | 调查，然后解决 |
| "做Z最好的方式？" | 用最好的方式做 Z | 决定，然后实现 |
| "为什么A坏了？" | 修 A | 诊断，然后修 |
| "你觉得C怎么样？" | 评估并实现 | 评估，然后行动 |

**纯问题（无行动）仅当所有条件满足**：用户明确说"just explain"/"don't change anything"；无可操作的代码库上下文；无问题或改进暗示。

**输出**：一行意图声明——"I detect [intent type] — [reason]. [What I'm doing now]."

#### 6.1.2 Ambiguity Scan（保留 v1，简化输出）

5 模式扫描保留：

| 模式 | 信号 | 行动 |
|------|------|------|
| Vague verb | "optimize", "improve", "fix", "refactor" | 列 2+ 解释 → 评估 |
| Undefined target | "the script", "the config" | 1 个匹配 → 假设；0 或 2+ → 标记 |
| Open-ended scope | "better", "cleaner", "faster" | 列 2+ 解释 + effort 估计 → 评估 |
| Missing constraint | 无错误处理、无边界行为 | 声明为假设 |
| Internal contradiction | 需求互斥 / 与项目规则冲突 | 标记，不自行解决 |

**Evaluation rule 保留**：2x+ effort difference → ask user。

**Flagged ambiguity resolution rule 保留**：标记后只能 (1) ask user 或 (2) 声明"所有胜任的工程师都会毫不犹豫地做出相同选择"并给出理由。

**输出**：

```
Intent: [意图声明]
Goal: [理解]
Ambiguity: [none | '[term]' → [interpretation] (assumption) | '[term]' → asked user, confirmed [interpretation]]
Scope: [in / out]
```

### 6.2 Phase 2: DISCOVER

**目的**：建立完整心智模型。代码感知推理——所有需要读代码的检查在此执行。

#### 6.2.1 Step 1: 定向读取 + Assumptions Check Round 1 [必做]

**顺序设计理由**：先快速读目标文件做 Round 1 检查，再根据 Round 1 结果决定是否需要广搜。这比"先广搜再检查"更高效——简单任务可能 Step 1 就够了，省掉 subagent 开销。

- 直接读目标文件（不启动 subagent）
- 重新评估 UNDERSTAND 歧义（有代码证据后）
- 代码结构歧义（代码揭示了哪些 prompt 未覆盖的歧义）
- 轻量 Consumer ID（grep 搜引用）
- Subagent 启动检查表
- 快速通道判定（一次性，基于代码证据）

**Subagent 启动检查表**（布尔逻辑驱动，非主观判断）：

```
## Explore Need Check
- 涉及文件数: [1 / 2+]
- 已直接读取目标文件: [yes/no]
- 目标文件内容是否足以理解修改上下文: [yes/no]
→ 2+ 文件 AND (未读取 OR 内容不足) = MUST launch Explore

## Librarian Need Check
- 是否使用不熟悉的库/API: [yes/no，列出名称]
- 项目内是否有参考实现: [yes/no]
- context7 MCP 是否已覆盖: [yes/no]
- 是否需要算法/标准/规范细节: [yes/no]
→ 存在任意 yes AND 无项目内参考 AND context7 未覆盖 = MUST launch Librarian
```

**Subagent 触发条件**（明确化）：

| Subagent | 触发条件 | 不触发的条件 |
|----------|---------|------------|
| **Explore** | 修改涉及 ≥ 2 文件 | 单文件变更，且目标文件已直接读取 |
| **Librarian** | ①使用不熟悉的库/API ②需要查算法/标准/规范 ③代码库内无参考实现 | ①项目内有参考代码 ②context7 MCP 能回答 ③模型已有充分知识 |

**快速通道判定**：在此步末尾一次性判定。条件见 §5.2。快速通道任务不做 Assumptions Check、不填检查表、不启动 subagent。

**输出**：

```
Updated ambiguities: [none | list]
Code ambiguities: [none | list]
Consumer: [confirmed/assumed/blocked]
Subagent need: [Explore: must/not-needed | Librarian: must/not-needed]
fast-track: [yes/no]
```

#### 6.2.2 Step 2: 广搜 [条件触发]

**触发条件**：Explore Need Check = MUST OR Round 1 发现新歧义需更多上下文 OR 核心问题未回答 OR 缺关键事实。

- 并行 2-5 explore/librarian subagent（`run_in_background=true`）
- 深度 Consumer ID（subagent 搜索调用链）

**停止条件**：足够上下文 / 信息重复 / 2 轮无新数据。

**不重复已委托的搜索**：一旦委托 explore agent 搜索，自己不再搜同一内容。

**输出**：

```
Facts: [N confirmed, with evidence source]
Consumer: [confirmed/assumed/blocked]（更新）
```

#### 6.2.3 Step 3: Assumptions Check Round 2 [条件触发]

**触发条件**：Round 1 发现新歧义 OR 任务涉及 ≥2 函数。

**检查项**（3 项）：

1. **跨函数语义一致性**：≥2 函数共享概念时，实现解释是否一致？不一致且 effort ≥2x → 标记
2. **调用链数据流一致性**（来自 v1 End-to-End Scenario，合并于此）：≥2 函数时，描述端到端调用链并确认数据流匹配——函数 A 的输出格式是否匹配函数 B 的输入预期？即使无共享概念，只要存在数据流依赖就需检查
   - 格式：`[function_A] → [function_B] → [function_C]`，Expected: [端到端预期行为]
   - 数据流不匹配 → 标记为歧义
3. **运行时假设**：依赖外部资源/运行时条件时，行为是否指定？

**为什么拆为 2 轮而非 4 项并行**：4 项同时检查 = 模型需在单次输出中维持 4 个并行推理线程。通用模型（GLM-5 在 100K+ context 退化、Kimi K3 thinking history 依赖、DeepSeek-V4 agent 任务弱于 GPT）在 DISCOVER 阶段认知负荷已高，4 项并行检查遗漏风险大。拆为 2 轮迭代，降低认知负荷，且 Round 2 可跳过（简单任务省开销）。

**为什么合并 End-to-End Scenario 到此**：v1 的 End-to-End Scenario（PLAN 阶段）和 Round 2 的跨函数一致性检查触发条件相同（≥2 函数），但覆盖维度互补——End-to-End Scenario 覆盖"调用链数据流"（A 的输出是否匹配 B 的输入），Round 2 覆盖"共享概念语义"（A 和 B 对同一概念的理解是否一致）。合并后消除冗余触发条件，且在 DISCOVER 阶段发现数据流问题比在 PLAN 阶段更早。

**输出**：

```
Cross-function issues: [none | list with effort ratios | N/A (single function)]
Call-chain data flow: [A → B → C, Expected: ... | data flow consistent | mismatch: ... | N/A (single function)]
Runtime assumptions: [none | list | N/A]
```

**如果发现新歧义**：增量补充到 UNDERSTAND 的结论，不回退重做整个 UNDERSTAND。仅当歧义满足 2x effort rule 时才 ask user。

#### 6.2.4 DISCOVER 统一输出

```
Facts: [N confirmed, with evidence source]
Consumer: [confirmed/assumed/blocked]
Assumptions: [list of atomic, testable propositions]
Scope: [in / out]
Workspace: [clean | pre-existing changes: ...]
fast-track: [yes/no]
```

### 6.3 Phase 3: PLAN

**目的**：承诺执行路径。此计划是漂移检测锚和约束再注入源。

**todowrite 从此阶段开始使用**——PLAN 完成时写入 todowrite，作为 EXECUTE 阶段的驱动。

#### 6.3.1 输出格式

```
## Plan: [one-sentence summary]

### Goal
[specific, verifiable completion criteria]

### Path
1. [step1] — [expected output] [TDD/direct] — [reason]
2. [step2] — [expected output] [TDD/direct] — [reason]
...

### Constraints
[constraint-1 | constraint-2 | constraint-3]
Assumptions tracked: [N items]

### Risks
- [risk] → [mitigation]
```

#### 6.3.2 TDD Default Rule（保留 v1，增加快速降级）

**判定粒度：step 级别**（非任务级别）。每个 PLAN step 独立判定 TDD/direct，标准客观。

- `[TDD]` — step 创建/修改有可测试行为的函数/类时，default
- `[direct]` — 封闭列表：CONFIG / VERIFY / FIXTURE / ANNOTATE / ENTRY。必须声明：`[direct] — [类型]: [原因]`
- **No mixed steps**：step 混合 TDD-eligible + direct-eligible 代码必须拆分
- **每个 step 必须标注 mode + reason**

**快速降级**（新增）：同一 step Red 失败 2 次 → 降级为 direct 模式，EXECUTE 后补测试。降级时声明："Red quality: 2 attempts failed, 降级为 direct。将在 EXECUTE 后补测试。"

**Red quality levels 保留**：
- Infrastructure Red（ImportError）：有效但弱
- Behavioral Red（AssertionError）：有效且强
- 目标：每个 TDD cycle 追求 Behavioral Red

**为什么 step 级而非任务级**：任务级分级（Level 1/2/3）的"单交付物"边界模糊，agent 判断困难。step 级判定的标准是客观的——"step 是否创建可测试行为"，封闭列表定义了边界，agent 无需做主观分类。

#### 6.3.3 粒度规则

- 最大 10 步，超过则拆分任务
- 最小粒度：每个独立交付物（有独立可测试行为的函数/类）必须是单独步骤
- 最大合并：2 个相关交付物/步骤（如 interface + implementation 同文件）

#### 6.3.4 快速通道简写

快速通道任务：Plan 可简写为 1-2 行——"修改 [file] 的 [function]，[what change]。[TDD/direct]。"

#### 6.3.5 todowrite 写入

PLAN 完成时写入 todowrite，格式：

```
## Plan Anchor
Goal: [一句话]
Constraints: [c1 | c2 | c3]
Steps: [N total, 0 completed]

## Failure Log
(empty at start)

---
- [ ] Step 1: [description] [TDD/direct]
- [ ] Step 2: [description] [TDD/direct]
...
```

### 6.4 Phase 4: EXECUTE

**目的**：按 PLAN 执行代码修改。每个编辑后立即验证，形成紧密循环。

#### 6.4.1 TODO Iron Law（保留 v1）

| 规则 | 描述 |
|------|------|
| Step tracking | PLAN path → todo list，Plan Anchor header 作为固定 header |
| Single-step focus | 同一时间只有 1 个 `in_progress` |
| Completion marking | 每步完成后立即标记 `completed`，不批量。同时更新 Steps 计数 |
| Drift detection | todowrite header 锚定 + 用户可观察（见 §6.4.5） |
| Post-edit verification | 每次编辑后验证（见 §6.4.2） |
| Constraint capture | 新约束 → 记录到 TODO + 更新 Plan Anchor Constraints |
| Assumption tracking | 假设变更 → 更新 Plan Anchor assumption 计数 |

#### 6.4.2 Post-Edit Verification（保留 v1）

每次文件编辑后：
1. `lsp_diagnostics` on changed files → 不可用或误报时用项目 type-check CLI
2. 项目 lint tool on changed files
3. 错误：auto-fix 可用时修复，验证无行为变更
4. 剩余：手动修复。代码缺陷 → 修代码（不压制规则）。误报 → 最小范围抑制

**为什么保留 v1 设计（不增加 todowrite 验证记录）**：v1 的 Post-Edit Verification 在 GLM-5.1 上已验证可接受。其可靠性来自"验证是工具调用（CLI 命令），不是纯推理"这一本质特性。增加 todowrite 验证记录是额外复杂度但无证据证明提升可靠性。

#### 6.4.3 TDD Enhancement（保留 v1，增加降级）

当步骤标记 `[TDD]` 时：
1. **Red**：写失败测试指定期望行为
2. **Green**：写最小代码通过
3. **Refactor**：清理，保持测试绿

**Red validity criterion 保留**（HARD RULE）。

**快速降级**：2 次 Red 失败 → 声明降级 → direct 模式 → EXECUTE 后补测试。

**当 `[direct]`**：仍遵循 TODO Iron Law、Post-Edit Verification。"Direct" = 无 test-first 循环，不是无纪律。

#### 6.4.4 失败恢复——三尝试失败协议（重设计）

**核心变更**：从 prompt 自律改为 todowrite 外部计数 + method-category。

**问题**：原设计（"换根本不同方法"）全靠模型自律——模型自己判断"是否换了方法"、自己计数"第几次失败"。通用模型会出现：假换方法（改个变量名声称换了）、忘记计数、重新计数、跳过 Oracle。

**todowrite Failure Log 设计**：

每次失败时，模型必须在 todowrite 的 Failure Log 中追加一条：

```
failure #1 | approach: [一句话描述] | error: [失败原因] | method-category: [algorithm | library | pattern | api-design | approach]
```

**method-category 分类**（5 类，粗粒度）：

| method-category | 含义 | 示例 |
|----------------|------|------|
| `algorithm` | 换了核心算法/策略 | BFS → DFS，递归 → 迭代 |
| `library` | 换了依赖库/框架 | requests → httpx |
| `pattern` | 换了设计模式/架构模式 | 回调 → Promise |
| `api-design` | 换了接口设计/数据结构 | REST → CLI |
| `approach` | 换了整体解决思路 | 解析器 → 正则 |

**强制规则**：

- failure #1 和 #2 的 method-category **相同** = 未换方法，Oracle 提前介入
- 同类切换算换方法，**仅当**新方法的核心机制与旧方法不同（非参数调整、非同类库的 API 风格差异）
  - 不算换方法：`library.requests` → `library.httpx`（同类 HTTP 库）、调参、重命名
  - 算换方法：`library.requests` → `pattern.caching`（从"直接请求"改为"缓存优先"）
- failure #3 → STOP，强制调用 Oracle subagent
- Oracle 后 #4 仍失败 → 强制问用户 1 个精确问题

**完整协议**：

```
第 1 次失败 → Failure Log 记录 → 换一种根本不同的方法
第 2 次失败 → Failure Log 记录 → #1 和 #2 method-category 相同 → Oracle 提前介入
                                    #1 和 #2 method-category 不同 → 再换一种方法
第 3 次失败 → Failure Log 记录 → STOP
  ├─ revert 到已知良好状态
  ├─ 记录 3 次尝试及失败原因
  ├─ 咨询 Oracle（同步，完整失败上下文）
  └─ Oracle 后再尝试 1 次
       ├─ 成功 → 继续
       └─ 失败 → 问用户 1 个精确问题
```

**Stall 定义**：2 个 edit-verify 循环诊断不变 = stall。Stall 时按失败恢复协议处理。

**为什么用 todowrite 而非模型内部计数**：
- todowrite 是外部工具，写入后模型无法篡改
- 用户和 orchestrator 可观察计数过程
- method-category 让"是否真换了方法"可被外部审查

#### 6.4.5 Drift Detection（重设计）

**核心变更**：从"模型主动回忆 PLAN 并对比"改为"todowrite header 锚定 + 用户可观察"。

**问题**：原设计要求模型每步执行后主动回忆 PLAN 内容、主动对比、主动判断 drift 程度。通用模型的"主动"能力弱，几乎不会发生。

**todowrite Plan Anchor 锚定**：

Plan Anchor 始终在 todowrite header 中可见。模型不需要"回忆" PLAN——每次看 todowrite 时都能看到锚点。

**Drift 判定改为可观察规则**：

| 信号 | 判定 | 行动 |
|------|------|------|
| Steps 计数跳跃（跳步） | Major drift | 暂停，ask user |
| Goal 被修改 | Major drift | 暂停，ask user |
| Constraints 被删除/替换（非追加） | Constraint decay | 再注入原始约束 |
| 新增 Constraint（追加） | Minor drift | 允许，记录 |
| Step 顺序调整但无跳步 | Minor drift | 允许，更新 |

**检测方式**：模型自律 + 用户可观察。Drift 信号写在 todowrite 中，用户和后续 review 可事后发现 drift，形成软约束。opencode 当前没有自动监控 todowrite 变化的功能，因此无法做外部自动检测。

**为什么比"主动对照 PLAN"更可靠**：模型不需要"回忆"——信息始终在眼前。Drift 信号是可观察的（Steps 计数变化、Goal/Constraints 修改），而非依赖模型内心判断。

### 6.5 Phase 5: VERIFY & QA GATE

**目的**：代码质量关卡 + 功能正确性关卡。先全量静态检查，再功能验证，最后 Success Criteria 确认。

**设计理由**：v1 的 VERIFY（静态）和 QA GATE（功能）是两个独立阶段。v2 合并为一个阶段，但内部保持 Step 1 → Step 2 → Step 3 的顺序，确保全量检查在功能验证之前。合并的原因：QA GATE 的 Success Criteria 已隐含全量静态检查的通过条件（lsp_diagnostics clean、build exit 0、tests pass），拆为两个阶段增加了一次阶段间输出的 token 开销而无实质收益。

#### 6.5.1 Step 1: 全量静态检查

全量检查所有变更文件（非增量），捕获跨文件交互错误。

| 检查项 | 验证内容 | 通过标准 |
|--------|---------|---------|
| Type safety | 所有变更代码的类型错误 | 0 type errors |
| Tests | 全量测试套件（已有 + 新增） | 全部通过 |
| Style compliance | 所有变更文件的 lint/format | 0 errors |
| Change scope | 只修改了 PLAN 声明的文件 | 仅声明文件 |
| Build | 项目编译/构建 | 成功 |

**失败路由**：→ EXECUTE（修代码）

**如果某项检查无工具可用**：跳过并声明 "NOT VERIFIED: [check] (reason: no tool available)"

#### 6.5.2 Step 2: Manual QA Gate

**Pass Conditions**（ALL must be true）：

1. **Step 1 全量静态检查通过**
2. **Surface verification**：交付物通过实际使用表面正常工作
3. **Assumption verification**：每个假设的实现正确覆盖
4. **Non-obvious combination**（≥2 函数共享概念时）：至少 1 个组合路径测试
5. **No known unresolved issues**

**按类型验证表**（来自 Hephaestus）：

| 交付物类型 | 验证方式 | 工具 |
|-----------|---------|------|
| CLI / 脚本 / shell binary | 启动运行：happy path + 1 个错误输入 + `--help` | `interactive_bash` (tmux) |
| Web / 浏览器 UI | 打开页面、点击元素、填充表单、观察控制台 | playwright skill |
| HTTP API / 运行服务 | 用 `curl` 或驱动脚本调用 | bash |
| Library / SDK / 模块 | 写最小驱动脚本 import 并执行 | bash + edit |
| 无匹配表面 | 问自己：真实用户怎么发现这东西能用？照做 | 按场景选择 |

**关键规则**：读源码然后说"这应该能工作" ≠ 通过。必须执行并观察正确行为。

**Assumption Verification Method**：对每个假设，运行一个场景：如果假设错误，该场景会失败。示例：假设"API 对缺失资源返回 404" → 请求一个缺失资源，确认 404。

**修复后隐含假设声明规则**（来自 v1 Post-fix reflection，合并于此）：每次在 VERIFY & QA GATE 中修复缺陷后，如果修复引入了 prompt 未明确指定的行为，必须将该行为声明为新假设并验证。示例：prompt 未指定空输入行为，修复时决定返回 400 → 必须声明假设"空输入返回 400"并验证。这不要求回退 DISCOVER，而是就地声明 + 验证。

**失败恢复路由**：

| 问题 | 路由 |
|------|------|
| 只需调整现有逻辑 | → EXECUTE |
| 测试错误，非代码错误 | → 修验证 → 重跑 Step 2 |
| 环境问题（缺依赖、端口冲突） | → 修环境 → 重跑 Step 2 |
| 需求理解错误 | → DISCOVER / UNDERSTAND（按原因） |
| 需要需求外的信息 | → Oracle → 用户 |

**安全网**：QA GATE 2 次失败 → Oracle → 用户。

#### 6.5.3 Step 3: Success Criteria 清单

Done 当且仅当 ALL 为 true：

1. 用户要求的每个行为都已实现；无部分交付，无"v0 / 后续扩展"
2. `lsp_diagnostics` 在所有修改文件上 clean
3. Build（如适用）exit 0；测试通过，或预存失败已显式说明原因
4. 交付物已通过其使用表面验证（Manual QA Gate）
5. 最终消息报告：做了什么、验证了什么、未能验证什么（含原因）、注意到的预存问题

**Forbidden stops**：
- sub-agent 返回后停止，未逐文件验证其工作
- Success Criteria 未全部满足时停止（尤其 Manual QA Gate）
- 3 次失败后未咨询 Oracle 就停止

**快速通道简写**：只做 Step 1 全量静态检查 + Step 2 的 happy path 验证，不做 assumption 逐条验证和组合路径测试。

---

## 7. QA Gate 体系设计

### 7.1 三支柱模型

v2 的 QA 体系由三个支柱构成，替代 v1 的双层验证（VERIFY + QA GATE）：

```
┌─────────────────────────────────────────────────────────┐
│                    QA Gate 三支柱                        │
├───────────────────┬─────────────────┬───────────────────┤
│  支柱 1           │  支柱 2         │  支柱 3           │
│  Manual QA Gate   │  三尝试失败协议  │  Success Criteria │
│  (按类型验证)      │  (强制换方法)    │  (完成清单)        │
├───────────────────┼─────────────────┼───────────────────┤
│  每次交付物必须    │  每次失败必须    │  每次完成必须      │
│  通过其使用表面    │  换根本不同的    │  全部满足才能      │
│  实际执行验证      │  方法再尝试      │  声明 Done        │
├───────────────────┼─────────────────┼───────────────────┤
│  Tier 1: 可执行   │  Tier 3:        │  Tier 1:          │
│  定义了每种类型    │  todowrite 外部 │  可观察的行为      │
│  的验证工具和步骤  │  计数+method-   │  清单             │
│                  │  category       │                   │
└───────────────────┴─────────────────┴───────────────────┘
```

### 7.2 支柱 1: Manual QA Gate

**核心原则**：`lsp_diagnostics` 抓类型错误不抓逻辑 bug；测试只覆盖作者预期的场景。"Done" = 亲自通过交付物的使用表面操作过，并观察到正确行为。

**按类型验证表**：见 §6.5.2。

**不可跳过**：即使是快速通道任务，也必须做 happy path 验证。

### 7.3 支柱 2: 三尝试失败协议

**核心原则**：失败时换根本不同的方法，而非在同一思路上微调。

**协议**：见 §6.4.4。

**与 v1 的区别**：v1 的"2 次无进展 → 升级"没有强制换方法，agent 可能在同一思路上反复。三尝试协议通过 todowrite 外部计数 + method-category 强制"不同算法/库/模式"。

### 7.4 支柱 3: Success Criteria 清单

**协议**：见 §6.5.3。

---

## 8. Subagent 生态设计

### 8.1 Subagent 清单

| Subagent | opencode 内置？ | 需自建？ | 用途 | deepworker 调用方式 |
|----------|---------------|---------|------|-------------------|
| Explore | ✅ 内置 | 否 | 代码库探索 | `task(subagent_type="explore")` |
| Scout | ✅ 内置 | 否 | 外部依赖研究（≈Librarian） | `task(subagent_type="scout")` |
| Oracle | ❌ | **是** | 对抗审查 / 架构咨询 | `task(subagent_type="oracle")` |

**最小集**：Explore(内置) + Oracle(自建)。Scout 覆盖 Librarian 的部分功能，context7 MCP 补充文档查找。

### 8.2 Oracle Subagent 设计

**文件**：`.opencode/agents/oracle.md` 或 `~/.config/opencode/agents/oracle.md`

**定位**：只读架构顾问。3 次失败后强制咨询，也可在复杂架构决策时按需咨询。

**Prompt 核心指令**：

```
You are Oracle — a read-only architecture consultant. Your job is to attack
conclusions and find errors in reasoning, NOT to implement anything.

When given analysis conclusions, find:
1. Understanding errors — wrong interpretation of requirements
2. Missed ambiguities — multiple valid interpretations not flagged
3. Invalid assumptions — assumptions that wouldn't hold in real usage
4. Unverified constraints — constraints declared but not grounded in evidence
5. Cross-stage inconsistencies — earlier assumptions contradicted by later findings

For each attack: state the specific claim, why it's likely wrong, what the
correct analysis should be.

If you find no challenges after thorough review, say "No challenges found"
with brief reasoning for each major conclusion.
```

**Permission**：read-only（只读）：

```yaml
permission:
  edit: deny
  bash: deny
  task: deny
  read: allow
  glob: allow
  grep: allow
```

**调用时机**：
- **强制**：3 次失败后（三尝试失败协议）
- **按需**：复杂架构决策、多系统权衡、不熟悉的模式
- **不调用**：已读代码可回答的问题、首次尝试决策

**调用格式**（4-field prompt，来自 Hephaestus）：

```
CONTEXT: [what task, which modules, what approach]
GOAL: [what decision the results unblock]
DOWNSTREAM: [how results will be used]
REQUEST: [what to find, format to return, what to skip]
```

### 8.3 Deepworker 对 Subagent 的 Permission

```yaml
permission:
  task:
    "*": deny
    "explore": allow
    "oracle": allow
    "scout": allow
```

---

## 9. Opencode 配置设计

### 9.1 Deepworker Agent 配置

**文件**：`.opencode/agents/deepworker.md` 或 `~/.config/opencode/agents/deepworker.md`

```yaml
---
description: 深度工作 Agent - 目标导向、端到端完成、验证后交付、不半途而废
mode: all
model: AstronCodingPlan/astron-code-latest
temperature: 0.2
steps: 50
hidden: false
color: '#D97706'
permissions:
  - action: edit
    resource: "*"
    effect: allow
  - action: shell
    resource: "*"
    effect: allow
  - action: subagent
    resource: "*"
    effect: deny
  - action: subagent
    resource: explore
    effect: allow
  - action: subagent
    resource: oracle
    effect: allow
  - action: subagent
    resource: scout
    effect: allow
  - action: lsp
    resource: "*"
    effect: allow
  - action: skill
    resource: "*"
    effect: allow
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  - action: webfetch
    resource: "*"
    effect: allow
  - action: websearch
    resource: "*"
    effect: allow
  - action: todowrite
    resource: "*"
    effect: allow
  - action: question
    resource: "*"
    effect: allow
---
```

**关键配置说明**：

| 配置项 | 值 | 理由 |
|-------|---|------|
| mode | `all` | 既可 primary 直接用，也可被 orchestrator 通过 task 调度 |
| steps | 50 | v1 的 66 过大，v2 流程更紧凑，50 足够 |
| temperature | 0.2 | 保持低随机性，确保纪律执行 |
| subagent deny * + allow 特定 | — | 最小权限原则，只允许需要的 subagent |

### 9.2 Oracle Agent 配置

**文件**：`.opencode/agents/oracle.md` 或 `~/.config/opencode/agents/oracle.md`

```yaml
---
description: 对抗审查 - 攻击分析结论，发现遗漏和错误
mode: subagent
model: AstronCodingPlan/astron-code-latest
temperature: 0.3
steps: 15
hidden: true
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: subagent
    resource: "*"
    effect: deny
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
---
```

**关键配置说明**：

| 配置项 | 值 | 理由 |
|-------|---|------|
| mode | `subagent` | 只被 deepworker 调度，不直接交互 |
| hidden | `true` | 不在 @ autocomplete 中显示，只通过 task 调用 |
| steps | 15 | Oracle 只做审查，不需要多步 |
| temperature | 0.3 | 略高于 deepworker，鼓励挑战性思维 |
| edit/shell/task deny | — | 只读，不能修改任何东西 |

### 9.3 Subagent Depth

如果 deepworker 需要通过 Oracle 间接调用 Explore（Oracle 审查时需要读代码），需要 `subagent_depth: 2`。但当前设计 Oracle 是只读的（deny task），不需要嵌套 subagent，因此 `subagent_depth: 1` 足够。

---

## 10. 变更清单

### 10.1 流程变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| F1 | 阶段数 | 7 | 5 | ORACLE ATTACK 移除；VERIFY 合入 VERIFY & QA GATE |
| F2 | 新增 Intent Gate | 无 | 有 | 解决 LLM 字面理解问题 |
| F3 | 新增快速通道 | 无 | 有 | 简单任务简化流程 |
| F4 | 回退路径 | 11 条 | 3 条 | 增量补充替代全量重做 |
| F5 | ORACLE ATTACK | 独立阶段 | 按需 + 失败强制 | 简单任务省掉 Oracle 开销 |
| F6 | Exit Declaration | 每阶段强制完整模板 | 结构化输出（1-3 行） | 减少 token 消耗 |
| F7 | Deep Ambiguity Scan | 4 项独立检查 | 2 轮迭代，Round 2 条件触发 | 降低通用模型认知负荷 |
| F8 | Gap Analysis | 4 步独立流程 | 合入 Assumptions Check | 减少流程步骤 |
| F9 | End-to-End Scenario | PLAN 阶段独立段落 | 合入 Assumptions Check Round 2 | 与跨函数一致性检查触发条件相同，合并消除冗余 |
| F9 | 失败恢复 | 2 次无进展→升级 | 三尝试失败协议 + todowrite 外部计数 | 强制换方法 + 可追踪 |
| F10 | Steps budget | 66 | 50 | 流程更紧凑 |
| F11 | Drift detection | prompt 自律 | todowrite header 锚定 + 用户可观察 | 可执行性提升 |
| F12 | 快速通道判定 | 无 | DISCOVER Step 1 后一次性判定 | 消除锚定效应 |
| F13 | Subagent 触发 | 模型主观判断 | 布尔检查表 + MUST 逻辑 | 消除主观判断 |
| F14 | VERIFY + QA GATE | 两个独立阶段 | 合并为 VERIFY & QA GATE | 减少阶段间开销 |
| F15 | todowrite 使用范围 | 未明确 | PLAN 阶段开始使用 | 交付物驱动，非流程控制 |
| F16 | 新增模型能力适配层 | 无 | Tier 1/2/3 机制分级 | 通用模型可用性 |
| F17 | Post-fix reflection | QA GATE 独立规则 | 合入 Assumption verification | 修复引入未指定行为必须声明为新假设 |
| F18 | Workspace declaration | DISCOVER Exit | 保留 | 事前记录工作区状态 |

### 10.2 QA 变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| Q1 | Manual QA Gate | Surface Verification（抽象） | 按类型验证表（可执行） | Hephaestus 验证有效 |
| Q2 | Success Criteria | QA GATE 5 条 pass condition | 5 条清单 + Forbidden stops | 更简洁 + 更严格 |
| Q3 | VERIFY 阶段 | 独立阶段 | 合入 VERIFY & QA GATE Step 1 | 减少阶段间开销，逻辑隐含在 Success Criteria 中 |
| Q4 | TDD 降级 | 无 | 2 次 Red 失败→降级 direct | 避免 LLM 在测试本身上卡住 |
| Q5 | TDD 判定粒度 | 隐式 step 级 | 显式 step 级 + 封闭列表 | 比任务级分级更客观清晰 |

### 10.3 配置变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| C1 | mode | all | all | 不变 |
| C2 | steps | 66 | 50 | 流程更紧凑 |
| C3 | permission 格式 | V1 object | V2 permissions array | 对齐 opencode V2 |
| C4 | Oracle subagent | 无 | 新建 | 支撑按需 Oracle 咨询 |
| C5 | call_omo_agent deny | 有 | 移除（V2 无此 key） | 对齐 opencode V2 |

### 10.4 保留项（不变）

- Ambiguity Scan 5 模式 + Evaluation rule + Flagged ambiguity resolution rule
- TDD default rule（step 级判定）+ Red quality levels + `[direct]` 封闭列表
- Constraint anchor
- Consumer Identification（分轻量 grep + 深度 subagent 两级）
- Post-Edit Verification
- Deletion Declaration
- Staged Area Check
- Sub-agent 4-field prompt (CONTEXT/GOAL/DOWNSTREAM/REQUEST)
- 并行执行原则
- Absolute prohibitions（不伪造验证结果、不修改 lint/type 规则压制错误）

---

## 11. 风险与缓解

| # | 风险 | 概率 | 影响 | 缓解 |
|---|------|------|------|------|
| R1 | 轻流程导致理解不足就动手 | 中 | 高 | Intent Gate + Ambiguity Scan 仍在前置；2x effort rule 保留 |
| R2 | 三尝试失败协议中 agent 不换方法 | 中→低 | 中 | todowrite method-category 外部可审查；同类切换需核心机制不同；Oracle 审查时检查方法差异 |
| R3 | Manual QA Gate 被跳过 | 低 | 高 | Success Criteria 清单中 Manual QA 是硬条件；Forbidden stops 明确禁止跳过 |
| R4 | 快速通道误判 | 低 | 中 | DISCOVER Step 1 后基于代码证据一次性判定；5 个条件全部可观察事实 |
| R5 | Oracle subagent 质量不足 | 低 | 中 | Oracle temperature 0.3 鼓励挑战性；hidden: true 避免用户误用 |
| R6 | V2 permissions 格式兼容性 | 低 | 低 | 确认 opencode 版本；如不支持 V2 格式则回退 V1 |
| R7 | Drift detection 依赖模型自律 | 中 | 中 | todowrite header 锚定降低自律要求；用户可观察形成软约束；无外部自动检测（opencode 当前不支持） |
| R8 | Subagent 启动检查表被敷衍 | 中 | 中 | 布尔逻辑比主观判断更难钻空子；检查表外部可观察 |
| R9 | DeepSeek-V4 XML tool-call 格式与 opencode JSON schema 不兼容 | 低 | 高 | 部署前验证兼容性；不兼容时降级为 JSON 格式或切换模型 |
| R10 | Kimi K3 thinking history 缺失导致质量不稳定 | 中 | 中 | 部署前验证 opencode subagent 是否保留完整 thinking blocks |

---

## 12. 附录

### 12.1 v1 → v2 流程映射

| v1 阶段 | v2 阶段 | 变化 |
|---------|---------|------|
| UNDERSTAND | Phase 1: UNDERSTAND | 新增 Intent Gate；Ambiguity Scan 保留但输出简化；快速通道初判取消 |
| DISCOVER | Phase 2: DISCOVER | 广搜改为条件触发；Deep Ambiguity Scan + Gap Analysis 合并为 2 轮迭代 Assumptions Check；新增 Subagent 启动检查表；新增快速通道一次性判定 |
| ORACLE ATTACK | (移除独立阶段) | Oracle 变为按需咨询 + 3 次失败后强制 |
| PLAN | Phase 3: PLAN | todowrite 从此阶段开始使用；TDD 判定粒度显式 step 级 |
| PLAN End-to-End Scenario | Phase 2: DISCOVER Step 3 | 合入 Assumptions Check Round 2（调用链数据流一致性） |
| EXECUTE | Phase 4: EXECUTE | VERIFY 不再合入循环，Post-Edit Verification 保留 v1；三尝试协议改为 todowrite 外部计数；Drift detection 改为 todowrite header 锚定 |
| VERIFY | Phase 5: VERIFY & QA GATE Step 1 | 合并入 VERIFY & QA GATE，作为 Step 1 |
| QA GATE | Phase 5: VERIFY & QA GATE Step 2-3 | 合并入 VERIFY & QA GATE，按类型验证表替代抽象 Surface Verification |

### 12.2 Hephaestus 特性采纳决策

| Hephaestus 特性 | 采纳？ | 理由 | 适配措施 |
|----------------|-------|------|---------|
| Intent Gate 意图表 | ✅ 是 | 解决 LLM 字面理解问题 | Tier 1，直接可用 |
| Discovery "启动一次广搜"策略 | ⚠️ 部分 | 比先广搜再检查更高效 | 改为先定向读取做 Round 1，再根据结果决定广搜 |
| Operating Loop 短循环 | ✅ 是 | 替代线性 7 阶段，更符合编码节奏 | — |
| Manual QA Gate 按类型验证 | ✅ 是 | 比 Surface Verification 更具体可执行 | Tier 1 |
| 三尝试失败协议 | ✅ 是 | 比回退表更实际，强制换方法 | Tier 3，todowrite 外部计数 + method-category |
| Success Criteria 清单 | ✅ 是 | 比 QA GATE pass condition 更简洁 | Tier 1 |
| "Default to not add tests" | ❌ 否 | 与 deepworker 质量标准不可接受 | — |
| "Skip planning for easiest 25%" | ⚠️ 部分 | 保留 PLAN 但允许简写，不跳过 | 快速通道任务简写 PLAN |
| Oracle 可选 | ❌ 否 | 保留 Oracle 价值但简化为按需 + 失败强制 | — |
| 激进并行 | ✅ 是 | 所有独立工具调用并行执行 | — |

### 12.3 术语表

| 术语 | 定义 |
|------|------|
| Intent Gate | 意图分类机制，将用户表面表达映射为真实意图和行动 |
| Manual QA Gate | 通过交付物的实际使用表面验证功能正确性的关卡 |
| 三尝试失败协议 | 3 次不同方法失败后强制 Oracle → 用户的恢复协议，通过 todowrite Failure Log 外部追踪 |
| Success Criteria | Done 的充要条件清单 |
| 快速通道 | 简单任务的简化流程路径，DISCOVER Step 1 后一次性判定 |
| Assumptions Check | 替代 Deep Ambiguity Scan + Gap Analysis，2 轮迭代，Round 2 含跨函数语义一致性 + 调用链数据流一致性 + 运行时假设 |
| Constraint anchor | PLAN 阶段声明的约束，作为后续漂移检测的锚，存储在 todowrite Plan Anchor header |
| Drift detection | todowrite header 锚定 + 用户可观察的漂移检测机制 |
| Plan Anchor | todowrite header 中的 Goal + Constraints + Steps 计数，作为漂移检测锚 |
| Failure Log | todowrite 中的失败记录，包含 failure #、approach、error、method-category |
| method-category | 5 类方法分类（algorithm/library/pattern/api-design/approach），用于判断是否"换了根本不同方法" |
| Subagent 启动检查表 | 布尔逻辑驱动的 subagent 启动判定机制，替代主观判断 |
| 模型能力适配层 | 按机制对模型能力的依赖程度分为 Tier 1/2/3，决定适配措施 |
| 调用链数据流一致性 | Assumptions Check Round 2 检查项，确认函数间数据流匹配（A 输出是否匹配 B 输入预期） |
| 修复后隐含假设声明 | QA 修复引入 prompt 未指定行为时，必须声明为新假设并验证 |

### 12.4 参考文档

- deepworker v1: https://github.com/cireric/workflows/blob/main/agents/deepworker.md
- Hephaestus 架构: `docs/research/agent-deepworker/hephaestus-architecture.md`
- oh-my-openagent: https://github.com/code-yeongyu/oh-my-openagent
- opencode agents 文档: https://opencode.ai/docs/agents
- opencode config 文档: https://opencode.ai/docs/config

### 12.5 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-23 | 初始版本，基于 deepworker v1 + Hephaestus 对比分析 |
| v2.0 | 2026-07-24 | 基于模型通用性拷问的重大修订：新增模型能力适配层（Tier 1/2/3）；三尝试协议改为 todowrite 外部计数；Drift detection 改为 todowrite header 锚定；Assumptions Check 拆 2 轮迭代；快速通道判定改为 DISCOVER Step 1 后一次性判定；Subagent 启动检查表；TDD 判定粒度显式 step 级；VERIFY + QA GATE 合并；todowrite 使用范围明确为 PLAN 阶段开始；阶段名恢复为 5 阶段 UNDERSTAND → DISCOVER → PLAN → EXECUTE → VERIFY & QA GATE |
| v2.1 | 2026-07-24 | v1 提示词差异点确认：End-to-End Scenario 合入 Assumptions Check Round 2（调用链数据流一致性）；Post-fix reflection 合入 Assumption verification（修复后隐含假设声明）；Workspace declaration 保留于 DISCOVER 统一输出 |
