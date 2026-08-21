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
| `sisyphus/default.ts` | 基础变体的提示词构建器，**包含完整 Phase 0 Intent Gate**；勘误：主函数不在工厂调用链上（见 §13） |
| `sisyphus/claude-opus-4-8.ts` | Opus 4.8 变体（历史主力，现主力为 Opus 5），包含 Intent Gate + 额外防漂移门 |
| `sisyphus/gemini.ts` | Gemini 专用纠偏覆盖层，含 `buildGeminiIntentGateEnforcement()` |
| `sisyphus/gpt-5-4.ts` / `gpt-5-5.ts` / `kimi-k*.ts` / `glm-5-2.ts` 等 | 各模型原生变体 |
| `sisyphus/index.ts` | 桶导出 |
| `dynamic-agent-core-sections.ts` | 动态段生成器，含 `buildKeyTriggersSection()`（被 Intent Gate 引用） |
| `dynamic-agent-prompt-builder.ts` | 动态段的桶导出 |
| `sisyphus-agent-factory.ts` | `createSisyphusAgent` 工厂 + `resolveSisyphusPromptFamily()` 模型族路由（12 分支，与 runtime reconciler 共享的 single source of truth） |
| `builtin-agents/sisyphus-agent.ts` | agent 入口（`maybeCreateSisyphusConfig`），负责模型解析 + 提示词拼装 + 运行时重建 |
| `sisyphus-dynamic-prompt.ts` | fallback 提示词入口：`buildFallbackSisyphusPrompt()` = Gemini 覆盖层套在动态构建器外 |
| `sisyphus/AGENTS.md` | 变体选择参考文档 |
| `../../model-core/src/agent-model-requirements.ts` | Sisyphus 模型 fallback 链定义 |

**核心事实**：仓库根目录**没有 `opencode.json` 来定义 Sisyphus**（根 `.opencode/` 目录只含 `AGENTS.md`、`command/`、`skills/` 等）。Sisyphus 的 agent 配置（模型、权限、提示词）完全由 TypeScript 代码动态构建。

---

## 3. 实现思路（核心设计哲学）

Intent Gate 的实现思路可以概括为四点：

### 3.1 提示词即逻辑（Prompt-as-Logic），而非代码拦截

绝大多数"意图识别"系统的实现方式是：写一个分类器函数（正则/ML/LLM 调用），在请求进入主循环前做拦截路由。oh-my-openagent **反其道而行**：Intent Gate 是写在系统提示词里的一段**多步决策流程指令**，由 Sisyphus 这个 LLM 自身在每一轮回复中"自我执行"。

- 没有独立的 `classifyIntent()` 函数被调用；
- 没有校验 Intent Gate 言语化输出的 hook（仓库里有一个 `prompt-async-gate-rfc.md`，但那是另一种"async gate"，与 Intent Gate 无关）。勘误补充：确实存在一个代码级 `keyword-detector` hook（`plugin/hooks/create-transform-hooks.ts` 注册），但它的职责是识别 `ulw`/`ultrawork` 等关键词并注入对应指令集——即 README 所说 "Light edition only recognises the ultrawork/ulw keyword"——它做的是**关键词触发的上下文注入**，不是意图分类，也不校验言语化是否发生；
- "门"的强制性来自提示词里的措辞（`MANDATORY`、`NO EXCEPTIONS`、`BLOCKING`、`YOU MUST`）+ 模型对指令的遵循。

