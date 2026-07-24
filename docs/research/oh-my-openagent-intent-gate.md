# Sisyphus 意图门（Intent Gate）技术文档

> **文档范围**：聚焦 oh-my-openagent（原 oh-my-opencode）中 Sisyphus 主编排代理的 **Phase 0 意图门（Intent Gate）** 机制，解析其实现思路与工作流程。本文档为 [`oh-my-openagent-architecture.md`](./oh-my-openagent-architecture.md) 第 1.4 节 IntentGate 条目的深度展开，二者互补，不重复整体架构内容。
>
> **信息来源**：
> - DeepWiki：code-yeongyu/oh-my-opencode — "Sisyphus: Primary Orchestrator"（逐行引用源码）
> - DeepWiki：opensoft/oh-my-opencode — "Orchestrator Agents: Sisyphus & Atlas"
> - 架构分析：yuanshenjian.cn《Oh My OpenCode：Atlas vs Sisyphus 双 orchestrator 架构解析》
> - 官方站：ohmyopenagent.com
> - 源码行号基于 DeepWiki 引用的快照 commit（`9ef62aa7` / `aead4aeb`），随版本演进可能偏移
>
> **截止日期**：2026-07-24

---

## 目录

1. [概述](#1-概述)
2. [实现架构：双层约束](#2-实现架构双层约束)
3. [Phase 0 四步详解](#3-phase-0-四步详解)
4. [意图路由映射](#4-意图路由映射)
5. [完整工作流程](#5-完整工作流程)
6. [权限兜底机制](#6-权限兜底机制)
7. [动态提示构建](#7-动态提示构建)
8. [设计洞察与启示](#8-设计洞察与启示)
9. [源码索引](#9-源码索引)
10. [参考来源](#10-参考来源)

---

## 1. 概述

### 1.1 什么是意图门

**Intent Gate（意图门）** 是 oh-my-openagent 主编排代理 **Sisyphus** 的入口机制。每一条进入 Sisyphus 的用户消息，在触发任何工具调用或代码改动之前，都必须先经过 Phase 0 的"意图门"——把用户的**字面请求**翻译成**真实意图**，显式语言化、分类，再决定路由与委派策略。

官方对其功能的一句话定义：

> **IntentGate** — Analyzes true user intent before classifying or acting. No more literal misinterpretations.
> （在分类或行动之前分析用户的真实意图，不再有字面误解。）

### 1.2 定位澄清：提示工程门，而非运行时中间件

理解意图门最关键的一点：**它不是一段独立运行的拦截器/中间件代码**，而是 **Sisyphus 系统提示词（system prompt）中的一个强制执行段落——Phase 0**。

其实现本质是 **提示工程（prompt engineering）+ 工具权限层兜底** 的组合：

| 层次 | 机制 | 作用 |
|------|------|------|
| **软约束（提示层）** | 在系统提示里规定"每条消息必须先走 Phase 0 四步"，强制模型动手前把真实意图显式说出来并分类 | 主导行为协议 |
| **硬约束（权限层）** | 通过 `tool-config-handler` 配置 Sisyphus 工具权限：允许 `task()` 委派、禁止 `call_omo_agent` 直接调特定 agent | 从能力上限上兜底，确保"只能规划调度" |

因此"门"的语义是 **意图先于行动被显式化、被分类、被路由**，而非物理拦截。

---

## 2. 实现架构：双层约束

```
用户消息
   │
   ▼
┌─────────────────────────────────────────────┐
│  Phase 0 · Intent Gate （系统提示词段落）    │  ← 软约束
│  1. 意图语言化  2. 请求分类                  │
│  3. 歧义协议    4. 委派检查                  │
└─────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────┐
│  工具权限层 (tool-config-handler)            │  ← 硬约束
│  task = allow   call_omo_agent = deny        │
│  → 只能通过 task() 委派，不能直调特定 agent  │
└─────────────────────────────────────────────┘
   │
   ▼
路由到 Phase 1–3（评估 / 探索 / 实现 / 验证）
```

两层必须**一致**才能真正可靠：提示层说"默认委派"，权限层就让 `call_omo_agent=deny / task=allow`。这是该框架值得借鉴的工程哲学——**意图约束与能力约束对齐**。

---

## 3. Phase 0 四步详解

### 3.1 步骤 1 · 意图语言化（Intent Verbalization）

在分类或行动之前，Sisyphus 必须先把"字面请求"翻译成"真实意图"并**口头化输出**。这是整个门的核心——先想清楚用户到底要什么，再决定怎么干。强制输出格式：

```
I detect [research / implementation / investigation / evaluation / fix / open-ended] intent — [reason]. My approach: [explore → answer / plan → delegate / clarify first / ...].
```

源码落点：`src/agents/sisyphus.ts` L192–214（旧单文件结构）或 `src/agents/sisyphus/gpt-5-4.ts` L141–162（新拆分结构）。

这一步直接兑现宣传语 *"No more literal misinterpretations"*——杜绝模型把"看看这个函数"当成"重写这个函数"。

### 3.2 步骤 2 · 请求分类（Classification）

语言化之后，按复杂度把请求归入五类，每类对应一种行动策略（`src/agents/sisyphus.ts` L61–65）：

| 类型 | 信号 | 行动 |
|------|------|------|
| **Trivial** | 单文件、位置已知、直接答案 | 直接用工具（除非命中 Key Trigger） |
| **Explicit** | 指定文件/行、命令清晰 | 直接执行 |
| **Exploratory** | "X 是怎么工作的？""找一下 Y" | 并行发射 1–3 个 explore agent + 工具 |
| **Open-ended** | "改进"、"重构"、"加功能" | 先评估代码库成熟度再提方案 |
| **Ambiguous** | 范围不清、多种解读 | 只问**一个**澄清问题 |

### 3.3 步骤 3 · 歧义协议（Ambiguity Protocol）

这是门里最"有性格"的一环：Sisyphus 被教导**敢于挑战用户**。规则有两条硬指标（`src/agents/sisyphus.ts` L73、L91–103）：

1. **2 倍阈值**：如果存在多种解读，且**工作量差异 ≥ 2 倍**，**必须**先问澄清，不许猜。
2. **主动反对**：如果某个设计决策看起来有缺陷、或与代码库既有模式相矛盾，要主动指出并反对，而不是盲从。

这把意图门从被动分类升级成了**主动的需求对齐**——和很多 agent 框架"用户说什么就做什么"形成对比。

### 3.4 步骤 4 · 委派检查（Delegation Check，强制）

分类完成、准备动手前，还有一道强制自问（`src/agents/sisyphus.ts` L238–244）：

- 是否存在**完美匹配**此请求的专家 agent？
- 若没有，是否有最贴切的**任务类别（category）**？必须 `task(load_skills=[...])` 找技能来用。
- "我自己做就一定最好吗？"

**默认偏向是 DELEGATE（委派）**，只有"超级简单"时才自己做。这条规则由权限层落地——光在提示里说"要委派"不够，还要在权限上让它**只能**委派。

---

## 4. 意图路由映射

下表为提示词中直接写死的"表象 → 真实意图 → 路由"样例（`src/agents/sisyphus.ts` L192–214 / `dynamic-agent-core-sections.ts` L77–116）：

| 表面措辞 | 真实意图 | 路由 |
|----------|----------|------|
| "explain X", "how does Y work" | 研究 / 理解 | explore/librarian → 综合 → 回答 |
| "implement X", "add Y" | 实现（显式） | plan → 委派或执行 |
| "look into X", "check Y" | 调查 | explore → 汇报发现 |
| "what do you think about X?" | 评估 | 评估 → 提议 → 等确认 |
| "I'm seeing error X" | 需要修复 | 诊断 → 最小化修复 |
| "refactor", "improve" | 开放式变更 | 先评估代码库 → 提方案 |

意图门的输出不是"做或不做"，而是"**走哪条后续流水线**"（探索流 / 实现流 / 澄清流），让单一线性 agent 变成带调度能力的编排器。

---

## 5. 完整工作流程

### 5.1 Sisyphus 阶段总览

意图门是 Phase 0，它之后还有几个阶段，共同构成 Sisyphus 的执行闭环：

| 阶段 | 名称 | 做什么 | 与意图门的关系 |
|------|------|--------|----------------|
| **Phase 0** | Intent Gate | 语言化 → 分类 → 歧义协议 → 委派检查 | **入口，决定路由** |
| Phase 1 | Codebase Assessment | 判定代码库成熟度（disciplined / transitional / legacy / greenfield），决定遵循旧模式还是提新方案 | Open-ended 意图才进入 |
| Phase 2A | Exploration & Research | 默认并行：同时发射 2–5 个 explore/librarian 后台 agent，独立读 / 搜同时跑 | Research / Investigation 意图主战场 |
| Phase 2B | Implementation | 按 category + skills 委派给 Sisyphus-Junior 等执行器 | Implementation 意图主战场 |
| Phase 2C | Failure Recovery | 错误处理协议 | 异常分支 |
| Phase 3 | Completion | 验证：LSP diagnostics、跑测试、构建——不信任任何人，独立核验 | 所有路径汇入 |

Phase 1 代码库成熟度判定（`src/agents/sisyphus.ts` L262–283）：

| 状态 | 判据 | 行为 |
|------|------|------|
| Disciplined | 模式一致、配置齐全、有测试 | 严格遵循现有风格 |
| Transitional | 模式混杂、有部分结构 | 询问："我看到 X 和 Y 模式，遵循哪个？" |
| Legacy / Chaotic | 无一致性、模式过时 | 提议："无明确约定，建议 [X]，OK？" |
| Greenfield | 新 / 空项目 | 应用现代最佳实践 |

### 5.2 端到端示例

```
用户: "帮我加一个用户注册的 API 端点"

Phase 0 · Intent Gate:
  "I detect [implementation] intent — user wants to add an auth endpoint.
   My approach: [explore → plan → delegate]."

Phase 1: todowrite([分析现有结构, 实现 handler, 添加路由, 写测试])

Phase 2A: task(subagent_type="explore",    run_in_background=true,  ...)  # 后台并行找现有模式
          task(subagent_type="librarian",  run_in_background=true,  ...)

Phase 2B: task(category="quick",           run_in_background=false, ...)  # 委派执行

Phase 3:  lsp_diagnostics() + bash("bun test")                            # 独立验证
```

---

## 6. 权限兜底机制

### 6.1 task vs call_omo_agent

意图门的"默认委派"由两个工具的权限配比落地（`src/plugin-handlers/tool-config-handler`）：

- `task()` —— 灵活的 category-based 委派（推荐路径，可选模型）
- `call_omo_agent()` —— 直接调用特定 agent（仅限 explore / librarian / oracle / hephaestus / metis / momus / multimodal-looker）

Sisyphus 权限配置：

```typescript
const sisyphus = agentByKey(params.agentResult, "sisyphus");
if (sisyphus) {
  sisyphus.permission = {
    ...sisyphus.permission,
    call_omo_agent: "deny",   // 不能直接调特定 agent
    task: "allow",            // 只能通过 task() 委派
    "task_*": "allow",
    teammate: "allow",
  };
}
```

### 6.2 与其他代理的权限对比

| Agent | `task()` | `call_omo_agent()` | 使用场景 |
|-------|----------|---------------------|----------|
| **Sisyphus**（主协调器） | ✅ 允许 | ❌ 禁止 | 动态规划、灵活委派 |
| **Sisyphus-Junior**（子执行器） | ❌ 禁止 | ✅ 允许 | 执行具体任务、自主探索 |
| **Atlas**（指挥家） | ✅ 重授 | ❌ 禁止 | 纯协调，零代码实现 |
| **Metis / Momus**（预规划 / 审核） | ❌ 禁止 | ✅ 允许 | 只读分析，可并行启动 explore/librarian |

Sisyphus-Junior 配置（`src/agents/sisyphus-junior/agent.ts`）：

```typescript
const BLOCKED_TOOLS = ["task"];          // 禁止 task
merged.call_omo_agent = "allow";         // 显式允许 call_omo_agent
```

这种设计形成 **权限互补**：协调器通过 `task()` 灵活委派，执行者通过 `call_omo_agent` 自主获取信息，二者无法越权——这正是意图门"委派检查"步骤的硬性保障。

---

## 7. 动态提示构建

### 7.1 按模型变体分派

意图门所在的 Sisyphus 提示词**并非写死**，而是按检测到的模型族在运行时构建（`src/agents/sisyphus/agent.ts` L50–88，`getSisyphusPromptSource`）：

| 模型族 | 构建函数 | 源文件 |
|--------|----------|--------|
| GPT-5.4 | `buildGpt54SisyphusPrompt` | `src/agents/sisyphus/gpt-5-4.ts` |
| GPT-5.5 | `buildGpt55SisyphusPrompt` | `src/agents/sisyphus/gpt-5-5.ts` |
| Claude Opus 4.7 | `buildClaudeOpus47SisyphusPrompt` | `src/agents/sisyphus/claude-opus-4-7.ts` |
| Kimi K2 | `buildKimiK26SisyphusPrompt` | `src/agents/sisyphus/kimi-k2-6.ts` |
| Gemini | `buildGeminiSisyphusPrompt` | `src/agents/sisyphus/gemini.ts` |

例如 GPT-5.4 采用 "8-Block" 架构，用 XML 标签（`<identity>`、`<constraints>`、`<intent>` 等）与命名子锚点管理注意力，适配其原则驱动推理特点。

### 7.2 Prompt 段落装配

提示词由 `dynamic-agent-prompt-builder.ts` 在运行时按当前环境可用工具 / agent / skill 动态拼装。主要段落：

| 段落 | 构建函数 | 用途 |
|------|----------|------|
| Role | 静态 | 身份、核心能力、运行模式 |
| **Phase 0: Intent Gate** | `buildKeyTriggersSection` | **意图语言化与分类** |
| Phase 1: Codebase Assessment | 静态 | 成熟度分类 |
| Phase 2A: Exploration | `buildToolSelectionTable`、`buildExploreSection`、`buildLibrarianSection` | 并行研究与工具使用 |
| Phase 2B: Implementation | `buildCategorySkillsDelegationGuide`、`buildDelegationTable` | 委派策略与会话续接 |
| Phase 2C: Failure Recovery | 静态 | 错误处理协议 |
| Phase 3: Completion | 静态 | 验证要求 |
| 约束 | `buildHardBlocksSection`、`buildAntiPatternsSection` | 硬性禁止与反模式 |

这种动态构建让意图门**模型无关**——换个模型只需换对应 builder，Phase 0 的四步逻辑保持一致。

---

## 8. 设计洞察与启示

1. **"门"在提示层，不在代码层**
   用提示词把"想清楚再动手"固化为模型行为协议，辅以工具权限兜底。这是一种轻量、模型无关的治理方式。

2. **语言化 = 可审计**
   强制输出 "I detect ... intent" 这句话，让意图判断**对用户可见、可纠偏**，而非黑箱决策。

3. **歧义协议的"2 倍工作量"阈值**
   用量化阈值把"要不要问"从主观判断变成可执行规则——既避免在无谓小歧义上反复打断用户，又防止在大歧义上瞎猜。

4. **意图门与权限门双重保证**
   提示层说"默认委派"，权限层让 `call_omo_agent=deny / task=allow`，两者一致才真正可靠。

5. **路由即分流**
   意图门输出的是"走哪条后续流水线"，让单一 agent 具备调度能力，而非线性执行器。

6. **主动挑战而非盲从**
   歧义协议要求 agent 在设计有缺陷或与代码库模式矛盾时主动反对——把 agent 从"指令执行者"提升为"有判断力的协作者"。

---

## 9. 源码索引

> 仓库历经 `oh-my-opencode` → `oh-my-openagent` 更名，源码从单文件拆为目录结构。下表并列两种引用，行号基于 DeepWiki 快照，随版本可能偏移。

| 关注点 | 旧结构（单文件） | 新结构（拆分） |
|--------|------------------|----------------|
| Intent Gate 主体（Phase 0） | `src/agents/sisyphus.ts` L141–162 | `src/agents/sisyphus/gpt-5-4.ts` L141–162 |
| 意图语言化样例 | `src/agents/sisyphus.ts` L192–214 | `src/agents/dynamic-agent-core-sections.ts` L77–116 |
| 五类分类 | `src/agents/sisyphus.ts` L61–65 | `src/agents/sisyphus/gpt-5-4.ts` |
| 2 倍歧义阈值 | `src/agents/sisyphus.ts` L73 | `src/agents/sisyphus/gpt-5-4.ts` |
| 挑战用户协议 | `src/agents/sisyphus.ts` L91–103 | `src/agents/sisyphus/gpt-5-4.ts` |
| 委派检查 | `src/agents/sisyphus.ts` L238–244 | `src/agents/sisyphus/gpt-5-4.ts` |
| 代码库成熟度评估 | `src/agents/sisyphus.ts` L262–283 | `src/agents/sisyphus/gpt-5-4.ts` |
| 身份与运行模式 | `src/agents/sisyphus.ts` L33–38, L120–127 | `src/agents/sisyphus/gpt-5-4.ts` L120–127 |
| 模型变体分派 | — | `src/agents/sisyphus/agent.ts` L50–88 |
| Prompt 段落装配 | — | `src/agents/dynamic-agent-prompt-builder.ts` L10–31 |
| Key Triggers 段落 | — | `src/agents/dynamic-agent-core-sections.ts` |
| 工具权限兜底 | `src/plugin-handlers/tool-config-handler` | 同 |
| Sisyphus-Junior 权限 | `src/agents/sisyphus-junior.ts` | `src/agents/sisyphus-junior/agent.ts` |
| call_omo_agent 允许列表 | `src/tools/call-omo-agent/constants` | 同 |

---

## 10. 参考来源

1. **DeepWiki — Sisyphus: Primary Orchestrator**
   https://deepwiki.com/code-yeongyu/oh-my-opencode/4.2-specialized-agents
2. **DeepWiki — Orchestrator Agents: Sisyphus & Atlas**
   https://deepwiki.com/opensoft/oh-my-opencode/2.1-orchestrator-agents:-sisyphus-and-atlas
3. **架构分析 — Atlas vs Sisyphus 双 orchestrator 架构解析**
   https://yuanshenjian.cn/articles/oh-my-opencode-atlas-vs-sisyphus-arch
4. **官方站 — Oh My OpenAgent**
   https://ohmyopenagent.com
5. **GitHub 仓库**
   https://github.com/code-yeongyu/oh-my-openagent/
6. **配套总体架构文档**
   [`./oh-my-openagent-architecture.md`](./oh-my-openagent-architecture.md)
