# Hephaestus 智能体架构技术文档

> **来源**: [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) (omo)
> **最后更新**: 2026-07-23
> **文档版本**: v1.1  

---

## 目录

1. [概述](#1-概述)
2. [系统定位](#2-系统定位)
3. [核心架构](#3-核心架构)
4. [模型变体与提示词工程](#4-模型变体与提示词工程)
5. [业务流程](#5-业务流程)
6. [自治铁律](#6-自治铁律)
7. [工具与委托机制](#7-工具与委托机制)
8. [配置与部署](#8-配置与部署)
9. [与其他智能体的协作](#9-与其他智能体的协作)
10. [附录](#10-附录)

---

## 1. 概述

**Hephaestus**（赫菲斯托斯）是 Oh-My-OpenAgent (omo) 多模型智能体编排系统中的**自主深度工作者（Autonomous Deep Worker）**。其设计哲学是"给目标，不给步骤"——接收高层次目标而非逐步指令，并端到端自主执行完成。

Hephaestus 的命名源自希腊神话中的锻造之神，omo 团队赋予其副标题 **"The Legitimate Craftsman"（合法的工匠）**，暗含对 Anthropic 封锁 OpenCode 的回应——既然被封锁，就打造一个 GPT 原生的自主智能体。

### 核心特征

| 特征 | 描述 |
|------|------|
| **自主性** | 接收目标即执行，无需逐步确认 |
| **深度探索** | 自动并行启动 2-5 个探索/图书馆智能体 |
| **端到端完成** | 不停止于中间状态，直到任务完全完成 |
| **严格验证** | 通过 lsp_diagnostics、构建/测试、Manual QA Gate 三重验证 |
| **模型专用** | 针对 GPT-5.6/5.5/5.4 有专门的提示词变体 |

---

## 2. 系统定位

### 2.1 在 omo 智能体体系中的位置

omo 系统共有 **11 个内置智能体**，分为两个层级：

```
┌─────────────────────────────────────────────────────────────┐
│                    主智能体 (Primary)                        │
├─────────────────────────────────────────────────────────────┤
│  Sisyphus    │  主编排器，任务规划与协调                       │
│  Hephaestus  │  自主深度工作者 (本文档主角)                     │
│  Prometheus  │  战略策划者，面试式需求澄清                       │
│  Atlas       │  计划执行者，按 Prometheus 计划执行               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    子智能体 (Subagent)                       │
├─────────────────────────────────────────────────────────────┤
│  Oracle      │  架构顾问，只读推理模型                          │
│  Librarian   │  文档/开源代码搜索                               │
│  Explore     │  代码库快速搜索                                  │
│  Multimodal-Looker │ 多模态视觉分析                           │
│  Metis       │  计划顾问，差距分析                              │
│  Momus       │  质量审查者                                    │
│  Sisyphus-Junior │  任务执行者                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 典型组装顺序

```
Sisyphus → Hephaestus → Prometheus → Atlas
```

Hephaestus 在需要**深度架构推理、复杂调试、跨域知识综合**时被激活。

### 2.3 与 Sisyphus + ultrawork 的对比

| 维度 | Hephaestus | Sisyphus + `ulw` |
|------|-----------|------------------|
| **主模型** | GPT-5.6 Sol / GPT-5.5 | Claude Opus 4.7 / Kimi K2.6 / GPT-5.5 |
| **工作方式** | 自主深度工作者 | 关键词激活的 ultrawork 模式 |
| **最佳场景** | 复杂架构工作、深度推理 | 一般复杂任务、"直接做"场景 |
| **规划方式** | 执行中自规划 | 使用 Prometheus 计划（如有） |
| **委托策略** | 重度使用 explore/librarian | 基于类别的委托 |
| **Temperature** | 未显式设置（使用模型默认） | 未显式设置（使用模型默认） |

---

## 3. 核心架构

### 3.1 代码结构

```
packages/omo-opencode/src/agents/hephaestus/
├── AGENTS.md                          # 智能体元数据与行为说明
├── agent.ts                           # 工厂函数 createHephaestusAgent()
├── agent.test.ts                      # 单元测试
├── delegation-table-contract.test.ts  # 委托表契约测试
├── gpt-5-6.ts                         # GPT-5.6 专用提示词 (结果优先)
├── gpt-5-6-registration.test.ts      # GPT-5.6 注册测试
├── gpt-5-5.ts                         # GPT-5.5 专用提示词 (任务纪律)
├── gpt-5-4.ts                         # GPT-5.4 专用提示词 (XML 标签)
├── gpt.ts                             # 通用 GPT 提示词 (fallback，含 GPT-5.3 Codex)
├── index.ts                           # Barrel 导出
└── openai-fast-alias.test.ts          # OpenAI 快速别名测试
```

### 3.2 工厂函数

`agent.ts` 中的 `createHephaestusAgent()` 负责创建 Hephaestus 智能体配置：

```typescript
export function createHephaestusAgent(
  model: string,
  availableAgents?: AvailableAgent[],
  availableToolNames?: string[],
  availableSkills?: AvailableSkill[],
  availableCategories?: AvailableCategory[],
  useTaskSystem = false,
): AgentConfig {
  // ...
  return {
    description: "Autonomous Deep Worker - goal-oriented execution...",
    mode: "primary",
    model,
    maxTokens: 32000,
    prompt,
    color: "#D97706",
    permission: {
      question: "allow",
      call_omo_agent: "deny",
      ...getFrontierToolSchemaPermission(model),
    },
    reasoningEffort: "medium",
  };
}
```

### 3.3 模型路由

```typescript
export function getHephaestusPromptSource(model?: string): HephaestusPromptSource {
  assertHephaestusSupportedModel(model);
  if (model && isGpt5_6Model(model)) return "gpt-5-6";
  if (model && isGpt5_5Model(model)) return "gpt-5-5";
  if (model && GPT_5_4_RE.test(extractModelName(model))) return "gpt-5-4";
  return "gpt";
}
```

支持的模型模式（`HephaestusPromptSource` 类型：`"gpt-5-6" | "gpt-5-5" | "gpt-5-4" | "gpt"`）：
- `gpt-5.6*` → GPT-5.6 结果优先提示词
- `gpt-5.5*` → GPT-5.5 任务纪律提示词
- `gpt-5.4*` → XML 标签结构化提示词
- `gpt-5.3-codex*` 及其他 GPT → 通用 GPT 提示词 (fallback)

---

## 4. 模型变体与提示词工程

Hephaestus 针对每个 GPT 版本都有专门的提示词变体，体现了精细化的提示词工程。

### 4.1 GPT-5.6: 结果优先 (Outcome-First)

**设计原则**（源自 `gpt-5-6.ts`）：
- 更短的提示词，优先结果而非过程
- 泛化的简洁指令有害（模型可能用更短的产物替代）
- 用优先级表达代替通用简洁指令
- ALWAYS/NEVER 仅用于真正的不变量

**核心模板结构**（HEPHAESTUS_GPT_5_6_TEMPLATE）：

```
# Autonomy
# Goal
# Discovery & Retrieval
# Parallelize
# Operating Loop (Explore -> Plan -> Implement -> Verify -> Manually QA)
# Manual QA Gate
# Failure Recovery
# Pragmatism & Scope
# AGENTS.md
# Output
# Tool Use
# Success Criteria
# Stop Rules
# Task Tracking
```

### 4.2 GPT-5.5: 任务纪律 (Task Discipline)

**设计原则**（源自 `gpt-5-5.ts`）：
- 温暖但克制的语调
- 高效沟通——提供足够上下文让用户信任工作，然后停止
- 不奉承、不叙述、不填充
- 默认实现，不提议

**关键段落**：

```
# Tone
Warm but spare. Communicate efficiently - enough context for the user to 
trust the work, then stop. No flattery, no narration, no padding.

# Autonomy and Persistence
Default: implement, don't propose. Unless the user is asking a question, 
brainstorming, or explicitly requesting a plan, assume they want code and 
tools, not a description of one.
```

### 4.3 GPT-5.4: XML 标签结构化

**设计原则**（源自 `gpt-5-4.ts`）：
- 人格/语调放在位置 1 以实现强语调启动
- 散文式指令，不使用 FORBIDDEN/MUST/NEVER 修辞
- 3 个针对性提示块：tool_persistence, dig_deeper, dependency_checks
- GPT-5.4 遵循指令良好——信任它，减少威胁性语言

**架构（9 个 XML 标签块）**：

```xml
<identity>      - 角色、人格/语调、自主性、范围
<intent>        - 意图映射、复杂度分类、歧义协议
<explore>       - 工具选择、持久化、深入挖掘、依赖检查、并行
<constraints>   - 硬性限制 + 反模式
<execution>     - 5 步工作流、验证、失败恢复、完成检查
<tracking>      - Todo/任务纪律
<progress>      - 更新风格与示例
<delegation>    - 类别+技能、提示结构、会话连续性、Oracle
<communication> - 输出格式、语调指导
```

### 4.4 通用 GPT: 基础提示词 (Fallback)

`gpt.ts` 提供了最全面的基础提示词（fallback），包含：
- 身份定义（Senior Staff Engineer）
- 硬约束（Hard Constraints）
- 意图门控（Intent Gate）
- 探索与研究阶段
- 执行循环（EXPLORE → PLAN → IMPLEMENT → VERIFY → Manually QA）
- 任务纪律
- 进度更新
- 代码质量与验证
- 失败恢复

---

## 5. 业务流程

### 5.1 完整业务流程图

> **注意**：以下流程综合了 GPT-5.5/5.6 最新版提示词。早期版本（GPT-5.3 Codex / 旧 GPT prompt）的流程略有不同（有独立的 DECIDE 步骤和 5 类 Intent Classification），但新版已统一为以下结构。

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户触发方式                               │
│  ┌─────────────────┐  ┌─────────────────┐                    │
│  │ 1. Tab 选择     │  │ 2. ultrawork    │                    │
│  │    Hephaestus   │  │    关键词激活   │                    │
│  └────────┬────────┘  └────────┬────────┘                    │
│           └─────────┬──────────┘                              │
│                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Hephaestus 接收目标 (Goal)                │ │
│  │         "给目标，不给步骤" — 自主执行哲学             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                     │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ① 意图推断 (Intent Inference)                         │ │
│  │     将用户表面表达映射为真实意图和行动                    │ │
│  │     例: "Why is A broken?" → 修 A                       │ │
│  │     例: "Did you do X?" (没做) → 现在做 X               │ │
│  │     纯问题仅当用户明确说 "just explain" 等              │ │
│  │     输出：一行意图声明                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                     │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ② 探索阶段 (Discovery & Retrieval)                    │ │
│  │     ├─ 首轮：并行启动 2-5 个 Explore/Librarian 智能体  │ │
│  │     │   └─> 代码库搜索、模式发现、文档检索             │ │
│  │     ├─ 同时进行直接文件读取                              │ │
│  │     ├─ 追加条件：核心问题未回答 / 缺关键事实 /          │ │
│  │     │         二阶信息浮现 / 需特定文档                  │ │
│  │     └─ 停止条件：足够上下文 / 信息重复 / 2轮无新数据    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                     │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ③ Operating Loop (可多轮)                              │ │
│  │  ┌───────────────────────────────────────────────────┐  │ │
│  │  │ Plan ──> Implement ──> Verify ──> Manually QA    │  │ │
│  │  │   ↑                                  │            │  │ │
│  │  │   └──────── 验证失败时回退 ──────────┘            │  │ │
│  │  │                                                   │  │ │
│  │  │ Plan: 文件列表 + 变更 + 依赖；最简单 25% 可跳过   │  │ │
│  │  │ Implement: 手术式变更，匹配代码库风格              │  │ │
│  │  │ Verify: lsp_diagnostics + 测试 + 构建（并行）     │  │ │
│  │  │ Manually QA: 按交付物类型通过使用表面验证          │  │ │
│  │  └───────────────────────────────────────────────────┘  │ │
│  │                                                           │ │
│  │  委托决策：                                               │ │
│  │  - 默认自执行 (Direct execution is default)              │ │
│  │  - 仅当工作单元明显超出单次连贯编辑时 → 委托 category    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                     │                                         │
│                     ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ④ 完成/失败处理                                      │ │
│  │     ├─ 成功: Success Criteria 全部满足 → Done           │ │
│  │     └─ 失败:                                           │ │
│  │         ├─ 尝试不同方法 (非小修小补)                   │ │
│  │         ├─ 3次失败后: STOP + 回滚 + 文档化             │ │
│  │         └─ 咨询 Oracle → 询问用户                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 操作循环详解

Hephaestus 遵循 **Explore → Plan → Implement → Verify → Manually QA** 的操作循环（GPT-5.5/5.6 版本）。早期版本（GPT-5.3 Codex / 旧 GPT prompt）有独立的 DECIDE 步骤，新版已将委托决策融入 Operating Loop。

#### 5.2.1 Explore（探索）

- **启动 2-5 个 explore/librarian 智能体并行运行**
- 使用 `run_in_background=true`
- 同时进行直接文件读取
- 目标：在第一次编辑前建立完整的心智模型

#### 5.2.2 Plan（规划）

- 列出要修改的文件
- 明确具体变更
- 分析依赖关系
- 使用 `update_plan` 进行非平凡工作
- 跳过最简单 25% 工作的规划
- 绝不做单步计划

#### 5.2.3 Implement（实现）

- **手术式变更**：匹配现有代码风格
- 命名、缩进、导入、错误处理——即使与自己的想法不同也要匹配
- 应用最小正确变更
- 修复周围代码时不重构

#### 5.2.4 Verify（验证）

- `lsp_diagnostics` 在修改的文件上并行运行
- 相关测试（模式：`foo.ts` → `foo.test.ts`）
- 类型检查
- 构建（如适用）

#### 5.2.5 Manually QA（手动 QA 关卡）

> "Diagnostics catch type errors, not logic bugs; tests cover only what their authors anticipated."

"完成"要求**亲自通过工件的表面使用它并观察到它在工作**：

| 表面类型 | 验证方式 |
|---------|---------|
| **TUI / CLI / shell 二进制** | 在 `interactive_bash` (tmux) 中启动：快乐路径、一个错误输入、`--help`、读取渲染输出 |
| **Web / 浏览器渲染 UI** | 加载 `playwright` 技能，驱动真实浏览器：点击、填充、观察控制台 |
| **HTTP API / 运行服务** | 用 `curl` 或驱动脚本命中实时进程 |
| **Library / SDK / 模块** | 编写最小驱动脚本导入并执行新代码 |
| **无匹配表面** | 做真实用户会做的来发现它是否工作 |

---

## 6. 自治铁律

Hephaestus 的核心设计是**最大化自主性**，其铁律如下：

### 6.1 "DO NOT Ask - Just Do"

**禁止问**：
- ❌ "Should I proceed with X?" → **直接做**
- ❌ "Do you want me to run tests?" → **直接运行**
- ❌ "I noticed Y, should I fix it?" → **修复或在最终消息中记录**
- ❌ 部分实现后停止 → **100% 完成或不做**

**正确行为**：
- ✅ 保持前进直到**完全完成**
- ✅ 运行验证（lint、测试、构建）**无需询问**
- ✅ 做决定。仅在**具体失败**时修正路线
- ✅ 在最终消息中记录假设，而非中途提问
- ✅ 需要上下文？立即在后台启动 explore/librarian

### 6.2 意图推断表

| 表面形式 | 真实意图 | 行动 |
|---------|---------|------|
| "Did you do X?" (你没做) | 现在做 X | 简要确认，做 X |
| "How does X work?" | 理解以修复或改进 | 探索，然后行动 |
| "Can you look into Y?" | 调查并解决 | 调查，然后解决 |
| "What's the best way to do Z?" | 用最佳方式做 Z | 决定，然后实现 |
| "Why is A broken?" / "Seeing error B" | 修复 A 或 B | 诊断，然后修复 |
| "What do you think about C?" | 评估并实现 | 评估，然后行动 |

**纯问题（无行动）仅当所有条件满足**：
- 用户明确说 "just explain" / "don't change anything"
- 没有可操作的代码库上下文
- 没有提到问题或改进

### 6.3 硬性不变量

无论压力多大都不可协商（GPT-5.6 版本，4 条）：

- **绝不**删除失败的测试以获得绿色构建，**绝不**弱化测试使其通过
- **绝不**使用 `as any`、`@ts-ignore` 或 `@ts-expect-error` 压制类型错误
- **绝不**在没有明确批准的情况下使用破坏性 git 命令（`reset --hard`、`checkout --`、force-push），**绝不**未经要求修改提交
- **绝不**编造引用、工具输出或验证结果

> **版本差异**：GPT-5.5 版本有 6 条不变量，额外包含"绝不回退未做的更改"和"绝不修改提交"。GPT-5.6 精简为 4 条核心不变量。

### 6.4 失败恢复协议

```
第 1 次失败 → 尝试不同的方法（不同算法、库或模式，非小修小补）
     ↓
第 2 次失败 → 再次尝试不同的方法
     ↓
第 3 次失败 → STOP
     ├─ 回退到最后已知良好状态
     ├─ 记录每次尝试及失败原因
     ├─ 咨询 Oracle（同步，完整失败上下文）
     └─ 如果 Oracle 无法解决 → 询问用户一个精确问题
```

---

## 7. 工具与委托机制

### 7.1 并行执行原则

```
独立工具调用在同一响应中并行运行，绝不顺序执行。
这是速度和准确性的主要杠杆。
```

- 每个独立 shell 命令都是独立的工具调用
- 不要在单个调用中用 `;` 或 `&&` 链接不相关的步骤
- 每次文件编辑后，在所有修改的文件上并行运行 `lsp_diagnostics`

### 7.2 子智能体委托

Hephaestus 可以委托给以下子智能体：

| 子智能体 | 类型 | 用途 |
|---------|------|------|
| **Explore** | `subagent_type="explore"` | 代码库搜索、模式发现 |
| **Librarian** | `subagent_type="librarian"` | 文档检索、开源代码参考 |
| **Oracle** | `subagent_type="oracle"` | 架构咨询（只读） |
| **Category** | `task(category="...")` | 基于类别的任务委托 |

### 7.3 委托提示结构

不同模型版本的子智能体提示结构不同：

**GPT-5.5 版本（4 字段）**：

```
1. CONTEXT: 什么任务、哪些模块、什么方法
2. GOAL: 结果将解锁什么决策
3. DOWNSTREAM: 结果将如何被使用
4. REQUEST: 找什么、返回格式、跳过什么
```

**GPT-5.6 版本（6 字段，更严格）**：

```
1. CONTEXT: 什么任务、哪些模块、什么方法
2. GOAL: 使子智能体完成的唯一结果（用结果和约束表达，非机制）
3. STOP WHEN: 结束运行的精确可观察条件
4. EVIDENCE: 子智能体返回什么让你能"看到"（而非信任）条件成立
5. DOWNSTREAM: 结果将如何被使用
6. REQUEST: 找什么、返回格式、跳过什么
```

> **关键区别**：GPT-5.6 增加了 STOP WHEN 和 EVIDENCE 字段，要求子智能体有明确的停止条件和可观察的证据，而非仅靠自我报告。

### 7.4 背景任务管理

- **收集结果**：使用背景任务 ID (`bg_...`) 通过 `background_output(task_id="bg_...")`
- **继续会话**：使用延续 ID (`ses_...`) 通过 `task(task_id="ses_...")`
- **取消任务**：在最终答案前单独取消可丢弃任务：`background_cancel(taskId="...")`
- **禁止**：`background_cancel(all=true)` —— 这会杀死尚未收集结果的任务

---

## 8. 配置与部署

### 8.1 配置示例

在 `oh-my-openagent.json` 中配置 Hephaestus：

```json
{
  "agents": {
    "hephaestus": {
      "model": "openai/gpt-5.6-sol",
      "variant": "medium"
    }
  }
}
```

### 8.2 模型回退链

```
主模型: GPT-5.6 Sol (medium effort) via OpenAI 或 Vercel
    ↓
回退: GPT-5.5 (medium effort) via OpenAI / GitHub Copilot / OpenCode / Vercel
    ↓
其他支持: GPT-5.4 (XML-tagged prompts), GPT-5.3 Codex variants
```

### 8.3 权限配置

```typescript
permission: {
  question: "allow",        // 允许提问
  call_omo_agent: "deny",  // 禁止调用其他 omo 智能体
  // ... 其他前沿工具模式权限
}
```

---

## 9. 与其他智能体的协作

### 9.1 协作关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                     智能体协作关系图                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   用户请求                                                      │
│      │                                                          │
│      ├──────────────────┬──────────────────┐                    │
│      ▼                  ▼                  ▼                    │
│ ┌─────────┐      ┌──────────┐      ┌──────────┐               │
│ │Sisyphus │      │Hephaestus│      │Prometheus│               │
│ │ + ulw   │      │ (直接)   │      │ /start-work│               │
│ └────┬────┘      └────┬─────┘      └────┬─────┘               │
│      │                │                 │                      │
│      │    ┌───────────┘                 │                      │
│      │    │                             │                      │
│      ▼    ▼                             ▼                      │
│ ┌─────────────────────────────────────────────────────────┐    │
│ │                    任务类型判断                          │    │
│ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │    │
│ │  │ 一般复杂任务 │  │ 深度架构工作 │  │  需要预先规划    │  │    │
│ │  │ Sisyphus处理│  │ Hephaestus  │  │ Prometheus规划   │  │    │
│ │  └─────────────┘  └─────────────┘  └─────────────────┘  │    │
│ └─────────────────────────────────────────────────────────┘    │
│      │                                                          │
│      ▼                                                          │
│ ┌─────────────────────────────────────────────────────────┐    │
│ │              子智能体并行调用 (Background)               │    │
│ │   ┌────────┐    ┌────────┐    ┌────────┐               │    │
│ │   │ Explore│    │Librarian│    │ Oracle │               │    │
│ │   │ 代码探索│    │ 文档检索│    │ 架构咨询│               │    │
│ │   │(read-only)│   │(read-only)│   │(read-only)│              │    │
│ │   └────────┘    └────────┘    └────────┘               │    │
│ │   ┌────────┐    ┌────────┐    ┌───────────┐           │    │
│ │   │ Sisyphus│    │ Category│    │  Manual   │           │    │
│ │   │ -Junior │    │ Agents  │    │  QA Gate  │           │    │
│ │   │ (执行)  │    │ (分类)  │    │ (验证)    │           │    │
│ │   └────────┘    └────────┘    └───────────┘           │    │
│ └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 何时使用 Hephaestus

**使用 Hephaestus**：
1. **深度架构推理需要** — "设计一个新的插件系统"
2. **复杂调试需要推理链** — "为什么这个竞态条件只在周二发生？"
3. **跨域知识综合** — "将我们的 Rust 核心与 TypeScript 前端集成"
4. **想要 GPT 原生自主推理** — 偏好 GPT-5.6 Sol

**使用 Sisyphus + `ulw`**：
1. **让智能体自己 figuring out** — "ulw fix the failing tests"
2. **复杂但范围明确的任务** — "ulw implement JWT authentication"
3. **懒得写详细需求** — 官方支持的使用场景
4. **利用现有计划** — 如果 Prometheus 计划存在

---

## 10. 附录

### 10.1 术语表

| 术语 | 定义 |
|------|------|
| **omo** | Oh-My-OpenAgent 的简称 |
| **GPT-5.6 Sol** | OpenAI GPT-5.6 的 "Sol" 变体，medium effort |
| **Hash-Anchored Edit** | LINE#ID 内容哈希验证的编辑方式 |
| **Manual QA Gate** | 通过实际使用验证工件的关卡 |
| **run_in_background** | 后台并行运行子智能体 |
| **continuation ID** | `ses_...` 格式的会话延续 ID |
| **background task ID** | `bg_...` 格式的后台任务 ID |

### 10.2 参考链接

- **项目主页**: https://github.com/code-yeongyu/oh-my-openagent
- **Hephaestus 目录**: `packages/omo-opencode/src/agents/hephaestus/`
- **编排指南**: `docs/guide/orchestration.md`
- **AGENTS.md**: `packages/omo-opencode/src/agents/hephaestus/AGENTS.md`

### 10.3 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.1 | 2026-07-23 | 校验 omo 源码后修正 11 处误差（见下方勘误表） |
| v1.0 | 2026-07-21 | 初始版本，基于 GitHub dev 分支 |

### 10.4 v1.1 勘误表

| # | 位置 | 原文 | 修正 | 依据 |
|---|------|------|------|------|
| 1 | §1 核心特征 | "四重验证" | "三重验证"（lsp_diagnostics + 构建/测试 + Manual QA Gate） | GPT-5.5/5.6 prompt 源码无"四重"表述 |
| 2 | §2.3 对比表 | Temperature 0.1 | 未显式设置（使用模型默认） | `createHephaestusAgent()` 无 temperature 字段，仅 `reasoningEffort: "medium"` |
| 3 | §3.1 代码结构 | 缺少 gpt.ts 注释 | gpt.ts 注释改为"含 GPT-5.3 Codex" | GPT-5.3 Codex 走 `gpt.ts` fallback 路径 |
| 4 | §3.3 模型路由 | "gpt-5.3-codex* → 基础 GPT 提示词" | 重排顺序，GPT-5.6 在前；GPT-5.3 Codex 走 fallback | `HephaestusPromptSource` 类型不含 `"gpt-5-3-codex"`，走 `"gpt"` default |
| 5 | §4.3 GPT-5.4 | "8 个 XML 标签块" | "9 个 XML 标签块"（增加 `<communication>`） | commit 3517017 重构后增加 `<communication>` 块 |
| 6 | §4.4 通用 GPT | "EXPLORE → PLAN → DECIDE → EXECUTE → VERIFY" | "EXPLORE → PLAN → IMPLEMENT → VERIFY → Manually QA" | 新版通用 GPT prompt 已统一为 5 步循环，移除 DECIDE |
| 7 | §5.1 流程图 | "意图分类 (Intent Classification)" 5 类 | "意图推断 (Intent Inference)" 映射表 | GPT-5.5/5.6 无 5 类分类，用意图映射表直接推断 |
| 8 | §5.1 流程图 | 独立"决策阶段 (Decision Phase)" | 委托决策融入 Operating Loop | GPT-5.5/5.6 无独立 Decision Phase |
| 9 | §5.1 流程图 | "Hash-Anchored Edits" | 移除 | Hash-Anchored Edits 是 omo 插件层功能，非 Hephaestus prompt 内容 |
| 10 | §7.3 委托提示 | "6 个必需部分" (TASK/EXPECTED OUTCOME/REQUIRED TOOLS/MUST DO/MUST NOT DO/CONTEXT) | GPT-5.5: 4 字段 (CONTEXT/GOAL/DOWNSTREAM/REQUEST)；GPT-5.6: 6 字段 (CONTEXT/GOAL/STOP WHEN/EVIDENCE/DOWNSTREAM/REQUEST) | 源码 `gpt-5-5.ts` 和 `gpt-5-6.ts` |
| 11 | §6.3 硬性不变量 | 6 条 | GPT-5.6: 4 条；GPT-5.5: 6 条（标注版本差异） | GPT-5.6 prompt 精简为 4 条核心不变量 |

---

> **文档生成说明**: 本文档基于 oh-my-openagent 项目的 GitHub 公开代码和文档整理，所有信息均来自官方仓库的 dev 分支。