这是一种 **"把控制流编码进自然语言"** 的范式。代价是依赖模型指令遵循能力；收益是零额外模型调用、且能处理任意开放性意图（不需要预定义枚举之外的兜底）。（勘误：并非"零开销/零延迟"——每轮 verbalization 约 20–40 token 输出 + 系统提示词常驻输入，见 §13.1-7、§13.3-B。）

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
| Claude Opus 5（当前主力） | `claude-opus-5.ts` | 4.8 骨架 + 三处**反向校准**（见 §13.3）：SCOPE CONSTRAINT（防扩 scope）、DELEGATION CAP（委派过频 → 按域+规模门控，**反转** DEFAULT BIAS: DELEGATE）、OVER-VERIFICATION REMOVAL（自验证只跑一次）；含 Step 0–2.5 全门与 4.8 的两行扩展意图映射 |
| Claude Fable 5 | `claude-fable-5.ts` | 勘误：初版遗漏；文件头自述 "Opus 4.8 direction, top-tier model"，工厂路由优先级在 opus-5 之前（见 §13） |
| Claude Opus 4.8 | `claude-opus-4-8.ts` | 增加 Step 1.5 Turn-Local Intent Reset + Step 2.5 Context-Completion Gate |
| Claude 通用 / fallback | `sisyphus-dynamic-prompt.ts` → `sisyphus-dynamic-prompt-role.ts`（fallback render 链） | 含 Step 0–3 全门（含 1.5/2.5）；注意 `default.ts` 的同名主函数不在工厂调用链上（见 §13） |
| Gemini | `gemini.ts` | fallback 路径上经 `applyGeminiFallbackOverrides()` 叠加 `buildGeminiIntentGateEnforcement()` 强制覆盖层 |
| GPT-5.4 / 5.5 / 5.6 | `gpt-5-4.ts` / `gpt-5-5.ts`（5.5 与 5.6 共用 gpt-5-5 变体） | 块结构化指令 |
| Grok 4.5/4.6 | `grok-4.ts` | 勘误：初版遗漏；验证循环为中心的精简变体（2026-08-16 才从 fallback 分出，见 §13） |
| Kimi K2.6/2.7/K3、GLM-5.2 | 各自文件 | GLM-5.2 为**结构级重写**（`<intent>` 压缩块，非 Step 阶梯），见 §8.3 |

这种"同一套门，按模型失败模式做差异化加固"的思路，是该实现的核心工程价值所在。

### 3.4 运行时重建（Runtime Prompt Reconciliation）

由于提示词是按"配置的模型"烘焙（bake）的，但当用户在 TUI 中临时切换模型族时，已烘焙的提示词会与新模型不匹配。工厂函数 `maybeCreateSisyphusConfig()` 通过 `setSisyphusRuntimePromptContext()` 捕获了一个 `rebuildPromptForModel` 回调，在 system-transform hook 中按运行时模型重建提示词（issue #5297/#5316）。这保证 Intent Gate 始终匹配当前实际跑的模型。

---

## 4. 核心架构：提示词是如何被构建出来的

完整调用链：

```
opencode 启动
  └─ maybeCreateSisyphusConfig()                    [builtin-agents/sisyphus-agent.ts]
       ├─ 读取 AGENT_MODEL_REQUIREMENTS["sisyphus"]  [model-core/agent-model-requirements.ts]
       │     → fallbackChain: [claude-opus-5, kimi-k3, gpt-5.6-sol, glm-5.2, big-pickle]
       ├─ applyModelResolution()  → 解析出实际模型 + variant
       ├─ createSisyphusAgent(model, agents, tools, skills, categories, useTaskSystem)
       │     [sisyphus-agent-factory.ts]
       │     └─ resolveSisyphusPromptFamily(model) 按模型族路由（12 分支，
       │          与 runtime reconciler 共享的 single source of truth）：
       │          - claude-fable-5 / claude-opus-5 / claude-opus-4-8 / claude-opus-4-7 → 各自原生变体
       │          - kimi-k3 / kimi-k2-7 / kimi-k2-6 → 对应 kimi 变体
       │          - gpt-5.5 / gpt-5.6 → buildGpt55SisyphusPrompt()（同族共用）
       │          - gpt-5.4（native）→ buildGpt54SisyphusPrompt()
       │          - glm-5-2 → buildGlm52SisyphusPrompt()
       │          - grok-4（4.5/4.6 共用）→ buildGrok4SisyphusPrompt()
       │          - fallback → buildFallbackSisyphusPrompt()（sisyphus-dynamic-prompt.ts，
       │            Gemini 走此路径并经 applyGeminiFallbackOverrides() 叠加纠偏覆盖层）
       │          （勘误：default.ts 的 buildDefaultSisyphusPrompt 不在调用链上，见 §13）
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
      model: "claude-opus-5", variant: "max" },        // 勘误：曾误记为 claude-opus-4-8
    { providers: ["opencode-go", "kimi-for-coding", "moonshotai", ...],
      model: "kimi-k3" },
    { providers: ["openai", "github-copilot", "opencode", "vercel"],
      model: "gpt-5.6-sol", variant: "medium" },
    { providers: ["zai-coding-plan", "opencode", "bailian-coding-plan", "vercel"],
      model: "glm-5.2" },                              // 勘误：曾误记为 glm-5
    { providers: ["opencode"], model: "big-pickle" },
  ],
  requiresAnyModel: true,
}
```

