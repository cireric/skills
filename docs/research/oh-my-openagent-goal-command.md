# oh-my-openagent `/goal` 命令技术文档

> **文档范围**：聚焦 oh-my-openagent（原 oh-my-opencode）的 **Goal 子系统**及其 **`/goal` 斜杠命令**。Goal 于 2026-07-17 的 PR #6184 中取代了旧的 Ralph Loop 子系统（`/ralph-loop`、`/ulw-loop`、`/cancel-ralph`）。本文为 [`oh-my-openagent-architecture.md`](./oh-my-openagent-architecture.md) 第 1.4 节 "Goal 持有每会话目标" 条目与 [`oh-my-openagent-intent-gate.md`](./oh-my-openagent-intent-gate.md) 的深度展开。
>
> **信息来源**（均为第一方）：GitHub 仓库 `code-yeongyu/oh-my-openagent`（dev 分支）源码、官方文档 `docs/reference/features.md`、合并 PR [#6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)、官方 issue [#6470](https://github.com/code-yeongyu/oh-my-openagent/issues/6470)。
>
> **截止日期**：2026-08-14（dev 分支快照，commit 为 `2ea9a61d` 之后的最新状态）

---

## 目录

1. [项目概述](#1-项目概述)
2. [Goal 子系统是什么](#2-goal-子系统是什么)
3. [`/goal` 命令用法与语法](#3-goal-命令用法与语法)
4. [执行流程逐步拆解](#4-执行流程逐步拆解)
5. [与工具集成的其他机制](#5-与工具集成的其他机制)
6. [配置与定制](#6-配置与定制)
7. [适用场景](#7-适用场景)
8. [约束、坑与前置条件](#8-约束坑与前置条件)
9. [参考来源](#9-参考来源)

---

## 1. 项目概述

**oh-my-openagent（OmO，前身 oh-my-opencode）** 是面向 [OpenCode](https://opencode.ai) 的多模型 Agent 编排框架（multi-model agent orchestration harness），目标是"把单个 AI agent 转化为真正能交付代码的协作开发团队"。仓库位于 [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)，License 为 SUL-1.0，运行时为 Bun + TypeScript（详见 [oh-my-openagent-architecture.md](./oh-my-openagent-architecture.md)）。

产品分为两个版本（见 [README](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/README.md)）：

- **Ultimate Edition（omo for OpenCode）**：完整功能，11 个 Agent、54+ 生命周期 hook、全部斜杠命令、Team Mode 等；`/goal` 属于此版本。
- **Light Edition（omo for Codex CLI，包名 `lazycodex-ai`）**：可移植组件（rules、comment-checker、git-bash、lsp、ultrawork、ulw-loop 等），**没有斜杠命令体系**，因此没有 `/goal` 命令面（官方文档明确："All built-in slash commands are Ultimate-only — Codex CLI does not have a slash-command surface" 见 [官方站 docs](https://ohmyopenagent.com/docs)）。

README 的特性表中 Goal 条目（[README](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/README.md)）：

> 🔁 **Goal / `/goal`** | Ultimate | Persistent per-session objective. Re-injects a continuation prompt on every idle until a completion audit says it's done.
> （持久化的每会话目标。每次 idle 时重新注入 continuation prompt，直到完成审计确认工作已做完。）

---

## 2. Goal 子系统是什么

### 2.1 定位

Goal 是 oh-my-openagent 的**纪律强制机制**之一（另两个是 Todo 强制器与 Comment checker）。官方 [overview 文档](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/guide/overview.md) 的描述：

> Goal holds a persistent per-session objective and re-injects a continuation prompt on every idle until a completion audit confirms the work is done. The system doesn't let the agent slack off.
> （Goal 持有持久化的每会话目标，每次 idle 时重新注入 continuation prompt，直到完成审计确认工作已做完。系统不让 agent 偷懒。）

### 2.2 历史：取代 Ralph Loop

Goal 子系统由 PR [#6184 "feat(goal): replace Ralph Loop with per-session Goal subsystem"](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)（2026-07-17 合并，merge commit `746ef63`）引入，取代旧的 **Ralph Loop** 用户侧子系统：

- 旧命令 `/ralph-loop`、`/ulw-loop`、`/cancel-ralph` 及其模板被移除（[PR #6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)、[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) 中 `/ulw-loop` 一节："The `/ulw-loop` slash command has been removed; continuous goal pursuit is now handled by `/goal`"）。
- 旧 Ralph Loop 的核心行为（自我参考的持续执行循环、检测 `<promise>DONE</promise>` 判断完成、自动续跑）被 Goal 的"完成审计（completion audit）"机制取代：新系统要求 agent **通过基于实际证据的审计**后才调用 `update_goal({status:"complete"})`，而不是靠一句完成承诺（见下文 §4.3 与 [prompt.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/prompt.ts)）。

### 2.3 架构落点

Goal 子系统位于适配器包 `packages/omo-opencode` 的 hook 模块 `src/hooks/goal/`（[源码目录](https://github.com/code-yeongyu/oh-my-openagent/tree/dev/packages/omo-opencode/src/hooks/goal)），包含：

| 文件 | 职责 |
|------|------|
| `types.ts` | Goal 领域类型与 Zod schema（`Goal`、`GoalStatus`、`GoalFile`、工具快照 schema） |
| `store.ts` | 基于文件的持久化（读/写/创建/更新/清除，原子写） |
| `controller.ts` | 状态控制器：set/get/pause/resume/clear/markComplete/accountUsage + TUI 镜像写入 |
| `validation.ts` | 目标文本校验（非空、≤2000 字符） |
| `prompt.ts` | continuation prompt 与 resume prompt 构建器 |
| `command-arguments.ts` | `/goal` 参数解析器 |
| `tools.ts` | 模型工具 `create_goal` / `update_goal` / `get_goal` |
| `index.ts` | Goal hook：`session.idle` 续跑分发与 `session.deleted` 清理 |

另有 Pi harness 适配器包 `packages/pi-goal`（Pi 是另一个 harness，见 [pi-goal/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/AGENTS.md)，该包是独立 vendored 的 Pi 扩展，不在 OpenCode/Codex 主流程中）。

---

## 3. `/goal` 命令用法与语法

### 3.1 官方用法（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) §/goal）

```
/goal "Build a REST API with authentication"
/goal                    # show the current goal
/goal pause              # stop idle continuations
/goal resume             # resume a paused goal
/goal clear              # clear the current goal
```

### 3.2 参数解析规则（[command-arguments.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/command-arguments.ts)）

`/goal` 无"子命令名"概念——**任何非关键字文本都被当作新的目标文本（setObjective）**。解析逻辑：

1. 参数为空（或纯空白）→ `show`（展示当前 goal，无副作用）
2. `pause` → `setStatus(paused)`（停止 idle 续跑，不删除 goal）
3. `resume` → `setStatus(active)`（恢复续跑）
4. `clear` → `clear`（删除当前 goal）
5. 其他任何文本 → `setObjective(objective)`（**设置/替换**当前 goal 的目标文本）

对应测试（[command-arguments.test.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/command-arguments.test.ts)）验证：空输入显示当前 goal、`pause` 暂停、空白输入显示、任意文本作为目标。Pi 版解析器行为一致（[pi-goal/src/goal/command.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/src/goal/command.ts)），且 Pi 版测试特别注明 *"does not require or special-case a set subcommand"*——即 `set up the release` 会被当作目标文本而不是 set 命令（[pi-goal/test/command.test.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/test/command.test.ts)）。

### 3.3 内置命令注册（[commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/commands.ts)）

`/goal` 注册为内置命令：

```ts
goal: {
  description: "(builtin) Set, show, pause, resume, or clear the active thread goal",
  template: `${GOAL_TEMPLATE}\n\n$ARGUMENTS`,
  argumentHint: "<objective> | pause | resume | clear",
},
```

命令模板（[templates/goal.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/templates/goal.ts)）向 agent 说明 Goal 的工作方式：目标在当前线程/session 持续有效、idle 时系统自动注入续跑 prompt、agent 可在审计通过后调用 `update_goal({ status: "complete" })`、可用 `/goal pause|resume|clear` 控制。

**重要**：`/goal` 命令本身不通过 `goal.enabled` 门控（它始终注册，受 `disabled_commands` 控制），**门控的是三个模型工具**（`create_goal`/`update_goal`/`get_goal`，仅在 `goal.enabled: true` 时注册，见 [docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) 与 PR [#6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)）。命令与 hook 是否启用由 `disabled_commands` / `disabled_hooks` 数组控制（`goal` 是合法值，见 [docs/reference/configuration.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/configuration.md)）。

---

## 4. 执行流程逐步拆解

### 4.1 双入口拦截

`/goal` 在插件层面被两条路径拦截（PR [#6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184) "Added `/goal` interception in `chat.message` and `command.execute.before`"）：

1. **`command.execute.before`**（[command-execute-before.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/command-execute-before.ts)）：命令归一化后若为 `goal`，解析参数并调用对应 controller 操作（setGoal / pauseGoal / resumeGoal / clearGoal；`show` 无副作用）。同处理器中 `stop-continuation` 命令会调用 `stopContinuation` 清空目标（见 §5.3）。
2. **`chat.message`**（[loop-commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/chat-message/loop-commands.ts) 的 `handleGoalMessage`）：当消息文本以 `/goal` 开头（且非原生 goal 命令路径、不包含 auto-slash-command 标签）时，同样解析并执行。该路径还承载 **`default_mode.goal` 自动启动**：首条消息且 `default_mode.goal: true` 时，若解析结果为 show 且消息非空，自动把整条消息设为 goal（"Default goal auto-started"）。

另外 `tool.execute.before`（[tool-execute-before.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/tool-execute-before.ts)）保留了对模型调用的 `ralph-loop`/`ulw-loop` 风格工具参数的兼容解析（`getLoopCommandArguments`），当模型以带参方式调用此类工具时把参数路由到 `hooks.goal.setGoal(...)`（兼容旧循环工作流的调用形态）。

### 4.2 持久化与 TUI 镜像

- **主存储**：`.omo/goal/<sessionID>.json`（sessionID 经 `encodeURIComponent` 转义），JSON 结构为 `{ version: 1, goal: Goal | null }`；写盘采用"临时文件 + rename"的原子写（[store.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/store.ts)）。
- **TUI 镜像**：每次状态变更同时写入 `.omo/ulw-loop/<sessionID>/goals.json`（`TuiLoopSnapshot` 结构：`version`、`activeGoalId`、`goals[]`），供 TUI 显示（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)）。
- **Goal 数据模型**（[types.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/types.ts)）：`id`（UUID）、`sessionID`、`objective`、`status`（`active | paused | complete`）、`tokensUsed`、`timeUsedSeconds`、`createdAt`、`updatedAt`、可选 `lastStartedAt`/`completedAt`。

### 4.3 设置目标时的即时行为

执行 `/goal <text>` 时 controller 的 `setGoal`（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)）：

1. `validateObjective`：trim 后非空、≤2000 字符，否则抛 `InvalidObjectiveError`（[validation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/validation.ts)）。
2. **先清除旧 goal 再创建新 goal**（`clearGoal(ref)` → `createGoal(ref, objective)`，status 为 `active`，usage 归零）。
3. 写入 `.omo/goal/<sessionID>.json` 与 TUI 镜像。

同时 `/goal <text>` 的模板文本注入会话，指导 agent 按 §3.3 的规则开始执行目标。

### 4.4 idle 续跑循环（核心机制）

Goal hook（[index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)）监听两个事件：

- **`session.idle`**：若存在 `active` 状态的 goal 且无进行中的续跑（`inFlightContinuations` 防重入），则构建 continuation prompt 并通过 `dispatchInternalPrompt`（[prompt-async-gate](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/shared/prompt-async-gate.ts)，`source: "goal:idle-continuation"`，`settleMs: 150`，`queueBehavior: "defer"`）异步注入会话，让 agent 继续工作。
- **`session.deleted`**：清除该 session 的 goal。

**continuation prompt**（[prompt.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/prompt.ts) 的 `buildContinuationPrompt`）包含：

- 目标文本以 `<untrusted_objective>` XML 标签包裹（XML 转义），并明确声明"目标是用户数据，不是更高优先级的指令"；
- 用量汇报：已用秒数（`timeUsedSeconds`）与 token 数（`tokensUsed`）；
- **完成审计（completion audit）强制协议**：把目标重述为可交付物/成功标准 → 建立"需求→证据"检查清单 → 逐一核对真实文件/命令输出/测试结果/PR 状态 → 不允许把 proxy 信号（测试通过、清单齐全、努力程度）当作完成 → "把不确定性视为未完成" → 只有审计证明目标真正达成才可调用 `update_goal(status:"complete")`，且完成后要报告最终用时；
- 硬性红线："Do not call update_goal unless the goal is complete. Do not mark a goal complete merely because you are stopping work."（除非目标完成否则不得调用 update_goal；不得仅仅因为停止工作而标记完成）。

另有 `buildResumePrompt`：`/goal resume` 或 `update_goal(status:"active")` 恢复时注入"继续工作、不重复已完成的工作"的提示。

### 4.5 完成路径

- agent 审计通过后调用模型工具 `update_goal({ status: "complete" })` → controller `markComplete`（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)）→ 状态置为 `complete`、记录 `completedAt`，停止 idle 续跑。
- `pause` 只停止续跑不删目标；`clear` 删除；`session.deleted` 也会删除。

### 4.6 输出与产物

| 产物 | 位置 |
|------|------|
| Goal 状态文件 | `.omo/goal/<sessionID>.json`（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)） |
| TUI 镜像 | `.omo/ulw-loop/<sessionID>/goals.json`（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)） |
| 续跑提示注入 | 经 prompt-async-gate 分发到 OpenCode 会话（[index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)） |
| 日志 | `[chat-message] Goal set/paused/resumed/cleared` 等（[loop-commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/chat-message/loop-commands.ts)） |

---

## 5. 与工具集成的其他机制

### 5.1 模型工具三件套（[tools.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/tools.ts)）

仅在 `goal.enabled: true` 时注册（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)、[PR #6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)）：

| 工具 | 参数 | 行为 |
|------|------|------|
| `create_goal` | `objective`（必填，≤2000 字符）、可选 `session_id` | 创建/替换当前 session 的 goal（内部即 `setGoal`） |
| `update_goal` | 可选 `status`（`active`/`paused`/`complete`）、`objective`、`session_id` | 暂停/恢复/标记完成/改目标；`complete` → `markComplete` |
| `get_goal` | 可选 `session_id` | 返回目标、状态与用量快照（无 goal 返回 `null`） |

工具返回统一 JSON：`{ "goal": GoalToolSnapshot | null }`（[types.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/types.ts)）。

### 5.2 与其他斜杠命令的关系

| 命令 | 与 Goal 的关系 |
|------|----------------|
| `/stop-continuation` | **清除当前 session 的 Goal**（同时停 todo continuation、清 boulder state，见 [templates/stop-continuation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/templates/stop-continuation.ts) 与 [command-execute-before.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/command-execute-before.ts)） |
| `/start-work` | Prometheus 规划后启动 Atlas 执行（与 Goal 是两条独立的"持续推进"路径；Goal 不依赖计划文件） |
| `/handoff` | 其 `argumentHint` 为 `[goal]`——续接会话时可带目标文本（[commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/commands.ts)） |
| `/ulw-loop` | **已移除**，持续目标追求改由 `/goal` 承担；`omo-agent-toolkit ulw-loop` CLI 子命令保留为 Codex LazyCodex 的 passthrough（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)） |

### 5.3 与 IntentGate / 编排体系的关系

- `/goal` 不经过 IntentGate 路由：它是**用户/模型直接设置持久目标的机制**，而 IntentGate 是 Sisyphus 主编排器（[intent-gate 文档](./oh-my-openagent-intent-gate.md)）Phase 0 的提示词级意图分类，两者正交——Goal 设定的是"长期目标状态"，IntentGate 分类的是"单条消息的真实意图"。
- 与 todo 强制器（Todo Continuation Enforcer）同属"纪律强制"层：todo 强制器针对**进行中的 todo 清单**续跑，Goal 针对**会话级目标**在 idle 时续跑；`/stop-continuation` 同时关闭两者与 boulder（[templates/stop-continuation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/templates/stop-continuation.ts)）。
- hook 表中登记为（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) hooks 表）：**goal** | Event | "Re-injects a goal continuation prompt on session.idle while a goal is active; clears the goal on session.deleted."；`goal` 是 `disabled_hooks` 的合法值（[docs/reference/configuration.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/configuration.md)）。
- 与 `default_mode.ultrawork` 的关系：Goal hook 的 `GoalHookOptions` 带 `ultrawork?: boolean` 选项，PR 摘要说明"ultrawork-aware prompts"——当 `default_mode.ultrawork` 同时开启时，goal 续跑提示使用 ultrawork 模式（[PR #6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)、[index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)）。

### 5.4 Pi harness 变体（[pi-goal](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/AGENTS.md)）

`packages/pi-goal` 是 vendored 自独立仓库 `code-yeongyu/pi-goal` 的 Pi 扩展（`@oh-my-opencode/pi-goal`，独立发布面，不接入 OpenCode/Codex/senpi 主流程）。它注册同样的 `create_goal`/`update_goal`/`get_goal` 工具与 `/goal` 命令，通过隐藏的 `pi-goal-continuation` 自定义消息续跑，并渲染 Codex 风格的 TUI footer。**其工具契约对齐 OpenAI Codex 的 `codex-rs/ext/goal`**：`update_goal` 额外接受 `blocked`（模型可设置的、可恢复的非终态）、`create_goal` 仅当现有 goal 为 `complete` 时才能替换（否则报 "unfinished goal"）、goal 状态枚举为 `active|paused|blocked|budgetLimited|complete`（比 OpenCode 版多 `blocked`/`budgetLimited`）。这是"goal 工具契约来自 Codex"的直接证据。

---

## 6. 配置与定制

### 6.1 `goal` 配置块（[config/schema/goal.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/goal.ts)、[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)）

```jsonc
{
  "goal": {
    "enabled": true,
    "auto_start": false,
    "default_max_iterations": 100
  }
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | boolean | `false` | 门控 Goal 子系统及其工具（`create_goal`/`update_goal`/`get_goal`） |
| `auto_start` | boolean | `false` | 配合 `default_mode.goal`：从首条 main-session 消息自动创建 goal |
| `default_max_iterations` | number (1–1000) | `100` | 续跑迭代上限，"preserved for Ralph Loop behavioral parity"（为与 Ralph Loop 行为对齐而保留） |

根 schema 中登记为 `goal: GoalConfigSchema.optional()`，另有 `ralph_loop: z.record(...)` 兼容 shim（[oh-my-opencode-config.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/oh-my-opencode-config.ts)）。

### 6.2 `default_mode.goal`（[config/schema/default-mode.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/default-mode.ts)）

```jsonc
{ "default_mode": { "goal": true } }
```

- 默认 `false`；开启后在 main session 首条消息自动创建 goal，无需 `/goal` 命令；
- 若同时开启 `default_mode.ultrawork`，goal 续跑提示使用 ultrawork 模式；
- 旧键 `default_mode.ralph_loop` 已更名为 `default_mode.goal`（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)）。

### 6.3 从 `ralph_loop` 自动迁移（[validate.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/validate.ts) 的 `migrateRalphLoopConfig`）

加载配置时，旧 `ralph_loop` 键的 `enabled` / `default_max_iterations` 会迁移到 `goal` 并打印弃用警告；**显式 `goal` 配置优先于迁移值**。迁移测试见 [validate-pipeline.test.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/validate-pipeline.test.ts)（如 `ralph_loop: { enabled: true, default_max_iterations: 50 }` → `goal: { enabled: true, auto_start: false, default_max_iterations: 50 }`）。PR #6184 声明 `ralph_loop` 键将被解析但忽略，未来版本移除。

### 6.4 其他定制点

- `disabled_hooks: ["goal"]` 关闭 goal hook（[docs/reference/configuration.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/configuration.md) 的可用 hooks 列表含 `goal`）。
- `disabled_commands: ["goal"]` 关闭 `/goal` 命令（可用命令枚举含 `goal`，同上）。
- 工具级定制：`create_goal`/`update_goal`/`get_goal` 是普通注册工具，可走 `disabled_tools` 机制（未在文档单独列出，属通用工具管理；此项未逐一核实）。
- 配置文件路径与合并规则见 [oh-my-openagent-architecture.md](./oh-my-openagent-architecture.md) §7.1。

---

## 7. 适用场景

官方文档（[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)）给出 `/goal` 的唯一完整示例是：

```
/goal "Build a REST API with authentication"
```

适用特征（据 [features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)、[README](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/README.md) 与 [PR #6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184) 归纳）：

- **跨多轮、需要持续追求的任务**：目标跨 turn 保持有效，agent 空闲时被自动拉回继续工作（"Set a persistent thread objective the agent pursues across turns until paused, cleared, or completed"）。
- **无人值守/长跑任务**：`default_mode.goal` 自动启动 + idle 续跑，配合完成审计，面向"设置好就跑、醒来验收"的使用方式（README 中用户证言提及 ralph loop 时代的整夜跑任务）。
- **需要"目标级"纪律而非单次指令的任务**：Goal 是纪律强制三件套之一（[overview.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/guide/overview.md)）。
- **替换旧 `/ulw-loop` 的连续追求工作流**：旧 `/ulw-loop`（带 ultrawork 模式持续到完成）由 `/goal` 承担（[features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) `/ulw-loop` 一节）。
- 模型中 `deep` category 的定位同样强调 "ONE goal + ONE deliverable per call"（[features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md) §Category），与 Goal 的"单目标"语义呼应。

不适合/不推荐的情形（官方未给出明确排除清单，以下据机制推导并标注）：需要独立审阅人签收的交付（见 §8 issue #6470）、目标文本超过 2000 字符（会被 `InvalidObjectiveError` 拒绝）。

---

## 8. 约束、坑与前置条件

1. **`goal.enabled` 默认关闭**：不开则三个模型工具不注册、hook 不工作；`/goal` 命令虽始终可用，但没有工具与 hook 支撑就没有续跑行为（[config/schema/goal.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/goal.ts)、[features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)）。
2. **无独立审阅签收门（已知缺口，issue [#6470](https://github.com/code-yeongyu/oh-my-openagent/issues/6470)，open 状态）**：`/goal` 允许 agent **自我声明** `update_goal({status:"complete"})`，无独立验证；旧 `/ulw-loop` 要求独立审阅者签字后才结束循环。issue 作者指出这对无人值守长跑是回归（"done" 变成 agent 自说自话），提出恢复带独立审阅门的 `/ulw-loop`。维护者 triage 意见：senpi 侧已有 ulw-loop 工作流，是否移植审阅门到 OpenCode `/goal` 是 owner 决策（2026-08-06）。
3. **目标文本长度上限 2000 字符**，超出抛 `InvalidObjectiveError`（[validation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/validation.ts)）。
4. **目标即指令的注入风险**：continuation prompt 把目标包在 `<untrusted_objective>` 中并声明"非更高优先级指令"，但 prompt 层约束不是硬隔离（[prompt.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/prompt.ts)）。
5. **重名/覆盖语义**：`/goal <text>` 与 `create_goal` 会**直接替换**当前 goal（OpenCode 版 `setGoal` 先 clear 再 create；[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)）。Pi/Codex 契约则相反：`create_goal` 仅当现有 goal 为 `complete` 时才替换，否则报 "unfinished goal"（[pi-goal/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/AGENTS.md)）——**两套语义不同，跨 harness 使用时需注意**。
6. **续跑注入竞态保护**：`inFlightContinuations` 防重入 + `dispatchInternalPrompt` 的 reserve/settle 机制（失败时仅告警，可能已被其他路由接受）（[index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)）。
7. **续跑失败容忍**：若 `dispatchInternalPrompt` 返回 failed 且未被接受，仅 `console.warn`，不重试（同上）。
8. **Ultimate-only**：Light Edition（Codex CLI）没有斜杠命令体系，无 `/goal` 命令面（[ohmyopenagent.com/docs](https://ohmyopenagent.com/docs)）。
9. **前置条件**：`/goal` 依赖 OpenCode 会话体系（sessionID）与 `.omo/` 目录写权限；续跑依赖 OpenCode 的 `session.idle` 事件与 prompt-async-gate 注入管线（[index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)）。

### 未能从第一方来源确认的点（显式标注）

- **`tokensUsed`/`timeUsedSeconds` 的实际记账调用点**：官方文档称续跑提示"tracks `tokensUsed` and `timeUsedSeconds`"（[features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)），controller 提供 `accountUsage` 方法（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)），但我在 dev 分支快照的 omo-opencode 插件装配代码中**未能定位到 `accountUsage` 的实际调用方**（github 代码搜索仅命中 controller 本身及其测试），即"谁在何时把 token/time 增量写回 goal 文件"未能在第一方源码中确认；`default_max_iterations` 的具体执行点同理（配置与文档存在，但 goal 模块源码中未见迭代计数逻辑，可能仍在遗留 ralph-loop 路径，未核实）。
- **TUI 侧栏的具体渲染实现**：文档称 "shown in the TUI"（[features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)），已确认有 `.omo/ulw-loop/<sessionID>/goals.json` 镜像文件（[controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)），但 OpenCode 侧消费该文件的 UI 组件未逐一核实（pi-goal 侧有 `src/goal/ui.ts` footer 组件，[pi-goal/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/AGENTS.md)）。

---

## 9. 参考来源

1. **官方文档 — /goal 完整说明**：[docs/reference/features.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)（dev 分支，§Commands / §/goal / §hooks 表 / §/ulw-loop）
2. **合并 PR — Goal 取代 Ralph Loop**：[PR #6184](https://github.com/code-yeongyu/oh-my-openagent/pull/6184)（feat(goal): replace Ralph Loop with per-session Goal subsystem，merge commit `746ef634`）
3. **基础提交**：[commit f23c9ef](https://github.com/code-yeongyu/oh-my-openagent/commit/f23c9efdcb952a52d69b1fc28c014dcf7bacf7ff)（goal foundation：types/persistence/prompts/parser/config//goal 命令）
4. **源码（dev 分支 raw，`packages/omo-opencode/src/`）**：
   - [hooks/goal/command-arguments.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/command-arguments.ts)（参数解析）
   - [hooks/goal/types.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/types.ts)（领域类型）
   - [hooks/goal/store.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/store.ts)（持久化）
   - [hooks/goal/controller.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/controller.ts)（状态控制器 + TUI 镜像）
   - [hooks/goal/prompt.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/prompt.ts)（续跑/恢复 prompt）
   - [hooks/goal/validation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/validation.ts)（目标校验）
   - [hooks/goal/tools.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/tools.ts)（模型工具三件套）
   - [hooks/goal/index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/hooks/goal/index.ts)（Goal hook：idle 续跑 + deleted 清理）
   - [config/schema/goal.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/goal.ts)（goal 配置 schema）
   - [config/schema/default-mode.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/default-mode.ts)（default_mode.goal）
   - [config/schema/oh-my-opencode-config.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/schema/oh-my-opencode-config.ts)（根 schema 中 goal/ralph_loop 键）
   - [config/validate.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/validate.ts)（ralph_loop → goal 迁移）
   - [config/validate-pipeline.test.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/config/validate-pipeline.test.ts)（迁移测试）
   - [features/builtin-commands/commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/commands.ts)（命令注册）
   - [features/builtin-commands/templates/goal.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/templates/goal.ts)（/goal 模板）
   - [features/builtin-commands/templates/stop-continuation.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/features/builtin-commands/templates/stop-continuation.ts)（/stop-continuation 清 goal）
   - [plugin/chat-message/loop-commands.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/chat-message/loop-commands.ts)（chat.message 拦截 + 自动启动）
   - [plugin/command-execute-before.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/command-execute-before.ts)（command.execute.before 拦截）
   - [plugin/tool-execute-before.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/omo-opencode/src/plugin/tool-execute-before.ts)（工具执行前拦截/旧循环兼容）
5. **Pi 适配器**：[packages/pi-goal/AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/AGENTS.md)、[pi-goal/src/index.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/src/index.ts)、[pi-goal/src/goal/command.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/src/goal/command.ts)、[pi-goal/test/command.test.ts](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/packages/pi-goal/test/command.test.ts)
6. **官方 issue — 已知缺口**：[issue #6470](https://github.com/code-yeongyu/oh-my-openagent/issues/6470)（Bring back /ulw-loop — /goal lets the agent mark itself done with no independent review）
7. **README**：[README.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/README.md)（Goal / `/goal` 特性行）
8. **配置参考**：[docs/reference/configuration.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/configuration.md)（disabled_hooks/disabled_commands 枚举）
9. **官方站**：[ohmyopenagent.com/docs](https://ohmyopenagent.com/docs)（斜杠命令 Ultimate-only 说明）
10. **配套文档**：[`./oh-my-openagent-architecture.md`](./oh-my-openagent-architecture.md)、[`./oh-my-openagent-intent-gate.md`](./oh-my-openagent-intent-gate.md)
