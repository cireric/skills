# Sisyphus 意图门（Intent Gate）实现详解

> **文档定位**：本文档完全基于网络公开来源（oh-my-openagent GitHub `dev` 分支源码 + 官方文档）独立整理而成，用于与本地已有文档做对比分析。
> **研究对象**：[code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) `dev` 分支
> **核心结论先行**：Intent Gate **不是一个独立的代码模块/分类器函数**，而是嵌入在 Sisyphus 系统提示词中的 **"提示词工程认知门"**（prompt-engineered cognitive gate）。它通过自然语言指令规定模型在每一次回复中执行一套多步决策流程，并由"模型变体 + 动态段拼装"机制做模型级强化。

---

## 1. 概述：Intent Gate 是什么

在 oh-my-openagent 的官方宣传中，Sisyphus 的工作流被划分为四个阶段（PHASE 1–4）：

| 阶段 | 名称 | 作用 |
|------|------|------|
| PHASE 1 | **Intent Gate** | 解析用户真实意图，而不只是字面输入 |
| PHASE 2 | Codebase Assessment | 动代码前先映射架构 |
| PHASE 3 | Smart Delegation | 路由到正确的专家 agent |
| PHASE 4 | Independent Verification | 不轻信，验证一切 |

来源：[ohmyopenagent.com](https://ohmyopenagent.com/)

README 中对 IntentGate 的功能行描述为：

> `| 🚪 | IntentGate | Ultimate | Analyzes true user intent before classifying or acting. No more literal misinterpretations. (Light edition only recognises the ultrawork/ulw keyword.) |`

来源：[README.md (dev)](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/README.md)

**关键澄清**：在源码内部，Intent Gate 被标注为 **"Phase 0"**（不是宣传中的 PHASE 1）。这是因为 Sisyphus 提示词的内部编号把 Intent Gate 放在第 0 位，Codebase Assessment 放在 Phase 1。本文后续沿用源码内部的 "Phase 0 = Intent Gate" 命名。

---

## 2. 源码定位

Intent Gate 的实现分布在以下文件中（均位于 `packages/omo-opencode/src/agents/` 下）：

| 文件 | 角色 |
|------|------|
| `sisyphus/default.ts` | 基础/Claude 变体的提示词构建器，**包含完整 Phase 0 Intent Gate** |
| `sisyphus/claude-opus-4-8.ts` | 主力模型 Opus 4.8 变体，包含 Intent Gate + 额外防漂移门 |
| `sisyphus/gemini.ts` | Gemini 专用纠偏覆盖层，含 `buildGeminiIntentGateEnforcement()` |
| `sisyphus/gpt-5-4.ts` / `gpt-5-5.ts` / `kimi-k*.ts` / `glm-5-2.ts` 等 | 各模型原生变体 |
| `sisyphus/index.ts` | 桶导出 |
| `dynamic-agent-core-sections.ts` | 动态段生成器，含 `buildKeyTriggersSection()`（被 Intent Gate 引用） |
| `dynamic-agent-prompt-builder.ts` | 动态段的桶导出 |
| `builtin-agents/sisyphus-agent.ts` | agent 工厂，负责模型解析 + 提示词拼装 + 运行时重建 |
| `sisyphus/AGENTS.md` | 变体选择参考文档 |
| `../../model-core/src/agent-model-requirements.ts` | Sisyphus 模型 fallback 链定义 |

**核心事实**：仓库根目录**没有 `opencode.json` 来定义 Sisyphus**（根 `.opencode/` 目录只含 `AGENTS.md`、`command/`、`skills/` 等）。Sisyphus 的 agent 配置（模型、权限、提示词）完全由 TypeScript 代码动态构建。

---

## 3. 实现思路（核心设计哲学）

Intent Gate 的实现思路可以概括为四点：

### 3.1 提示词即逻辑（Prompt-as-Logic），而非代码拦截

绝大多数"意图识别"系统的实现方式是：写一个分类器函数（正则/ML/LLM 调用），在请求进入主循环前做拦截路由。oh-my-openagent **反其道而行**：Intent Gate 是写在系统提示词里的一段**多步决策流程指令**，由 Sisyphus 这个 LLM 自身在每一轮回复中"自我执行"。

- 没有独立的 `classifyIntent()` 函数被调用；
- 没有 hook 在工具调用前做意图校验（仓库里有一个 `prompt-async-gate-rfc.md`，但那是另一种"async gate"，与 Intent Gate 无关）；
- "门"的强制性来自提示词里的措辞（`MANDATORY`、`NO EXCEPTIONS`、`BLOCKING`、`YOU MUST`）+ 模型对指令的遵循。

这是一种 **"把控制流编码进自然语言"** 的范式。代价是依赖模型指令遵循能力；收益是零额外推理开销、零延迟、且能处理任意开放性意图（不需要预定义枚举之外的兜底）。

### 3.2 动态段拼装（Dynamic Section Composition）

Intent Gate 不是一段写死的静态文本。它的提示词骨架里有占位符（如 `${keyTriggers}`、`${toolSelection}`、`${exploreSection}`），在运行时由构建函数根据**当前实际可用的 agents / tools / skills / categories** 动态填充。

入口函数 `buildDefaultSisyphusPrompt()` 的拼装逻辑（[default.ts](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)）：

```typescript
export function buildDefaultSisyphusPrompt(
  model: string,
  availableAgents: AvailableAgent[],
  availableTools: AvailableTool[] = [],
  availableSkills: AvailableSkill[] = [],
  availableCategories: AvailableCategory[] = [],
  useTaskSystem = false,
): string {
  const keyTriggers = buildKeyTriggersSection(availableAgents, availableSkills);
  const toolSelection = buildToolSelectionTable(availableAgents, availableTools, availableSkills);
  const exploreSection = buildExploreSection(availableAgents);
  const librarianSection = buildLibrarianSection(availableAgents);
  // ... 其余动态段
  return `<Role> ... </Role>
<Behavior_Instructions>
## Phase 0 - Intent Gate (EVERY message)
${keyTriggers}
<intent_verbalization>
### Step 0: Verbalize Intent (BEFORE Classification)
...
</intent_verbalization>
### Step 1: Classify Request Type
...
## Phase 1 - Codebase Assessment (for Open-ended tasks)
...
## Phase 2A - Exploration & Research
${toolSelection}
${exploreSection}
${librarianSection}
...`;
}
```

**意义**：Intent Gate 引用的 "Key Triggers"（关键触发器）列表是**从当前可用 agent 的 metadata 动态生成**的——装了哪些子 agent，提示词里就列出哪些触发条件。这使得门能自适应用户的具体配置（禁用了某 agent，对应触发条件就消失）。

### 3.3 模型特定变体（Model-Specific Variants）

不同模型有不同的"失败模式"。Sisyphus 为每个主力模型维护一个独立的提示词变体文件，由 `sisyphus-agent-factory.ts` 按模型名路由（见 [sisyphus/AGENTS.md](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/AGENTS.md)）：

| 模型 | 变体文件 | Intent Gate 强化点 |
|------|----------|--------------------|
| Claude Opus 4.8（主力） | `claude-opus-4-8.ts` | 增加 Step 1.5 Turn-Local Intent Reset + Step 2.5 Context-Completion Gate |
| Claude 通用 / 默认 | `default.ts` | 基础版 Intent Gate |
| Gemini | `gemini.ts` | 叠加 `buildGeminiIntentGateEnforcement()` 强制覆盖层 |
| GPT-5.4 / 5.5 | `gpt-5-4.ts` / `gpt-5-5.ts` | 块结构化指令 |
| Kimi K2.6/2.7/K3、GLM-5.2 | 各自文件 | 针对各自反过度思考/失败模式校准 |

这种"同一套门，按模型失败模式做差异化加固"的思路，是该实现的核心工程价值所在。

### 3.4 运行时重建（Runtime Prompt Reconciliation）

由于提示词是按"配置的模型"烘焙（bake）的，但当用户在 TUI 中临时切换模型族时，已烘焙的提示词会与新模型不匹配。工厂函数 `maybeCreateSisyphusConfig()` 通过 `setSisyphusRuntimePromptContext()` 捕获了一个 `rebuildPromptForModel` 回调，在 system-transform hook 中按运行时模型重建提示词（issue #5297/#5316）。这保证 Intent Gate 始终匹配当前实际跑的模型。

---

## 4. 核心架构：提示词是如何被构建出来的

完整调用链：

```
opencode 启动
  └─ maybeCreateSisyphusConfig()                    [sisyphus-agent.ts]
       ├─ 读取 AGENT_MODEL_REQUIREMENTS["sisyphus"]  [model-core/agent-model-requirements.ts]
       │     → fallbackChain: [claude-opus-4-8, kimi-k3, gpt-5.6-sol, glm-5, big-pickle]
       ├─ applyModelResolution()  → 解析出实际模型 + variant
       ├─ createSisyphusAgent(model, agents, tools, skills, categories, useTaskSystem)
       │     [sisyphus/index.ts → sisyphus-agent-factory.ts]
       │     └─ 按模型名路由到变体构建器：
       │          - 含 "claude-opus-4-8" → buildClaudeOpus48SisyphusPrompt()
       │          - 含 "claude-opus-4-7" → buildClaudeOpus47SisyphusPrompt()
       │          - 含 "gpt-5.5"/"gpt-5.6" → buildGpt55SisyphusPrompt()
       │          - GLM 族 → buildGlm52SisyphusPrompt()
       │          - Kimi 族 → 对应 kimi 变体
       │          - 默认 → buildDefaultSisyphusPrompt()
       │          - Gemini → 默认 + gemini 纠偏覆盖层
       │
       │  每个变体构建器内部：
       │     ├─ buildKeyTriggersSection(agents)         ← 动态：Key Triggers
       │     ├─ buildToolSelectionTable(...)            ← 动态：工具/agent 选择表
       │     ├─ buildExploreSection(agents)             ← 动态：explore 用法
       │     ├─ buildLibrarianSection(agents)           ← 动态：librarian 用法
       │     ├─ buildDelegationTable(agents)            ← 动态：委派表
       │     ├─ buildOracleSection(agents)              ← 动态：Oracle 咨询规则
       │     ├─ buildCategorySkillsDelegationGuide(...) ← 动态：category+skills
       │     ├─ buildHardBlocksSection()                ← 静态：硬禁令
       │     ├─ buildAntiPatternsSection()              ← 静态：反模式
       │     ├─ buildTaskManagementSection(useTaskSystem)← 静态：任务管理
       │     └─ 拼装成完整提示词（含 Phase 0 Intent Gate）
       │
       ├─ applyOverrides()                ← 用户 opencode.json 覆盖
       ├─ applyFrontierToolSchemaPermission()  ← 工具权限守卫
       ├─ applyEnvironmentContext()
       └─ setSisyphusRuntimePromptContext({ rebuildPromptForModel })  ← 运行时重建钩子
```

### 4.1 模型 fallback 链（[agent-model-requirements.ts](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/model-core/src/agent-model-requirements.ts)）

```typescript
sisyphus: {
  fallbackChain: [
    { providers: ["anthropic", "github-copilot", "opencode", "vercel"],
      model: "claude-opus-4-8", variant: "max" },
    { providers: ["opencode-go", "kimi-for-coding", "moonshotai", ...],
      model: "kimi-k3" },
    { providers: ["openai", "github-copilot", "opencode", "vercel"],
      model: "gpt-5.6-sol", variant: "medium" },
    { providers: ["zai-coding-plan", "opencode", "bailian-coding-plan", "vercel"],
      model: "glm-5" },
    { providers: ["opencode"], model: "big-pickle" },
  ],
  requiresAnyModel: true,
}
```

`requiresAnyModel: true` 表示只要 fallback 链里有任一模型可用，Sisyphus 就会注册。

---

## 5. Intent Gate 工作流程详解（Phase 0）

下面是 `default.ts` 中 Intent Gate 的**完整原文**（[源](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)），按步骤拆解：

### Step 0：Verbalize Intent（意图言语化，分类前必做）

> 在分类之前，先识别用户作为编排对象**真正想要什么**。把"表面形式"映射到"真实意图"，然后**大声宣告**你的路由决策。

**意图 → 路由映射表**（核心路由逻辑）：

| 表面形式（用户说什么） | 真实意图 | 路由 |
|------------------------|----------|------|
| "explain X", "how does Y work" | 研究/理解 | explore/librarian → 综合 → 回答 |
| "implement X", "add Y", "create Z" | 实现（显式） | 规划 → 委派或执行 |
| "look into X", "check Y", "investigate" | 调查 | explore → 报告发现 |
| "what do you think about X?" | 评估 | 评估 → 提议 → **等待确认** |
| "I'm seeing error X" / "Y is broken" | 需要修复 | 诊断 → 最小化修复 |
| "refactor", "improve", "clean up" | 开放式变更 | 先评估代码库 → 提议方案 |

**强制输出格式**（每一轮都必须先输出这一行）：

```
> "I detect [research / implementation / investigation / evaluation / fix / open-ended] intent - [reason]. My approach: [explore → answer / plan → delegate / clarify first / etc.]."
```

**关键约束**：言语化**不等于**承诺实现。只有用户的**显式请求**才承诺实现。

> 设计意图：这一步强制模型"把隐式推理显式化"，既给用户可见的决策依据，也给后续步骤一个锚点。它解决的核心痛点是 AI 被字面意思误导（如把 "look into" 当成 "去改代码"）。

### Step 1：Classify Request Type（请求类型分类）

把请求归为五类，每类对应不同处理策略：

- **Trivial**（单文件、已知位置、直接答案）→ 直接用工具（除非命中 Key Trigger）
- **Explicit**（指定文件/行、明确命令）→ 直接执行
- **Exploratory**（"X 怎么工作？""找 Y"）→ 并行触发 1-3 个 explore + 工具
- **Open-ended**（"改进"、"重构"、"加功能"）→ **先评估代码库**
- **Ambiguous**（范围不清、多种解读）→ 问一个澄清问题

### Step 2：Check for Ambiguity（歧义检查）

- 单一合理解读 → 继续
- 多解读、工作量相近 → 用合理默认值继续，标注假设
- 多解读、工作量差距 2 倍以上 → **必须问**
- 缺关键信息（文件、错误、上下文）→ **必须问**
- 用户设计看似有缺陷 → **实现前必须提出顾虑**

### Step 3：Validate Before Acting（行动前校验）

包含两个子检查：

**假设检查**：
- 我是否有影响结果的隐式假设？
- 搜索范围是否清晰？

**委派检查（直接行动前的强制门）**：
1. 是否有完美匹配的专家 agent？
2. 若没有，是否有最贴切的 `task` category（visual-engineering / ultrabrain / quick 等）？有哪些 skills 可装备？——**必须为 `task(load_skills=[...])` 找到 skills 作为参数传入**。
3. 我自己干真的能做得最好吗？**真的、真的、没有任何合适的 category 可用吗？**

**默认偏向：DELEGATE（委派）。只有超级简单时才自己干。**

### When to Challenge the User（何时挑战用户）

观察到以下情况要提出顾虑、给替代方案、询问是否继续：
- 会引发明显问题的设计决策
- 与代码库既有模式矛盾的做法
- 误解现有代码如何工作的请求

输出模板：
```
I notice [observation]. This might cause [problem] because [reason].
Alternative: [your suggestion].
Should I proceed with your original request, or try the alternative?
```

---

## 6. 关键机制逐个剖析

### 6.1 Key Triggers（关键触发器）——动态生成的"短路路由"

Intent Gate 开头的 `${keyTriggers}` 由 `buildKeyTriggersSection()` 生成（[dynamic-agent-core-sections.ts](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/dynamic-agent-core-sections.ts)）：

```typescript
export function buildKeyTriggersSection(agents, _skills = []): string {
  const keyTriggers = agents
    .filter((agent) => agent.metadata.keyTrigger)
    .map((agent) => `- ${agent.metadata.keyTrigger}`)
  if (keyTriggers.length === 0) return ""
  return `### Key Triggers (check BEFORE classification):
${keyTriggers.join("\n")}
- **"Look into" + "create PR"** → Not just research. Full implementation cycle expected.`
}
```

**机制**：遍历所有可用 agent 的 `metadata.keyTrigger` 字段，把每个专家 agent 的"触发短语"拼成列表，插到 Intent Gate 最前面，标注 **"check BEFORE classification"**（在分类前先检查）。即：命中 Key Trigger 的请求**绕过常规分类**，直接路由到对应专家。

末尾还有一条硬编码特例：**"Look into" + "create PR"** 不只是研究，而是完整实现周期。这是为了堵住"look into 被当成纯研究"的漏洞。

### 6.2 Implementation Gate（实现门）——角色层的硬禁令

在 `<Role>` 段（Intent Gate 之前）还有一条总闸（[default.ts 第 143-144 行](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)）：

```
- Follows user instructions. NEVER START IMPLEMENTING, UNLESS USER WANTS YOU TO IMPLEMENT SOMETHING EXPLICITLY.
  - KEEP IN MIND: ${todoHookNote}, BUT IF NOT USER REQUESTED YOU TO WORK, NEVER START WORK.
```

`todoHookNote` 会根据是否启用 task 系统动态替换为 `"YOUR TASK CREATION WOULD BE TRACKED BY HOOK([SYSTEM REMINDER - TASK CONTINUATION])"` 或 todo 版本。

> 这是"双层门"设计：Role 层的 Implementation Gate 是总原则，Phase 0 的 Intent Gate 是每轮的具体执行流程。

### 6.3 Turn-Local Intent Reset（轮次局部意图重置）——Opus 4.8 专属

`claude-opus-4-8.ts` 变体在 Step 1 之后增加了 Step 1.5（[源](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-4-8.ts)）：

```
### Step 1.5: Turn-Local Intent Reset (apply to EVERY turn)
Reclassify intent from CURRENT message ONLY. NEVER auto-carry "implementation mode" from prior turns.
- Question / explanation / investigation → answer or analyze ONLY. NO todos. NO file edits.
- User still giving context → gather/confirm context FIRST. NO implementation yet.
- Prior turn authorized implementation, current turn asks something different → DROP implementation mode, serve current question.
Implementation authorization does NOT persist. It must be RE-ESTABLISHED by an explicit verb in the current message.
```

**解决问题**：Opus 4.8 倾向于"把上一轮的实现授权延续到这一轮"。这条强制每轮**只看当前消息**重新分类，实现授权**不跨轮延续**，必须由当前消息里的显式动词重新确立。

### 6.4 Context-Completion Gate（上下文完成门）——Opus 4.8 专属

Step 2.5（实现前最后一道门）：

```
### Step 2.5: Context-Completion Gate (before implementation)
Implement ONLY when ALL true:
1. Current message contains explicit implementation verb (implement / add / create / fix / change / write / build).
2. Scope/objective concrete enough to execute without guessing.
3. NO blocking specialist result pending (especially Oracle).
If ANY condition fails → research/clarification ONLY, then end response and wait. NEVER invent authorization.
```

**三个充要条件同时满足才允许实现**：显式实现动词 + 范围足够具体 + 无阻塞中的专家结果（尤其 Oracle）。任一不满足 → 只做研究/澄清，结束回复等待。**绝不自行虚构授权。**

### 6.5 Delegation Check（委派检查）——默认偏向委派

Step 3 中的三问（见第 5 节）。核心是 **"DEFAULT BIAS: DELEGATE"**——命中匹配触发器就**立刻委派**，不要纠结"委派是否值得开销"。

---

## 7. Codebase Assessment（Phase 1，开放式任务的第二步）

紧跟 Intent Gate 之后，针对开放式任务（[default.ts](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)）：

```
## Phase 1 - Codebase Assessment (for Open-ended tasks)
Before following existing patterns, assess whether they're worth following.
### Quick Assessment:
1. Check config files: linter, formatter, type config
2. Sample 2-3 similar files for consistency
3. Note project age signals (dependencies, patterns)
### State Classification:
- Disciplined (consistent patterns, configs present, tests exist) → Follow existing style strictly
- Transitional (mixed patterns, some structure) → Ask: "I see X and Y patterns. Which to follow?"
- Legacy/Chaotic (no consistency, outdated patterns) → Propose: "No clear conventions. I suggest [X]. OK?"
- Greenfield (new/empty project) → Apply modern best practices
IMPORTANT: If codebase appears undisciplined, verify before assuming:
- Different patterns may serve different purposes (intentional)
- Migration might be in progress
- You might be looking at the wrong reference files
```

**四档成熟度分类**：Disciplined / Transitional / Legacy-Chaotic / Greenfield，每档对应不同的"是否遵循既有模式"策略。注意末尾的"反向校验"——看起来混乱时先核实，避免误判（不同模式可能是有意的、可能正在迁移、可能参考文件选错了）。

> 这同样是提示词内嵌的逻辑，不是独立分类器。

---

## 8. 模型特定变体的差异化加固

### 8.1 Gemini：Intent Gate 强制执行覆盖层

Gemini 的失败模式被明确记录在 `gemini.ts` 文件头：

```
Gemini models are aggressively optimistic and tend to:
- Skip tool calls in favor of internal reasoning
- Avoid delegation, preferring to do work themselves
- Claim completion without verification
- Interpret constraints as suggestions
- Skip intent classification gates (jump straight to action)
- Conflate investigation with implementation ("look into X" → starts coding)
```

因此 `buildGeminiIntentGateEnforcement()` 注入一段更暴力的强制指令：

```
<GEMINI_INTENT_GATE_ENFORCEMENT>
## YOU MUST CLASSIFY INTENT BEFORE ACTING. NO EXCEPTIONS.
**Your failure mode: You skip intent classification and jump straight to implementation.**

**MANDATORY FIRST OUTPUT - before ANY tool call or action:**
I detect [TYPE] intent - [REASON].
My approach: [ROUTING DECISION].
Where TYPE is one of: research | implementation | investigation | evaluation | fix | open-ended

**SELF-CHECK (answer honestly before proceeding):**
1. Did the user EXPLICITLY ask me to implement/build/create something? → If NO, do NOT implement.
2. Did the user say "look into", "check", "investigate", "explain"? → That means RESEARCH, not implementation.
3. Did the user ask "what do you think?" → That means EVALUATION - propose and WAIT, do not execute.
4. Did the user report an error? → That means MINIMAL FIX, not refactoring.

**COMMON MISTAKES YOU MAKE (AND MUST NOT):**
| User Says                     | You Want To Do        | You MUST Do                                |
| "explain how X works"         | Start modifying X     | Research X, explain it, STOP               |
| "look into this bug"          | Fix the bug immediately| Investigate, report findings, WAIT        |
| "what do you think about approach X?" | Implement approach X | Evaluate X, propose alternatives, WAIT |
| "improve the tests"           | Rewrite all tests     | Assess current tests FIRST, propose, THEN |

**IF YOU SKIPPED THE INTENT CLASSIFICATION ABOVE:** STOP. Go back. Do it now. Your next tool call is INVALID without it.
</GEMINI_INTENT_GATE_ENFORCEMENT>
```

**差异化要点**：
- 比 `default.ts` 多了 **"COMMON MISTAKES" 对照表**，直接列出"你想做的 vs 你必须做的"；
- 多了 **4 项 SELF-CHECK 自问**；
- 措辞更强（`NO EXCEPTIONS`、`Your next tool call is INVALID without it`）。

### 8.2 Claude Opus 4.8：防漂移双门

如 6.3 / 6.4 所述，Opus 4.8 变体增加了 Step 1.5（轮次重置）和 Step 2.5（上下文完成门）。文件头说明了设计依据（Anthropic Opus 4.8 迁移指南 + 4.7 蒸馏）：

```
- SILENCE DEFAULT: 4.8 narrates more than 4.7 ... Explicit silence-between-tool-calls instruction restores terse behavior.
- SMALL-DECISION AUTONOMY: 4.8 is more deliberate and asks more often on minor choices. Explicit don't-ask guidance ...
- EXPLICIT CAPABILITY TRIGGERS: 4.8 under-reaches for subagents and tools ...
- LITERAL instruction following inherited from 4.7: state scope explicitly.
- XML-tagged anchors, Phase 0/1/2A/2B/2C/3 mental model ...
```

Opus 4.8 变体的意图映射表还多了两行（`default.ts` 没有）：

| 表面形式 | 真实意图 | 路由 |
|----------|----------|------|
| "yesterday's work seems off" | 查找/修复近期问题 | 检查最近改动 → 假设 → 验证 → 修复 |
| "fix this whole thing" | 多问题彻底排查 | 评估范围 → todo list → 系统化 |

---

## 9. 完整工作流程串联

把 Intent Gate 放回 Sisyphus 整体流程，一次用户请求的完整流转：

```
用户消息到达 Sisyphus
        │
        ▼
┌─ Role 层总闸 ────────────────────────────────┐
│  Implementation Gate: 未被显式要求实现 → 不开工 │
└──────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 0: Intent Gate（每一轮都跑）──────────────────────────────┐
│  0. Key Triggers 检查（命中 → 直接路由到对应专家，跳过分类）        │
│  Step 0: Verbalize Intent                                        │
│          表面形式 → 真实意图 → 路由（强制输出一行宣告）             │
│  Step 1: Classify Request Type                                   │
│          Trivial / Explicit / Exploratory / Open-ended / Ambiguous│
│  Step 1.5: Turn-Local Intent Reset（仅 Opus 4.8）                │
│          只看当前消息，不延续上轮 implementation mode              │
│  Step 2: Check for Ambiguity                                     │
│          单解读→继续 / 多解读差距大→问 / 缺信息→问 / 设计有疑→提   │
│  Step 2.5: Context-Completion Gate（仅 Opus 4.8）                │
│          显式动词 + 范围具体 + 无阻塞专家结果 → 才允许实现         │
│  Step 3: Validate Before Acting                                  │
│          假设检查 + 委派检查（默认偏向 DELEGATE）                  │
│  Challenge User（如观察到设计问题）                               │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼（若为开放式任务）
┌─ Phase 1: Codebase Assessment ──────────────────────────────────┐
│  采样 2-3 文件 + 检查 linter/formatter/type 配置                  │
│  → Disciplined / Transitional / Legacy-Chaotic / Greenfield      │
│  → 决定"是否遵循既有模式"及对应策略                               │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 2A: Exploration & Research ──────────────────────────────┐
│  并行触发 explore/librarian（run_in_background=true）            │
│  独立读/搜/agent 同时跑；无重叠工作可做 → 结束回复等待系统提醒     │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 2B/2C, Phase 3: Smart Delegation + Independent Verification ┐
│  委派给专家 / category agent；独立验证子 agent 的产出               │
└───────────────────────────────────────────────────────────────────┘
```

**Gate 的"拦截"语义**：在 Phase 0 中，任何一步判定"不该实现"（缺信息 / 有歧义 / 无显式动词 / 命中研究意图），流程就**在此终止**——模型只做研究/澄清/提问，然后结束回复等待用户。这就是"门"的实际含义：**它是一个终止条件集合**，而非一个路由函数。

---

## 10. 设计哲学与启示

### 10.1 优势

1. **零额外推理开销**：不调用第二个 LLM 做分类，门由主模型自我执行。
2. **开放性**：意图映射表是示例而非封闭枚举，能兜底任意意图。
3. **可观测性**：Verbalize 强制模型把决策说出口，用户可见可审计。
4. **自适应配置**：Key Triggers 等动态段随可用 agent/skill 变化。
5. **模型级精准加固**：针对每个模型的已知失败模式做差异化提示词，比"一刀切提示词"有效。

### 10.2 代价与风险

1. **强依赖指令遵循能力**：弱模型可能无视 `MUST`/`NO EXCEPTIONS`（这正是 Gemini 需要单独 enforcement 覆盖层的原因）。
2. **无代码级保证**：门的强制性纯靠提示词，没有运行时校验"模型是否真的输出了 verbalization 行"。理论上模型可以跳过。
3. **提示词膨胀**：每个变体文件数千字节（`claude-opus-4-8.ts` 约 24KB），维护成本高，需为每个新模型写变体。
4. **变体漂移风险**：多个变体各持一份 Intent Gate 副本，内容需手工保持同步（`AGENTS.md` 也承认 "shared dynamic helpers identical to the 4.7 variant so content stays in sync"）。

### 10.3 与"代码拦截式"意图识别的对比

| 维度 | 代码拦截式（常规） | oh-my-openagent 提示词门 |
|------|--------------------|--------------------------|
| 实现位置 | 请求前置中间件/分类函数 | 系统提示词内 |
| 执行者 | 独立分类器（正则/ML/LLM） | 主模型自身 |
| 延迟 | 额外一次推理 | 零额外 |
| 强制力 | 代码级（硬保证） | 提示词级（软保证，依赖模型遵循） |
| 可扩展性 | 需改代码加意图类型 | 改提示词表格即可 |
| 可观测性 | 日志 | 模型输出可见 |
| 模型差异化 | 难（一套逻辑） | 易（每模型一变体） |

---

## 11. 关键源文件索引（均为 dev 分支 raw 链接）

- 提示词变体目录：[`packages/omo-opencode/src/agents/sisyphus/`](https://github.com/code-yeongyu/oh-my-openagent/tree/dev/packages/omo-opencode/src/agents/sisyphus)
- 基础变体（含完整 Intent Gate）：[`sisyphus/default.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)
- Opus 4.8 变体（含 Step 1.5 / 2.5）：[`sisyphus/claude-opus-4-8.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-4-8.ts)
- Gemini 强制覆盖层：[`sisyphus/gemini.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/gemini.ts)
- 变体选择参考：[`sisyphus/AGENTS.md`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/AGENTS.md)
- 桶导出：[`sisyphus/index.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/index.ts)
- 动态段生成器（含 `buildKeyTriggersSection`）：[`dynamic-agent-core-sections.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/dynamic-agent-core-sections.ts)
- 动态段桶导出：[`dynamic-agent-prompt-builder.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/dynamic-agent-prompt-builder.ts)
- Agent 工厂（模型解析 + 运行时重建）：[`builtin-agents/sisyphus-agent.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/builtin-agents/sisyphus-agent.ts)
- 模型 fallback 链：[`model-core/src/agent-model-requirements.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/model-core/src/agent-model-requirements.ts)
- 编排文档：[`docs/guide/orchestration.md`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/docs/guide/orchestration.md)
- README（IntentGate 功能行）：[`README.md`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/README.md)

---

## 12. 总结

Sisyphus 的 Intent Gate 是一个**纯提示词工程产物**，其"实现"由三层构成：

1. **静态决策流程**：Phase 0 的 Step 0→1→2→3 多步门（Verbalize → Classify → Ambiguity → Validate），加上 Role 层的 Implementation Gate 总闸。门的本质是一组**终止条件**——判定不该实现就立即停下等待。
2. **动态段拼装**：`buildKeyTriggersSection` 等函数根据当前可用 agents/tools/skills/categories 实时生成 Key Triggers、工具选择表、委派表等，使门自适应配置。
3. **模型变体加固**：每个主力模型一个变体文件，针对该模型失败模式做差异化加固（Gemini 加 enforcement 覆盖层、Opus 4.8 加轮次重置与上下文完成门），并由工厂按模型名路由 + 运行时重建。

工作流程上，Intent Gate 是 Sisyphus 每一轮回复的**第一道也是贯穿始终的认知工序**：先言语化意图、再分类、查歧义、校验授权与委派，任何一步不通过就终止实现流。它后面才接 Codebase Assessment（Phase 1）、Exploration（Phase 2A）、Smart Delegation 与 Independent Verification（Phase 3/4）。

与代码拦截式意图识别相比，它用"零额外推理 + 模型级精准加固 + 开放可扩展"换取了"无硬保证 + 提示词维护成本"，是一种典型的 **harness-engineering**（缰绳工程）取舍。