`requiresAnyModel: true` 表示只要 fallback 链里有任一模型可用，Sisyphus 就会注册。

---

## 5. Intent Gate 工作流程详解（Phase 0）

下面是 `default.ts` 中 Intent Gate 的**完整原文**（[源](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)），按步骤拆解（注意：`default.ts` 主函数不在工厂调用链上，生产路径执行的是 fallback render 与各模型变体中的等价门，内容几乎相同，见 §13.1-3）：

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

### 6.3 Turn-Local Intent Reset（轮次局部意图重置）——Opus 4.8 / Opus 5 变体与 fallback 共有

`claude-opus-4-8.ts` 变体在 Step 1 之后（[源](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-4-8.ts)），`claude-opus-5.ts` 与 fallback render（`sisyphus-dynamic-prompt-role.ts`）同样包含此步（标注 MANDATORY）：

```
### Step 1.5: Turn-Local Intent Reset (apply to EVERY turn)
Reclassify intent from CURRENT message ONLY. NEVER auto-carry "implementation mode" from prior turns.
- Question / explanation / investigation → answer or analyze ONLY. NO todos. NO file edits.
- User still giving context → gather/confirm context FIRST. NO implementation yet.
- Prior turn authorized implementation, current turn asks something different → DROP implementation mode, serve current question.
Implementation authorization does NOT persist. It must be RE-ESTABLISHED by an explicit verb in the current message.
```

**解决问题**：Opus 4.8 倾向于"把上一轮的实现授权延续到这一轮"。这条强制每轮**只看当前消息**重新分类，实现授权**不跨轮延续**，必须由当前消息里的显式动词重新确立。

### 6.4 Context-Completion Gate（上下文完成门）——Opus 4.8 / Opus 5 变体与 fallback 共有

Step 2.5（实现前最后一道门，三处均有；措辞略有差异）：

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

> 勘误/补充：这一偏向是**按模型校准的**，并非全变体统一。Opus 5 变体文件头明确说明其**反转**了该策略——"Opus 5 delegates to subagents MORE readily than prior models, so the 4.8 'DEFAULT BIAS: DELEGATE' push is inverted into domain-and-size gating, with an explicit ban on verify-my-own-work subagents"（[claude-opus-5.ts 文件头](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-5.ts)，见 §13.3）。

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

如 6.3 / 6.4 所述，Step 1.5（轮次重置）和 Step 2.5（上下文完成门）在 **Opus 4.8、Opus 5 与 fallback render 三处共有**——勘误：非 Opus 4.8 独有；但 `default.ts`（不在工厂调用链上）没有。文件头说明了设计依据（Anthropic Opus 4.8 迁移指南 + 4.7 蒸馏）：

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
│  Step 1.5: Turn-Local Intent Reset（Opus 4.8/5 与 fallback 均有）     │
│          只看当前消息，不延续上轮 implementation mode              │
│  Step 2: Check for Ambiguity                                     │
│          单解读→继续 / 多解读差距大→问 / 缺信息→问 / 设计有疑→提   │
│  Step 2.5: Context-Completion Gate（Opus 4.8/5 与 fallback 均有）     │
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

1. **零额外模型调用**：不调用第二个 LLM 做分类，门由主模型自我执行。（勘误：并非"零开销"——每轮强制 verbalization 输出约 20–40 token，且各变体 10–26KB 的系统提示词每请求计入输入 token。）
2. **开放性**：意图映射表是示例而非封闭枚举，能兜底任意意图。
3. **可观测性**：Verbalize 强制模型把决策说出口，用户可见可审计。
4. **自适应配置**：Key Triggers 等动态段随可用 agent/skill 变化。
5. **模型级精准加固**：针对每个模型的已知失败模式做差异化提示词，比"一刀切提示词"有效。

