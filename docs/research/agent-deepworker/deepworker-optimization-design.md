# Deepworker Agent 优化需求设计文档

> **来源**: deepworker.md (cireric/workflows) + Hephaestus (oh-my-openagent) 对比分析
> **创建日期**: 2026-07-23
> **文档版本**: v1.0
> **状态**: Draft

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [现状分析](#2-现状分析)
3. [设计原则](#3-设计原则)
4. [流程重设计](#4-流程重设计)
5. [各阶段详细设计](#5-各阶段详细设计)
6. [QA Gate 体系设计](#6-qa-gate-体系设计)
7. [Subagent 生态设计](#7-subagent-生态设计)
8. [Opencode 配置设计](#8-opencode-配置设计)
9. [变更清单](#9-变更清单)
10. [风险与缓解](#10-风险与缓解)
11. [附录](#11-附录)

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

### 1.2 参考基准

Hephaestus (omo) 的 GPT-5.5 提示词验证了一个关键假设：**"轻流程 + 重 QA Gate"比"重流程 + 轻 QA"更可靠**。其证据：

- Manual QA Gate 按交付物类型定义验证方式，可执行性强
- 三尝试失败协议强制换方法，避免同一思路上反复
- Operating Loop 短循环（Explore→Plan→Implement→Verify→QA）符合实际编码节奏
- Success Criteria 清单比复杂 pass condition 更简洁有效

### 1.3 优化目标

| 指标 | v1 (当前) | v2 (目标) | 改善幅度 |
|------|----------|----------|---------|
| 阶段数 | 7 | 5 | -29% |
| 回退路径 | 11 条 | 3 条 | -73% |
| Exit Declaration | 每阶段强制完整模板 | 条件强制 + 增量声明 | token -60% |
| Oracle 开销 | 每次任务 3 轮 | 按需（3 次失败后强制） | 简单任务 -100% |
| Steps budget | 66 | 50 | -24% |
| QA 强度 | 双层但抽象 | 三支柱 + 按类型验证 | 可执行性 +↑ |

---

## 2. 现状分析

### 2.1 Deepworker v1 流程

```
UNDERSTAND → DISCOVER → ORACLE ATTACK → PLAN → EXECUTE → VERIFY → QA GATE → Done
     ↑           ↑            ↑                    ↑        ↑        ↑
     └───────────┴────────────┴────────────────────┴────────┴────────┘
                        11 条回退路径
```

### 2.2 Hephaestus 流程

```
Intent Gate → Discovery & Retrieval → Operating Loop → Done
                                      ┌──────────────────────────────┐
                                      │ Explore → Plan → Implement → │
                                      │ Verify → Manual QA           │
                                      └──────────────────────────────┘
                                           (短循环，可多轮)
```

### 2.3 关键差异对比

| 维度 | deepworker v1 | Hephaestus | v2 取向 |
|------|-------------|-----------|---------|
| **流程结构** | 线性 7 阶段 + 回退表 | 3 层（Intent→Discovery→Loop） | 5 阶段 + 短循环 |
| **歧义处理** | 5 模式扫描 + Deep Scan + Gap Analysis | Intent Gate 意图表 + Assumptions Check | 两者融合 |
| **Oracle** | 独立阶段，强制 3 轮 | 按需咨询，3 次失败后强制 | 按需 + 失败强制 |
| **TDD** | 强制 default，direct 仅限封闭列表 | 无 TDD 要求，"Default to not add tests" | 保留 TDD 偏好 + 快速降级 |
| **验证** | VERIFY(静态) + QA GATE(功能) 分离 | lsp_diagnostics + Manual QA Gate | 合并为循环 + Manual QA |
| **Exit Declaration** | 每阶段强制完整模板 | 无 | 条件强制 + 增量声明 |
| **回退** | 11 条显式路径 | 就地修复 + 3 次失败协议 | 3 条路径 |
| **并行** | sub-agent 并行（默认） | 激进并行（所有独立调用） | 继承激进并行 |

### 2.4 v1 保留项 vs 新增项 vs 简化项

| 类别 | 具体内容 |
|------|---------|
| **保留** | Ambiguity Scan 5 模式、TDD default rule、Constraint anchor、Drift detection、Consumer Identification、Post-Edit Verification、Deletion Declaration、Staged Area Check |
| **新增** | Intent Gate（来自 Hephaestus）、Manual QA Gate 按类型验证表（来自 Hephaestus）、三尝试失败协议（来自 Hephaestus）、Success Criteria 清单（来自 Hephaestus）、快速通道（简单任务简化流程） |
| **简化** | Exit Declaration → 条件强制 + 增量声明、ORACLE ATTACK → 按需 + 失败强制、Deep Ambiguity Scan 4 项 → 合并到 DISCOVER 流程中、Gap Analysis → 简化为 Assumptions Check、回退路径 11 条 → 3 条、Steps 66 → 50 |

---

## 3. 设计原则

### P1: 轻流程 + 重 QA Gate

流程的重量从"过程控制"转移到"结果验证"。阶段间松散过渡，只在关键决策点设卡。验证行为通过工具调用强制，而非通过模板格式约束。

**含义**：
- 去掉每阶段强制 Exit Declaration，改为关键决策点声明
- 强化 Manual QA Gate 为不可跳过的硬关卡
- 用 Success Criteria 清单替代复杂的 pass condition

### P2: 增量而非全量

回退时增量补充，不全量重做。新发现的信息追加到已有结论，而非重新执行整个阶段。

**含义**：
- DISCOVER → INTENT+UNDERSTAND 回退时，只补充新歧义
- EXECUTE 循环内就地修复，不回退到 PLAN
- 假设列表追加而非重建

### P3: 按需而非强制

高成本操作（Oracle、完整 Exit Declaration、Deep Ambiguity Scan）按需触发，而非每次任务都执行。

**含义**：
- Oracle 在 3 次失败后强制，而非每次任务必跑
- Exit Declaration 只在产出关键决策时要求完整模板
- Deep Ambiguity Scan 在 DISCOVER 中自然执行，不作为独立检查清单

### P4: 可执行优于可声明

规则必须能通过工具调用或行为观察来验证，而非仅靠 prompt 文本约束。

**含义**：
- Manual QA Gate 定义按交付物类型的验证方式（可执行）
- Success Criteria 是可观察的行为（可验证）
- 三尝试失败协议有明确的计数和行动（可追踪）

---

## 4. 流程重设计

### 4.1 v2 整体流程

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: INTENT + UNDERSTAND                                │
│   - Intent Classification (Hephaestus 意图表)               │
│   - Ambiguity Scan (5 模式，简化版)                          │
│   - 2x effort difference → ask user                         │
│   输出：Goal + Scope + Assumptions (1-3 行)                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: DISCOVER (广搜一次 + 条件追加)                      │
│   - 并行 2-5 explore/librarian + 直接读                      │
│   - Consumer Identification                                 │
│   - Assumptions Check (简化版 Gap Analysis)                  │
│   输出：Confirmed facts + Assumptions (1-3 行)               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: PLAN                                               │
│   - 文件列表 + 变更描述 + 依赖                               │
│   - TDD/direct 标注                                         │
│   - 约束锚定                                                │
│   - 简单任务允许简写                                         │
│   输出：Execution Plan (结构化)                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: EXECUTE + VERIFY (循环)                            │
│   ┌──────────────────────────────────────┐                  │
│   │  Implement → Post-Edit Verify        │                  │
│   │      ↑            │                  │                  │
│   │      └── 修复 ←───┘                  │                  │
│   └──────────────────────────────────────┘                  │
│   - TDD 纪律 (Red/Green/Refactor)                           │
│   - Drift detection                                         │
│   - 2 次失败 → 换方法                                       │
│   - 3 次失败 → Oracle → 用户                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: QA GATE (Manual QA)                                │
│   - 按交付物类型执行验证 (验证表)                             │
│   - Assumption 逐条验证                                     │
│   - 非显然组合路径测试 (≥2 函数共享概念时)                    │
│   - 失败 → 就地修复 → 重入 Phase 4                          │
│   输出：Pass/Fail + evidence                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
                     Done
```

### 4.2 快速通道

简单任务（满足以下全部条件）可跳过 Phase 3 (PLAN) 和 Phase 5 的部分检查：

**快速通道条件**（全部满足才适用）：
- 单文件变更
- ≤3 步操作
- 无歧义（Intent Gate 判定为 explicit）
- 无跨函数共享概念

**快速通道流程**：
```
INTENT+UNDERSTAND → DISCOVER(简写) → EXECUTE+VERIFY → Manual QA(简写) → Done
```

**简写规则**：
- DISCOVER：直接读目标文件 + 1 个 explore agent，不做 Consumer ID 和 Assumptions Check
- Manual QA：只做 happy path 验证，不做 assumption 逐条验证和组合路径测试

### 4.3 回退路径（3 条）

| # | 触发条件 | 路径 | 行为 |
|---|---------|------|------|
| 1 | EXECUTE 内单步验证失败 | 就地修复 → 重验证 | 不离开 Phase 4 |
| 2 | 3 次不同方法均失败 | Oracle 咨询 → 再尝试 1 次 | Oracle 结果指导修复 |
| 3 | Oracle 后仍失败 | 问用户 1 个精确问题 | 最后手段 |

**与 v1 的关键区别**：不再回退到早期阶段（UNDERSTAND/DISCOVER/PLAN）。原因：
- 回退到早期阶段意味着全量重做，token 成本极高
- 实际中，理解错误在 EXECUTE 阶段通过 Oracle 咨询即可修正
- 如果确实需要重新理解，Oracle 会指出，此时再增量补充

### 4.4 循环终止

| 条件 | 行动 |
|------|------|
| Success Criteria 全部满足 | Done |
| Phase 4 循环 3 次无进展 | → Oracle |
| Oracle 后 1 次仍无进展 | → 用户 |
| Phase 5 QA GATE 2 次失败 | → Oracle → 用户 |

---

## 5. 各阶段详细设计

### 5.1 Phase 1: INTENT + UNDERSTAND

**目的**：确定用户真实意图 + 识别歧义。纯语义推理，不做代码探索。

#### 5.1.1 Intent Classification（新增，来自 Hephaestus）

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

#### 5.1.2 Ambiguity Scan（保留 v1，简化输出）

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

**输出简化**（不再要求完整模板）：

```
Goal: [理解]
Ambiguity: [none | '[term]' → [interpretation] (assumption) | '[term]' → asked user, confirmed [interpretation]]
Scope: [in / out]
```

#### 5.1.3 快速通道判定

在此阶段末尾判定是否进入快速通道。判定条件见 4.2。

### 5.2 Phase 2: DISCOVER

**目的**：建立完整心智模型。代码感知推理——所有需要读代码的检查在此执行。

#### 5.2.1 广搜策略（来自 Hephaestus）

**启动一次广搜**：并行发射 2-5 个 explore/librarian sub-agent（`run_in_background=true`）+ 直接读已知相关文件。目标：第一次编辑前建立完整心智模型。

**追加条件**（仅当满足时才追加检索）：
- 首批没回答核心问题未回答
- 缺关键事实（文件路径、类型、所有者、约定）
- 二阶信息浮现（调用者、错误路径、副作用）
- 需要特定文档/源码/commit

**停止条件**：足够上下文 / 信息重复 / 2 轮无新数据

**不重复已委托的搜索**：一旦委托 explore agent 搜索，自己不再搜同一内容。

#### 5.2.2 Consumer Identification（保留 v1）

1. 代码搜索：搜索被修改代码的引用/调用/导入
   - 找到 → 记录为 confirmed fact
   - 未找到 → 进入步骤 2
2. 概念推断：从任务描述和交付物类型推断消费者
   - 可推断 → 记录为 assumption
   - 不可推断 → 记录为 blocked

#### 5.2.3 Assumptions Check（简化版 Gap Analysis）

替代 v1 的 Deep Ambiguity Scan (4 项) + Gap Analysis (4 步)。合并为单一检查：

1. **重新评估 UNDERSTAND 歧义**：有代码证据后，之前的歧义判断是否变化？
2. **代码结构歧义**：代码揭示了哪些 prompt 未覆盖的歧义？
3. **跨函数一致性**：≥2 函数共享概念时，实现解释是否一致？不一致且 effort ≥2x → 标记
4. **运行时假设**：依赖外部资源/运行时条件时，行为是否指定？

每项结果简写：`[updated: X / no change / N/A]`、`[N ambiguities: list / none]`

**输出**：

```
Facts: [N confirmed, with evidence source]
Consumer: [confirmed/assumed/blocked]
Assumptions: [list of atomic, testable propositions]
Scope: [in / out]
```

**如果发现新歧义**：增量补充到 Phase 1 的结论，不回退重做整个 UNDERSTAND。仅当歧义满足 2x effort rule 时才 ask user。

### 5.3 Phase 3: PLAN

**目的**：承诺执行路径。此计划是漂移检测锚和约束再注入源。

#### 5.3.1 输出格式

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

#### 5.3.2 TDD Default Rule（保留 v1，增加快速降级）

**Default mode = `[TDD]`**。`[direct]` 仅当步骤不创建新的可测试行为时使用，且必须声明原因。

`[direct]` 封闭列表：CONFIG、VERIFY、FIXTURE、ANNOTATE、ENTRY。

**快速降级**（新增）：如果 Red 阶段 2 次仍无法写出有效测试 → 降级为 direct 模式，在 EXECUTE 后补测试。降级时声明："Red quality: 2 attempts failed,降级为 direct。将在 EXECUTE 后补测试。"

**Red quality levels 保留**：
- Infrastructure Red（ImportError）：有效但弱
- Behavioral Red（AssertionError）：有效且强
- 目标：每个 TDD cycle 追求 Behavioral Red

#### 5.3.3 粒度规则

- 最大 10 步，超过则拆分任务
- 最小粒度：每个独立交付物（有独立可测试行为的函数/类）必须是单独步骤
- 最大合并：2 个相关交付物/步骤（如 interface + implementation 同文件）

#### 5.3.4 简单任务简写

快速通道任务：Plan 可简写为 1-2 行——"修改 [file] 的 [function]，[what change]。[TDD/direct]。"

### 5.4 Phase 4: EXECUTE + VERIFY

**目的**：按 PLAN 执行代码修改。每个编辑后立即验证，形成紧密循环。

#### 5.4.1 TODO Iron Law（保留 v1）

| 规则 | 描述 |
|------|------|
| Step tracking | PLAN path → todo list，constraints summary 作为固定 header |
| Single-step focus | 同一时间只有 1 个 `in_progress` |
| Completion marking | 每步完成后立即标记 `completed`，不批量 |
| Drift detection | 每步后对照 PLAN 检查 |
| Post-edit verification | 每次编辑后验证（见下） |
| Constraint capture | 新约束 → 记录到 TODO + 更新 PLAN Constraints |
| Assumption tracking | 假设变更 → 更新 PLAN Constraints 计数 |

#### 5.4.2 Post-Edit Verification（保留 v1）

每次文件编辑后：
1. `lsp_diagnostics` on changed files → 不可用或误报时用项目 type-check CLI
2. 项目 lint tool on changed files
3. 错误：auto-fix 可用时修复，验证无行为变更
4. 剩余：手动修复。代码缺陷 → 修代码（不压制规则）。误报 → 最小范围抑制

#### 5.4.3 TDD Enhancement（保留 v1，增加降级）

当步骤标记 `[TDD]` 时：
1. **Red**：写失败测试指定期望行为
2. **Green**：写最小代码通过
3. **Refactor**：清理，保持测试绿

**Red validity criterion 保留**（HARD RULE）。

**快速降级**：2 次 Red 失败 → 声明降级 → direct 模式 → EXECUTE 后补测试。

#### 5.4.4 失败恢复（重设计，来自 Hephaestus）

**三尝试失败协议**：

```
第 1 次失败 → 换一种根本不同的方法（不同算法/库/模式，非微调）
第 2 次失败 → 再换一种方法
第 3 次失败 → STOP
  ├─ revert 到已知良好状态
  ├─ 记录 3 次尝试及失败原因
  ├─ 咨询 Oracle（同步，完整失败上下文）
  └─ Oracle 后再尝试 1 次
       ├─ 成功 → 继续
       └─ 失败 → 问用户 1 个精确问题
```

**Stall 定义**：2 个 edit-verify 循环诊断不变 = stall。Stall 时按失败恢复协议处理。

**Drift 处理**：
- Minor（步骤顺序、细节）→ 允许 + 更新
- Major（跳步、改目标）→ 暂停；明显更好 → 更新 + 继续；不确定 → ask user
- Constraint decay → 再注入原始路径

### 5.5 Phase 5: QA GATE (Manual QA)

**目的**：功能正确性关卡——交付物必须实际可用，而非仅通过静态检查。

#### 5.5.1 Pass Conditions（ALL must be true）

1. **Phase 4 验证通过**：所有可用检查通过
2. **Surface verification**：交付物通过实际使用表面正常工作
3. **Assumption verification**：每个假设的实现正确覆盖
4. **Non-obvious combination**（≥2 函数共享概念时）：至少 1 个组合路径测试
5. **No known unresolved issues**

#### 5.5.2 Manual QA Gate 按类型验证表（新增，来自 Hephaestus）

| 交付物类型 | 验证方式 | 工具 |
|-----------|---------|------|
| CLI / 脚本 / shell binary | 启动运行：happy path + 1 个错误输入 + `--help` | `interactive_bash` (tmux) |
| Web / 浏览器 UI | 打开页面、点击元素、填充表单、观察控制台 | playwright skill |
| HTTP API / 运行服务 | 用 `curl` 或驱动脚本调用 | bash |
| Library / SDK / 模块 | 写最小驱动脚本 import 并执行 | bash + edit |
| 无匹配表面 | 问自己：真实用户怎么发现这东西能用？照做 | 按场景选择 |

**关键规则**：读源码然后说"这应该能工作" ≠ 通过。必须执行并观察正确行为。

#### 5.5.3 Assumption Verification Method

对每个假设，运行一个场景：如果假设错误，该场景会失败。

示例：假设"API 对缺失资源返回 404" → 请求一个缺失资源，确认 404。

#### 5.5.4 QA GATE 失败恢复

| 问题 | 路由 |
|------|------|
| 只需调整现有逻辑 | → Phase 4 EXECUTE |
| 测试错误，非代码错误 | → 修验证 → 重跑 QA GATE |
| 环境问题（缺依赖、端口冲突） | → 修环境 → 重跑 QA GATE |
| 需要需求外的信息 | → Oracle → 用户 |

**安全网**：QA GATE 2 次失败 → Oracle → 用户。

---

## 6. QA Gate 体系设计

### 6.1 三支柱模型

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
│  可执行：定义了    │  可追踪：3 次    │  可观察：每条      │
│  每种类型的验证    │  计数 + 强制    │  都是可观察的      │
│  工具和步骤        │  行动            │  行为             │
└───────────────────┴─────────────────┴───────────────────┘
```

### 6.2 支柱 1: Manual QA Gate

**核心原则**：`lsp_diagnostics` 抓类型错误不抓逻辑 bug；测试只覆盖作者预期的场景。"Done" = 亲自通过交付物的使用表面操作过，并观察到正确行为。

**按类型验证表**：见 5.5.2。

**不可跳过**：即使是快速通道任务，也必须做 happy path 验证。

### 6.3 支柱 2: 三尝试失败协议

**核心原则**：失败时换根本不同的方法，而非在同一思路上微调。

**协议**：见 5.4.4。

**与 v1 的区别**：v1 的"2 次无进展 → 升级"没有强制换方法，agent 可能在同一思路上反复。三尝试协议强制"不同算法/库/模式"。

### 6.4 支柱 3: Success Criteria 清单

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

---

## 7. Subagent 生态设计

### 7.1 Subagent 清单

| Subagent | opencode 内置？ | 需自建？ | 用途 | deepworker 调用方式 |
|----------|---------------|---------|------|-------------------|
| Explore | ✅ 内置 | 否 | 代码库探索 | `task(subagent_type="explore")` |
| Scout | ✅ 内置 | 否 | 外部依赖研究（≈Librarian） | `task(subagent_type="scout")` |
| Oracle | ❌ | **是** | 对抗审查 / 架构咨询 | `task(subagent_type="oracle")` |

**最小集**：Explore(内置) + Oracle(自建)。Scout 覆盖 Librarian 的部分功能，context7 MCP 补充文档查找。

### 7.2 Oracle Subagent 设计

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

**Permission**：read-only（只读）**：

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

### 7.3 Deepworker 对 Subagent 的 Permission

```yaml
permission:
  task:
    "*": deny
    "explore": allow
    "oracle": allow
    "scout": allow
```

---

## 8. Opencode 配置设计

### 8.1 Deepworker Agent 配置

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

### 8.2 Oracle Agent 配置

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

### 8.3 Subagent Depth

如果 deepworker 需要通过 Oracle 间接调用 Explore（Oracle 审查时需要读代码），需要 `subagent_depth: 2`。但当前设计 Oracle 是只读的（deny task），不需要嵌套 subagent，因此 `subagent_depth: 1` 足够。

---

## 9. 变更清单

### 9.1 流程变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| F1 | 阶段数 | 7 | 5 | UNDERSTAND+DISCOVER 可合并；VERIFY 合入 EXECUTE 循环 |
| F2 | 新增 Intent Gate | 无 | 有 | 解决 LLM 字面理解问题 |
| F3 | 新增快速通道 | 无 | 有 | 简单任务不需要完整流程 |
| F4 | 回退路径 | 11 条 | 3 条 | 增量补充替代全量重做 |
| F5 | ORACLE ATTACK | 独立阶段 | 按需 + 失败强制 | 简单任务省掉 Oracle 开销 |
| F6 | Exit Declaration | 每阶段强制完整模板 | 条件强制 + 增量声明 | 减少 token 消耗 |
| F7 | Deep Ambiguity Scan | 4 项独立检查 | 合入 DISCOVER 流程 | 减少流程步骤 |
| F8 | Gap Analysis | 4 步独立流程 | 简化为 Assumptions Check | 减少流程步骤 |
| F9 | 失败恢复 | 2 次无进展→升级 | 三尝试失败协议 | 强制换方法 |
| F10 | Steps budget | 66 | 50 | 流程更紧凑 |

### 9.2 QA 变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| Q1 | Manual QA Gate | Surface Verification（抽象） | 按类型验证表（可执行） | Hephaestus 验证有效 |
| Q2 | Success Criteria | QA GATE 5 条 pass condition | 5 条清单 + Forbidden stops | 更简洁 + 更严格 |
| Q3 | VERIFY 阶段 | 独立阶段 | 合入 EXECUTE 循环 | 每次编辑后立即验证更实际 |
| Q4 | TDD 降级 | 无 | 2 次 Red 失败→降级 direct | 避免 LLM 在测试本身上卡住 |

### 9.3 配置变更

| # | 变更 | v1 | v2 | 理由 |
|---|------|----|----|------|
| C1 | mode | all | all | 不变 |
| C2 | steps | 66 | 50 | 流程更紧凑 |
| C3 | permission 格式 | V1 object | V2 permissions array | 对齐 opencode V2 |
| C4 | Oracle subagent | 无 | 新建 | 支撑按需 Oracle 咨询 |
| C5 | call_omo_agent deny | 有 | 移除（V2 无此 key） | 对齐 opencode V2 |

### 9.4 保留项（不变）

- Ambiguity Scan 5 模式 + Evaluation rule + Flagged ambiguity resolution rule
- TDD default rule + Red quality levels + `[direct]` 封闭列表
- Constraint anchor + Drift detection
- Consumer Identification
- Post-Edit Verification
- TODO Iron Law
- Deletion Declaration
- Staged Area Check
- Sub-agent 4-field prompt (CONTEXT/GOAL/DOWNSTREAM/REQUEST)
- 并行执行原则
- Absolute prohibitions（不伪造验证结果、不修改 lint/type 规则压制错误）

---

## 10. 风险与缓解

| # | 风险 | 概率 | 影响 | 缓解 |
|---|------|------|------|------|
| R1 | 轻流程导致理解不足就动手 | 中 | 高 | Intent Gate + Ambiguity Scan 仍在前置；2x effort rule 保留 |
| R2 | 三尝试失败协议中 agent 不换方法 | 中 | 中 | Prompt 中明确"不同算法/库/模式，非微调"；Oracle 审查时检查方法差异 |
| R3 | Manual QA Gate 被跳过 | 低 | 高 | Success Criteria 清单中 Manual QA 是硬条件；Forbidden stops 明确禁止跳过 |
| R4 | 快速通道误判（简单任务实际复杂） | 中 | 中 | 快速通道条件严格（单文件+≤3步+无歧义+无共享概念）；执行中发现复杂可退出快速通道 |
| R5 | Oracle subagent 质量不足 | 低 | 中 | Oracle temperature 0.3 鼓励挑战性；hidden: true 避免用户误用 |
| R6 | V2 permissions 格式兼容性 | 低 | 低 | 确认 opencode 版本；如不支持 V2 格式则回退 V1 |

---

## 11. 附录

### 11.1 v1 → v2 流程映射

| v1 阶段 | v2 阶段 | 变化 |
|---------|---------|------|
| UNDERSTAND | Phase 1: INTENT + UNDERSTAND | 新增 Intent Gate；Ambiguity Scan 保留但输出简化 |
| DISCOVER | Phase 2: DISCOVER | 广搜策略来自 Hephaestus；Deep Ambiguity Scan + Gap Analysis 合并为 Assumptions Check |
| ORACLE ATTACK | (移除独立阶段) | Oracle 变为按需咨询 + 3 次失败后强制 |
| PLAN | Phase 3: PLAN | 保留，增加简单任务简写 |
| EXECUTE | Phase 4: EXECUTE + VERIFY | VERIFY 合入循环；失败恢复改为三尝试协议 |
| VERIFY | Phase 4: EXECUTE + VERIFY | 不再独立，每次编辑后立即验证 |
| QA GATE | Phase 5: QA GATE (Manual QA) | 按类型验证表替代抽象 Surface Verification |

### 11.2 Hephaestus 特性采纳决策

| Hephaestus 特性 | 采纳？ | 理由 |
|----------------|-------|------|
| Intent Gate 意图表 | ✅ 是 | 解决 LLM 字面理解问题，比 Vague Verb 模式更实用 |
| Discovery "启动一次广搜"策略 | ✅ 是 | 比"DISCOVER 阶段做完所有探索"更实际 |
| Operating Loop 短循环 | ✅ 是 | 替代线性 7 阶段，更符合编码节奏 |
| Manual QA Gate 按类型验证 | ✅ 是 | 比 Surface Verification 更具体可执行 |
| 三尝试失败协议 | ✅ 是 | 比回退表更实际，强制换方法 |
| Success Criteria 清单 | ✅ 是 | 比 QA GATE pass condition 更简洁 |
| "Default to not add tests" | ❌ 否 | 与 deepworker 质量标准不可接受 |
| "Skip planning for easiest 25%" | ⚠️ 部分 | 保留 PLAN 但允许简写，不跳过 |
| Oracle 可选 | ❌ 否 | 保留 Oracle 价值但简化为按需 + 失败强制 |
| 激进并行 | ✅ 是 | 所有独立工具调用并行执行 |

### 11.3 术语表

| 术语 | 定义 |
|------|------|
| Intent Gate | 意图分类机制，将用户表面表达映射为真实意图和行动 |
| Manual QA Gate | 通过交付物的实际使用表面验证功能正确性的关卡 |
| 三尝试失败协议 | 3 次不同方法失败后强制 Oracle → 用户的恢复协议 |
| Success Criteria | Done 的充要条件清单 |
| 快速通道 | 简单任务的简化流程路径 |
| Assumptions Check | 简化版 Gap Analysis，在 DISCOVER 中检查假设和歧义 |
| Constraint anchor | PLAN 阶段声明的约束，作为后续漂移检测的锚 |
| Drift detection | 每步执行后对照 PLAN 检查是否偏离 |

### 11.4 参考文档

- deepworker v1: https://github.com/cireric/workflows/blob/main/agents/deepworker.md
- Hephaestus 架构: `docs/research/agent-deepworker/hephaestus-architecture.md`
- oh-my-openagent: https://github.com/code-yeongyu/oh-my-openagent
- opencode agents 文档: https://opencode.ai/docs/agents
- opencode config 文档: https://opencode.ai/docs/config

### 11.5 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-23 | 初始版本，基于 deepworker v1 + Hephaestus 对比分析 |