### 10.2 代价与风险

1. **强依赖指令遵循能力**：弱模型可能无视 `MUST`/`NO EXCEPTIONS`（这正是 Gemini 需要单独 enforcement 覆盖层的原因）。
2. **无代码级保证**：门的强制性纯靠提示词，没有运行时校验"模型是否真的输出了 verbalization 行"。理论上模型可以跳过。
3. **提示词膨胀**：每个变体文件数千字节（`claude-opus-4-8.ts` 约 24KB），维护成本高，需为每个新模型写变体。
4. **变体漂移风险**：多个变体各持一份 Intent Gate 副本，内容需手工保持同步。`claude-opus-4-8.ts` 文件头（勘误：初版误将此引文归于 AGENTS.md）自述 "shared dynamic helpers identical to the 4.7 variant so content stays in sync"——但同步仅覆盖共享动态段，静态门内容已经漂移：`default.ts` 无 Step 1.5/2.5，而 fallback render（`sisyphus-dynamic-prompt-role.ts`）有；`default.ts` 的主函数 `buildDefaultSisyphusPrompt` 甚至不在工厂调用链上（仅 `buildTaskManagementSection` 被复用），疑似遗留代码。

### 10.3 与"代码拦截式"意图识别的对比

| 维度 | 代码拦截式（常规） | oh-my-openagent 提示词门 |
|------|--------------------|--------------------------|
| 实现位置 | 请求前置中间件/分类函数 | 系统提示词内 |
| 执行者 | 独立分类器（正则/ML/LLM） | 主模型自身 |
| 延迟 | 额外一次推理 | 零额外模型调用（但有常驻 token 摊销，见 §13.3-B） |
| 强制力 | 代码级（硬保证） | 提示词级（软保证，依赖模型遵循） |
| 可扩展性 | 需改代码加意图类型 | 改提示词表格即可 |
| 可观测性 | 日志 | 模型输出可见 |
| 模型差异化 | 难（一套逻辑） | 易（每模型一变体） |

---

## 11. 关键源文件索引（均为 dev 分支 raw 链接）

- 提示词变体目录：[`packages/omo-opencode/src/agents/sisyphus/`](https://github.com/code-yeongyu/oh-my-openagent/tree/dev/packages/omo-opencode/src/agents/sisyphus)
- 基础变体（含完整 Intent Gate，**主函数不在工厂调用链上**）：[`sisyphus/default.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/default.ts)
- Opus 5 变体（当前主力，含 Step 1.5 / 2.5 + 反向校准）：[`sisyphus/claude-opus-5.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-5.ts)
- 工厂路由（12 分支 single source of truth）：[`sisyphus-agent-factory.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus-agent-factory.ts)
- fallback 提示词入口（含 Gemini 覆盖层挂载）：[`sisyphus-dynamic-prompt.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus-dynamic-prompt.ts)
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
3. **模型变体加固**：每个主力模型一个变体文件，针对该模型失败模式做差异化校准（Gemini 加 enforcement 覆盖层、Opus 4.8/5 与 fallback 均含轮次重置与上下文完成门；Opus 5 更将 DELEGATE 偏向**反转**为按域+规模门控——校准是双向的，见 §13.3），并由工厂按模型族路由 + 运行时重建。

工作流程上，Intent Gate 是 Sisyphus 每一轮回复的**第一道也是贯穿始终的认知工序**：先言语化意图、再分类、查歧义、校验授权与委派，任何一步不通过就终止实现流。它后面才接 Codebase Assessment（Phase 1）、Exploration（Phase 2A）、Smart Delegation 与 Independent Verification（Phase 3/4）。

与代码拦截式意图识别相比，它用"零额外模型调用 + 模型级精准校准 + 开放可扩展"换取了"无硬保证 + 提示词维护成本"，是一种典型的 **harness-engineering**（缰绳工程）取舍。

---

## 13. 复盘：查证过程与批判性分析

> 本节是全文的复盘层：§13.1 列出初版文档的事实错误及权威修正来源；§13.2 分析错误根源；§13.3 对文档核心观点做批判性再审视；§13.4 给出复盘结论。
> **查证基线**：dev 分支，工厂文件最新提交 [`a88f1e2`](https://github.com/code-yeongyu/oh-my-openagent/commit/a88f1e2c753e9081f65a4720afe304e7fa47c2a2)（2026-08-16，"route Grok 4.5/4.6 to a native model-specific prompt"）。dev 是活跃移动靶，本节结论同样有半衰期。

### 13.1 勘误清单（初版 → 查证后）

| # | 初版说法 | 查证后事实 | 权威来源 |
|---|----------|-----------|----------|
| 1 | fallback 主模型 `claude-opus-4-8`，GLM 为 `glm-5` | 主模型 **`claude-opus-5`**（variant `"max"`），GLM 为 **`glm-5.2`**；完整链：claude-opus-5 → kimi-k3 → gpt-5.6-sol → glm-5.2 → big-pickle | [`agent-model-requirements.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/model-core/src/agent-model-requirements.ts) |
| 2 | Step 1.5 / 2.5 为 Opus 4.8 变体专属 | **三处共有**：`claude-opus-4-8.ts`、`claude-opus-5.ts`、fallback render 链；`default.ts` 反而没有 | 三变体源码 |
| 3 | `default.ts` 是被工厂默认调用的基础构建器 | `createSisyphusAgent` 的 switch 共 **12 分支**（11 个模型族 + fallback），无一路调用 `buildDefaultSisyphusPrompt`；fallback 走 `buildFallbackSisyphusPrompt`（[`sisyphus-dynamic-prompt.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus-dynamic-prompt.ts)）；`default.ts` 仅 `buildTaskManagementSection` 被各变体复用，主函数疑似遗留代码 | [`sisyphus-agent-factory.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus-agent-factory.ts) |
| 4 | §4 调用链图含旧 fallbackChain（opus-4-8/glm-5）与"默认 → buildDefaultSisyphusPrompt" | 已同步为 claude-opus-5 / glm-5.2 / 12 分支 / fallback 真实路径 | 同上 |
| 5 | 变体清单遗漏 Grok 4.5/4.6 | `grok-4.ts`（4.5/4.6 共用，验证循环为中心的精简变体）。提交 `a88f1e2`（2026-08-16）信息明说此前 Grok 走 "generic Claude-flavored fallback"——该变体仅存在 5 天 | 工厂源码 + 提交 `a88f1e2` |
| 6 | 变体清单遗漏 Claude Fable 5 | `claude-fable-5.ts` 存在，工厂路由优先级在 opus-5 之前；文件头自述 "Opus 4.8 direction, top-tier model" | [`sisyphus-agent-factory.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus-agent-factory.ts)、[`sisyphus/index.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/index.ts) |
| 7 | "零额外推理开销" | 应为"**零额外模型调用**"：每轮 verbalization 约 20–40 输出 token；各变体 10–26KB 系统提示词每轮计入输入 token | 各变体源码 |
| 8 | "没有 hook 做意图校验" | 存在代码级 `keyword-detector` hook（识别 `ulw`/`ultrawork` 关键词注入指令集），但不做意图分类、不校验言语化——初版结论方向对，表述过强 | `plugin/hooks/create-transform-hooks.ts` |
| 9 | 引文出处误标 AGENTS.md | 出自 `claude-opus-4-8.ts` 文件头注释 | 源码文件头 |

### 13.2 错误根源分析（初版为什么会错）

1. **信源时点错配**。官网/README 是宣传层快照，滞后于 dev 分支演进：宣传页把 Intent Gate 标为 PHASE 1，源码内部是 Phase 0；`claude-opus-4-8`/`glm-5` 是历史主力，dev 上已迁移。grok-4 变体 5 天前才从 fallback 分出——**dev 分支的信息半衰期以周计**，凡未锚定提交的"当前"结论都不可靠。
2. **以文档代替代码做路由结论**。初版引用 `sisyphus/AGENTS.md`（变体选择参考）推断调用关系，而路由事实只活在 `sisyphus-agent-factory.ts` 的 switch 里。仓库内文档同样可能滞后于代码——"仓库里写的"不等于"代码里跑的"。
3. **从命名/导出/注释推断行为，未验证调用点**。`default.ts` 的命名、桶导出、`index.ts` 头注释（"Base implementation for Claude and general models"）都在暗示"默认路径"，但 switch 证明无人调用它。**函数被导出 ≠ 被调用；注释自称基础 ≠ 真在链路上**。连带后果：本文 §5 引用的门文本出自 `default.ts`（死代码），生产路径上真正执行的是 fallback render 与各模型变体中的等价物（内容几乎相同，引用尚可成立，但出处应如此理解）。
4. **绝对化表述缺乏成本核算**。"零额外推理开销"把"零额外模型调用"偷换成"零开销"，未核算常驻输入 token 与每轮输出 token（详见 §13.3 观点 B）。

### 13.3 核心观点批判性再审视

**观点 A："Intent Gate 是纯提示词工程产物，无代码级保证" —— 方向正确，表述需细化。**

README 功能行本身写明 IntentGate 有两档："Ultimate"（提示词门）与 "Light edition only recognises the ultrawork/ulw keyword"（即 `keyword-detector` hook 的代码级关键词匹配）。准确的说法是：**同一功能，Ultimate 档用提示词实现，Light 档用代码实现**——代码级意图通道并非不存在，而是被定位为弱模型的降级路径。初版"非此即彼"的框架忽略了作者自己维护着一条"提示词门之外的代码级底线"。

更进一步的批判：系统已有 system-transform hook（运行时重建）与 keyword-detector hook（关键词注入）两类代码挂载点，技术上完全可以在工具调用前校验"本轮是否输出了 verbalization 行"，但作者没做。Gemini 覆盖层里的 "Your next tool call is INVALID without it" 是**修辞而非机制**——运行时不会真的拒绝该调用。所有 `MANDATORY`/`NO EXCEPTIONS` 的强制性最终折算为同一种东西：对模型指令遵循概率的信任。

**观点 B："零额外推理"是核心优势 —— 被夸大，应重新核算。**

真实的成本结构是把分类成本从"一次性前置调用"改造为"常驻性摊销"：(a) 每轮 20–40 token 的 verbalization 输出；(b) 10–26KB 系统提示词的常驻输入。对 N 轮会话，输入侧增量为 N × 提示词体积，随轮数线性放大；独立分类器则是一次性成本。在长会话 + 贵模型组合下，"零额外推理"可能反而**更贵**。公允地说，verbalization 的 token 买到了可观测性（决策依据用户可见），这笔钱不算白花——但初版对比表曾把这一格记为"零额外"（已勘误，见 §10.3）。

**观点 C："模型级精准加固是核心工程价值" —— 成立，且查证后得到强化。**

新证据：Opus 5 变体不只是"加固"，而是**反向校准**——4.8 的失败模式是委派不足（推 DELEGATE），Opus 5 的失败模式是委派过频（反转为 domain-and-size 门控 + 禁止自我验证型子 agent）；4.8 要压 narration，Opus 5 的 effort 控制思考量而非回复长度；Opus 5 自验证能力强，重复验证脚手架被整体移除（OVER-VERIFICATION REMOVAL）。同一套门，按模型偏置**双向调节**——这说明作者理解的"门"不是"约束越多越好"，而是**抵消特定模型特定偏置的负反馈控制器**。这是提示词工程从"加约束"进化到"做校准"的实证，比初版"差异化加固"的表述更有信息量。

#### 观点 C 附表：Opus 5 三处反向校准对照（含代码位置）

> 行号基线：dev 分支 2026-08-21 快照，经 ripgrep + .NET ReadAllLines 双重核验。[`claude-opus-5.ts`](https://github.com/code-yeongyu/oh-my-openagent/blob/86ae07264ebc964a7090a2f4ee32bb81755cc4c6/packages/omo-opencode/src/agents/sisyphus/claude-opus-5.ts) 自提交 [`86ae072`](https://github.com/code-yeongyu/oh-my-openagent/commit/86ae07264ebc964a7090a2f4ee32bb81755cc4c6)（2026-07-24，"add Claude Opus 5-native prompt variant"，该文件唯一提交）后未再改动，行号可按该提交锚定；[`claude-opus-4-8.ts`](https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/refs/heads/dev/packages/omo-opencode/src/agents/sisyphus/claude-opus-4-8.ts) 为 dev 快照行号。

**改动原因与作者意图**：三处反向校准共享同一根因——Opus 5 与 4.8 的失败模式沿"行动量"轴线反向分布：4.8 动力不足（小决策过度询问、该委派却不委派、需被要求才验证），提示词的角色是**油门**，推它去做；Opus 5 动力过剩（自作主张扩 scope、过度委派 subagent、无提示也反复自验证），提示词的角色翻转为**刹车**，把超出请求的主动拉回来。作者意图有据可查：其一，方法论是"最小增量"——文件头明言 "Opus 5 runs well on 4.8 prompts, so only the documented behavior deltas are tuned"，即 4.8 骨架（Step 0–3 门、动态段拼装、Phase 结构）原样继承，只调三处行为增量，依据是 Anthropic 官方 "Prompting Claude Opus 5" 指南；其二，三处各有具体动机——SCOPE 硬栅栏针对"重诠释任务应该是什么"的字面漂移（保留 4.8 的自主决策收益，只堵越界通道），DELEGATION CAP 针对小任务上委派的成本与时延放大（"Delegation multiplies cost and wall-clock time on small tasks"），OVER-VERIFICATION REMOVAL 针对重复验证的 token 浪费（"repeat-verification scaffolding wastes tokens per Anthropic"）；其三，证据门本身不减——done 的定义（真实使用、证据而非断言）原样保留，移除的只是重复执行（提交信息："verification section reframed to evidence-once"）。一句话：作者把提示词从"约束集"改造成**负反馈控制器**——同一套门，对 4.8 促动、对 Opus 5 限动，校准方向由官方文档记载的模型偏置决定。

| # | 4.8 基线（被替换的原方向） | Opus 5 反转（新方向） | 代码位置 |
|---|---------------------------|----------------------|----------|
| ① SCOPE CONSTRAINT | **SMALL-DECISION AUTONOMY**：4.8 小决策过度询问 → counter 是"不许问，自己定"（OVER-ASKING 计数器） | 压 **SCOPE EXPANSION**（"add steps that were not requested and reinterpret what the task 'should' be"）：自主决策保留，但加硬范围栅栏——"Deliver what was asked, at the scope intended... NEVER quietly narrow, widen, or transform it"；认为请求有误→"say so in ONE sentence and continue with the task as asked" | opus-5：文件头 L7–9；`<self_knowledge>` #2 L113。4.8：文件头 L7–8；#3 OVER-ASKING L100 |
| ② DELEGATION CAP | **EXPLICIT CAPABILITY TRIGGERS**：4.8 能力欠伸 → "DEFAULT BIAS: DELEGATE. A matching trigger means delegate NOW - do not deliberate over whether delegation is 'worth the overhead'"（Step 3 三问以"证明自己干合理"收尾） | 压 **OVER-DELEGATION**（"reach for subagents more readily than the work justifies"）：三问重排、默认自己干——Q3 变为 "Neither, or you can finish it in a handful of tool calls → do it YOURSELF"；总纲 "**DELEGATE BY DOMAIN AND SIZE, NOT BY DEFAULT.** Delegation multiplies cost and wall-clock time on small tasks"；"NEVER spawn a subagent to verify or double-check your own work" | opus-5：文件头 L10–13；#3 L114；Step 3 正文 L255–263（L263 为反转总纲）。4.8：文件头 L9–11；Step 3 L241–249（L249 为 DELEGATE 原句） |
| ③ OVER-VERIFICATION REMOVAL | `<verification>` 首条即 "VERIFY before claiming done... EVERY line should run at least once"——4.8 需**被要求**才验证 | 压 **OVER-VERIFICATION**（"You already verify your own work"，自验证是默认能力）：证据门保留（仍定义 done）但只跑一次——"Run each evidence gate in \<verification\> ONCE, then stop - no extra verification passes, no re-running green suites"；"This is not repeat verification - it is the definition of done... it runs once" | opus-5：文件头 L14–16；#4 L115；`<verification>` L151（ONCE 规则）、L175（runs-once 免责）。4.8：`<verification>` L136–162（L137 为基线句） |

附注：

1. **保留例外**：Phase 2C Failure Recovery 的 "Re-verify after EVERY attempt" 在两版均存在（4.8 L389 / opus-5 L403）——移除的只是"绿门重跑/重复验证已完成结论"，失败恢复场景的重验证不在移除之列。
2. **作者自证**：提交 `86ae072` 的 message 原文即为此框架定性——"self_knowledge counters flipped to Opus 5's documented deltas: scope expansion, over-delegation, over-verification... (replacing 4.8's over-asking + capability under-reach counters)"、"delegation bias inverted"、"verification section reframed to evidence-once"。"反向校准"的定性出自作者本人，非本文推断。
3. **第四、五项不在其列**：同文件还有 LONG RESPONSES（#5，L116）与 NARRATION CADENCE（含结尾 `<tone_preference>` 提醒，L469–471）两项调优，属叙述风格校准，不在"反向"三件套内（它们替换的是 4.8 的 SILENCE DEFAULT，方向相同：都是压输出长度/narration）。

**观点 D："变体漂移风险" —— 被源码证实，且比初版写的更具体。**

漂移的活标本就是 `default.ts`：主函数掉出调用链，但导出仍在、`index.ts` 头注释仍自称 "Base implementation"。代码活着、注释活着、语义已死——没有任何机制会报告这件事。公允面同样成立，作者有三层制度性防御：(1) 11 个 `build*` 动态段函数被所有变体共享；(2) `resolveSisyphusPromptFamily` 作为路由 single source of truth 与 runtime reconciler 共享（注释明说）；(3) 每个变体文件头写明设计依据（如 Anthropic 官方 Opus 5 提示指南）。防御覆盖了"动态段同步"与"路由一致性"，但**不覆盖静态门内容的拷贝漂移**——Step 1.5/2.5 在三处的措辞已有差异，也没有机制保证新变体（如 fable-5）与旧变体的门语义一致。

**观点 E："门是终止条件集合，不是路由函数" —— 准确，值得保留并拔高。**

这正是提示词门与代码门的本质差异：代码拦截门的语义是"闸门不放行"，失败模式是闸门 bug；提示词门的语义是"模型自己决定不发车"，失败模式是**自律失效**。所以才有 Gemini enforcement 这种"用更强的修辞给自律加他律"的补丁，以及 Light 档这种"放弃自律改用他律"的降级。整个系统可以读作：在"信任模型自律"与"不信任"之间，按模型逐一定价。

**观点 F（复盘新增）：可维护性天花板。**

12 个路由分支 × 每个含一份 20KB+ 提示词副本 × 静态门内容靠人工同步。每新增一个主力模型 = 写一个新变体 + 重新校准门的语义（fable-5 的出现说明该模式仍在扩张）。作为对照，"单一通用门 + 模型补丁层"（fallback + gemini overlay 的结构）扩展成本更低，但作者显然认为按模型重写的收益（贴合失败模式）大于维护成本——这是一个可以被数据检验的赌注，仓库里未见检验数据。

### 13.4 复盘结论

1. **查证纪律**：对活跃 dev 分支的论断必须锚定提交（本节锚定 `a88f1e2`，2026-08-16）；路由/调用类结论只能来自调用点（switch、调用链），不能来自命名、导出、注释或仓库内文档。
2. **核心架构判断存活**：Intent Gate = 提示词内多步决策门 + 动态段拼装 + 模型变体 + 运行时重建——经全部查证后成立，且 Opus 5 的"反向校准"证据（观点 C）使"模型级校准"这层价值更立体。
3. **最需要修正的心智模型**：把"零开销""无代码级保证""纯提示词"这类绝对化表述，替换为分档（Light/Ultimate）、分成本（输入/输出 token）、分模型（双向校准）的具体陈述。README 的分档、Opus 5 的 DELEGATE 反转、`default.ts` 的失联，共同说明这个系统里几乎没有"一刀切"的事实。
