# DeepSeek Harness (dsh) Agent 架构学习笔记

> 通过学习 DeepSeek Harness（`dsh`）源码来理解 agent 架构设计与 TypeScript 工程实践。
> 这是一个**引导式学习产物**：以架构理解为主，按课程逐步深入核心源码。

- 源码位置：`/Users/eric/Project/tests/deepseek-harness/`
- 学习目标：① 理解 agent 架构的核心设计；② 在阅读 TypeScript 源码中吸收工程技巧
- 学习方式：引导式源码探险（agent-loop → agent → session → llm → tools）

---

## 0. 一句话总结

**dsh 的核心哲学：一切皆插件（everything is a plugin）+ 会话日志单一事实源（event-sourced session log）。**

几乎所有 agent harness 都要回答两个问题：
1. **如何组织系统**（体系结构）→ dsh 的答案是"Cordis 插件树"
2. **如何保存与重建上下文**（记忆模型）→ dsh 的答案是"追加式事件日志 + 从日志派生态化史"

理解了这两点，你就掌握了 dsh 的 90%。

---

## Lesson 1: Cordis 五概念（插件的基石）

> 源码：`vendor/cordis/src/`、`docs/cordis-primer.md`、`docs/cordis-tutorial/`

Cordis 是 dsh 底层的插件框架（vendored from [cordiverse/cordis](https://github.com/cordiverse/cordis)）。五个核心概念：

### 1.1 Plugin（插件）
一个实现 `Service` 的对象或函数。最常见的是函数形式：

```ts
import type { Context } from '@deepseek-ai/cordis'

export const name = 'hello'
export function apply(ctx: Context) {
  console.log('hello from my first plugin')
}
```

三种形态：
- **函数插件**（最常见）：`apply(ctx)`
- **对象插件**：带有 `apply` 方法的对象
- **类插件**：继承 `Service` 子类，注册一个命名服务（`super(ctx, 'name')`）

### 1.2 Context（上下文）— 一个服务仓库
核心文件：`deepseek-harness/vendor/cordis/src/context.ts`

- 每个插件通过 `apply(ctx)` 拿到 context。
- context 是一个 **Proxy**，属性读取走"服务解析器"。
- 服务通过稳定的 `ctx.<key>`（如 `ctx.tools`、`ctx.llm`、`ctx.sessions`）暴露；其他插件通过 key 找服务，而**不 import 具体实现**。
- `ctx.extend()` / `ctx.isolate()` / `ctx.intercept()` 创建作用域化的**子上下文**，不污染父级。

```ts
// 子上下文：prototypally 继承父级，own property 覆盖
const child = ctx.extend({ agent })
```

### 1.3 Service 依赖注入（`inject`）
插件通过 `inject` 声明它需要的服务，Cordis **等这些服务存在后才挂载该插件**。加载顺序由服务依赖驱动，而不是手动排列 `cordis.yml` 的行序。这解决了传统框架"先 load A 还是 B"的排序难题。

### 1.4 类型化事件（Typed Events）
服务通过 **TypeScript 声明合并（declaration merging）** 声明事件名，然后用五种分发模式之一派发：

| 模式 | await? | 顺序 | 返回值 | 典型用途 |
|---|---|---|---|---|
| `emit` | 否 | 注册序 | 无 | 观察、记录 |
| `waterfall` | 否 | 注册序 | 有 | 中间件 / 环绕逻辑 |
| `parallel` | 是 | 并行 | 无 | 并行副作用 |
| `serial` | 是 | 注册序 | 有 | 顺序决策 |
| `bail` | 同步 | 注册序 | 有 | 第一个 bail 停止 |

`waterfall` 是 dsh 里最重要的机制（见 Lesson 4）。它的核心语义：**监听器收到 `(...args, next)`，调用 `next()` 委托给链条下一个，不调用则短路**。

### 1.5 可逆效果（Reversible Effects）
所有注册（监听器、prompt 段、tool schema、adapter、provider）都通过 `ctx.effect()` 或 `ctx.on()` 安装，**插件卸载时会被自动撤销**。这让"热插拔"和"重载"可预测。

### 💡 TypeScript 技巧（Lesson 1 收获）
- **Context 接口通过 `declare module '@deepseek-ai/cordis'` 增强**——每个包在自己文件里往 `Context` 和 `Events` 接口里塞自己的服务/事件，实现了"每个插件扩展系统类型，而无需改框架源码"。这是 dsh 可插拔性的类型层根基。
- 这是 TS 的 `declare module` + 接口合并的经典应用。

---

## Lesson 2: 全局俯瞰（profile / bundle / 插件树）

> 源码：`deepseek-harness/docs/architecture.md`、`packages/boot/`

### 2.1 三个层次
- **Plugin（插件）**：单个贡献单元，见 Lesson 1。
- **Bundle（捆绑包）**：一组 Cordis 配置行 + 其挂载的代码的**分发格式**。bundle 里插入的每样东西，都能被更上层 patch。
- **Profile（档案）**：一个命名的组合，存放在 harness home（`~/.dsh/profiles/<name>/`）。它列出要叠加的 bundles、装载的外置插件、和用户的 `cordis.patch.yml`。`web` 和 `headless` 是两个内置模板。

你的本地 profile：`~/.dsh/profiles/web/package.json` 里 `dsh.profile.bundles` 是：
```json
"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]
```

### 2.2 启动时如何组装
启动时在一个**空 entry 列表**上按顺序应用各层：
`各 bundle → profile 的 cordis.patch.yml → home 级 → 任意 --patch 覆盖`

每个 patch 按**行 id** 定位并对整行 config 做替换或插入新行。**核心铁律：改你自己的 patch 层，别动 bundle 本体。**

查看你机器实际启动的插件树：
```sh
dsh --profile web --dump-config
```

### 2.3 六个核心包的"脊柱"
一个 turn 流过这六个包，构成 agent 的主循环（spine）：

| 包 | 拥有什么 | `ctx` key |
|---|---|---|
| `core/session` | 追加式 `SessionEvent` 日志 + 内存存储（**单一事实源**） | `ctx.sessions` |
| `core/system-prompt` | prompt 段 + tool schema 组装 | `ctx.systemPrompt` |
| `core/tools` | 作用域化 tool 注册表 + 守护执行管线 | `ctx.tools` |
| `core/agent` | `Agent` 接口、实时注册表、`agent/*` 事件 | `ctx.agents` |
| `core/agent-loop` | **具体循环实现**（默认 driver） | `ctx.agentLoop` |
| `core/scope` | 每-agent 作用域注册原语 | 库，无 key |

**关键设计**：`agent-loop` 是 `Agent` 公共契约的**唯一具体实现**，但扩展插件只依赖 `agent`（接口），**从不依赖 `agent-loop` 具体实现**。这让整个循环引擎都可替换。

### 💡 TypeScript 技巧（Lesson 2 收获）
依赖抽象包（`agent`）而非具体实现包（`agent-loop`）——这是"面向接口而非实现"的包级体现，让循环保持可替换性。

---

## Lesson 3: 核心循环（turn / step 生命周期）

> 源码：`deepseek-harness/packages/core/agent-loop/src/agent.ts`（核心，建议精读 `turn()` 与 `preStep()`）

### 3.1 两个时间单位
- **step（步）**：一次模型请求 + 它调用的工具。
- **turn（轮）**：零或多个 step。**turn 在第一个输入被 claim 之前打开**，在"不再欠任何东西"后关闭。一个 turn 可能包含多次 step（例如 agent 连续调工具、或收到 steer 后继续）。

### 3.2 三类 input 进入 Inbox
- **followup()** → 排队到 `next-turn` 并唤醒 driver（普通后续轮次）。
- **steer()** → 排队到 `next-step` 并唤醒（在最近的 step 边界被消费）。
- **inject()** → 排队到 `next-step` **不唤醒**（等待下个 wake 才被消费，注入式上下文）。

### 3.3 主循环驱动（`kick` → `while(turn)`）

```text
turn/start
  claim 下一步输入 + 排队消息
  组装 prompt 段 + tool schema
  -> agent/pre-step                # 可 reject 或改写
     step/start
     追加 user/message
     从日志派生 model history
     agent/request -> llm/stream -> assistant/chunk* -> assistant/message
     tool/call* -> tools/pre-execute -> tools/execute -> tools/post-execute -> tool/result*
     step/end
     若工具还欠下一步请求，或 input 到达 -> claim -> 下一步
  -> agent/turn-stopping
turn/end
```

关键 code 剪辑（`turn()` 里的状态机核心）：

```ts
while (true) {
  signal.throwIfAborted()
  const step = phase.step + 1
  const decision = await this.preStep(target, { turn, step })
  if (decision.kind === 'reject') return false          // 空轮/被拒 -> 关闭
  if (turnEnds && decision.messages.length === 0) break  // 无欠账 -> 结束
  this.session.append('step/start', { turn, step })
  // 追加 user/message -> 跑 step() -> step/end
  this.session.append('step/end', { turn, step })
  if (turnEnds && this.inbox.nextStep.length === 0) break
  target = 'next-step'
}
```

### 3.4 取消（Cancellation）
- 每个运行中的 driver 持有一个 `AbortController`。
- `cancel(cause)` 除非 `keepInbox` 否则清空 inbox 并 abort。abort 的 reason 是一个 TS 强类型的 `AgentCancelCause`：
  ```ts
  type AgentCancelCause =
    | { kind: 'user' } | { kind: 'parent' }
    | { kind: 'hook'; reason: string } | { kind: 'disposed' }
  ```
- **AbortSignal 传递全链路**：step → pre-step → 每个 tool execute，都观察 `exec.signal`。这是 agent 保持可中断性的核心模式。

### 💡 TypeScript 技巧（Lesson 3 收获）
- **Discriminated union（可判别联合）驱动状态机**：`Phase = {kind: 'idle'} | {kind: 'running', turn, step, ...} | ...`，每个分支带一个 `kind` tag。switch 它，TS 自动 narrow，拼错 tag 直接编译错误。这是 dsh（及整个 repo）的压倒性统一模式。
- **`satisfies` 约束**：用于让一个表/对象必须匹配某个 union 的所有成员，漏一个成员就是类型错误。
- **结构化错误**：`LlmError` 保留失败事实，其他异常用 `errorChain` 拍平成 `{ code: 'UNKNOWN', message }`——让跨进程/日志的错误可序列化。

---

## Lesson 4: 扩展点（`agent/*` 事件与 waterfall）

> 源码：`deepseek-harness/packages/core/agent/src/runtime-types.ts`、`deepseek-harness/docs/subsystems/core.md`

### 4.1 how to 扩展：选对事件域
设计文档给了一张"目标 → 机制"映射表，挑几条最常用的：

| 目标 | 机制 |
|---|---|
| 加一个模型 provider | register adapter 到 `ctx.llm` |
| 加一个 model-facing 能力 | register 到 `ctx.tools` |
| **拦截一个请求/tool/turn** | 用其 `agent/*` 或 `tools/*` 事件 |
| 加 model-facing 上下文 | `agent.inject()` |
| 加后台工作 | register `ctx.jobs` |
| **停掉一个 turn** | `agent/turn-stopping` |

### 4.2 关键 waterfall 事件
- **`agent/pre-step`**（waterfall）：接收 `<messages, turn, step, signal>`，返回 `PreStepDecision`。监听器可：
  - 调用 `next()` → 保留原 messages（默认进入 step）
  - 返回 `{ kind: 'reject' }` → 不开 step（空轮关闭）
  - 改写 `messages` → 用改写后的内容进入 step
- **`agent/request`**（waterfall）：可替换冻结的调用配置。
- **`agent/request-error`**（waterfall）：返回 `{ kind: 'retry' }` 即可接管失败重试。
- **`agent/turn-stopping`**（serial，无 next()）：在 turn 关闭前的最后机会。

### 4.3 工具执行管线（3 个 waterfall + 1 个 emit）
工具一次调用的完整流水：
```
model -> tool/call -> tools/pre-execute -> tools/execute -> tools/post-execute -> tool/result -> model
```
- `tools/pre-execute`：**放行/拒绝/询问**（approval policy 在此）。`next()` 委托=allow；`ask` 若无审批支持降级为 deny。
- `tools/execute`：**around-dispatch**，用于 timeout/retry/metrics 包装。
- `tools/post-execute`：接受/替换/增强/阻断一个已归一化的结果。
- `tools/result`（emit）：观察最终冻结结果，副作用监听。

### 💡 TypeScript 技巧（Lesson 4 收获）
**waterfall = 无状态中间件链**。每个 `agent/*` 或 `tools/*` waterfall 都是 "payload + next()" 的签名。这是 dsh 把"策略"和"能力"解耦的轴心：一个监听器做策略（approve/deny/rewrite），另一个做能力（真实的 execute），彼此不 import。三种角色构成一个 **capability seam**：
- **Service Definition**（接口）
- **Service Provider**（实现）
- **Consumer**（通常是 model-facing tool）

一个 provider 替换就能让整个产品换世界的依据就在这：例如文件系统和子进程 provider 共享一个执行世界，指向远程沙箱就能把 Bash/PTY/LSP 一起搬走。

---

## Lesson 5: 会话日志与事件溯源（Session Log）

> 源码：`deepseek-harness/packages/core/session/src/`

### 5.1 单一事实源（The Source of Truth）
- 一个 `Session` 是**追加式（append-only）`SessionEvent` 日志**。
- **model 看到的 LLM 历史不是单独存储的，而是从日志`派生`出来的**（`deriveMessages()`）。
- 每条 entry 带单调递增 `seq`、`time`、和以 `type` 判别的 `data` payload。

十二种事件变体（部分）：
`turn/start`, `turn/end`, `step/start`, `step/end`, `user/message`, `assistant/chunk`, `assistant/message`, `tool/call`, `tool/result`, `steering/message`, `todo/write`, `request/header`

### 5.2 朴素且深刻的规则：**Model-visible means logged**
> "Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it."

这是 dsh 最深刻的架构法之一：
- fork、resume、transcript、telemetry、persistence **全部从这同一个事件流派生**。
- 想要给 model 增加一种新的可见输入，就必须**新增一种 SessionEvent**，并从日志渲染——不能偷偷加内容进 prompt。
- 因为"该看到的东西必须被 log 记录"，所以**日志即真相**，模型看到什么永远可以被回放。

### 5.3 派生缓存（deriveMessages 的实现智慧）
```ts
deriveMessages(): Message[] {
  // 存在 surface generation 缓存：每个 surface node 只投影一次
  // 每个新调用只花 O(new nodes)，`replace` 压缩时重建
  // 返回 fresh 数组，但其中 Message 对象是 SHARED + deep-frozen
}
```
- **冻结（deep-freeze）** 返回的 Message，防止消费者意外污染后续派生态化史。
- **缓存 + generation 失效** 替代每次全量重建：增量投影。这是性能与不可变性的平衡。

### 💡 TypeScript 技巧（Lesson 5 收获）
- **Branded ID（品牌化 ID）**：`SessionId`、`CallId` 在类型层面是 `string & { readonly [BRAND]: B }`——结构是 string，但不可互换。一个 `SessionId` 不会被误传为 `CallId`。dsh 用独立的**类型纯**包 `dsh-brand` 承载它（无运行时代码），避免无关能力包之间的依赖。
- 品牌化是 TS 模拟"强类型名义类型"的经典手法。

---

## Lesson 6: 三个贯穿全 repo 的 TS 模式
（合并了前几课收获，单独成节便于复习）

### 6.1 `…Map → derived-union` 模式
几乎每个可扩展的 sum type 都长这样：
```ts
interface ThingMap {
  'a': { kind: 'a'; /* … */ }
  'b': { kind: 'b'; /* … */ }
}
type Thing = ThingMap[keyof ThingMap]      // 判别联合
// 插件无需改源码即可扩展：
declare module '@deepseek-ai/dsh-llm' {
  interface ThingMap { 'c': { kind: 'c' } }
}
```
六个 canonical maps：`ContentBlockMap`、`MessageSourceMap`、`FinishReasonMap`、`TurnTriggerMap`、`TurnEndReasonMap`、`SessionEventMap`。

### 6.2 面向 `switch` + tag narrow，而非 `if` 链
对 `StreamChunk` / `SessionEvent` 这类大联合，**用 switch 且每个 arm 都带 tag**。拼错 tag 直接编译失败。

### 6.3 包级依赖倒置与 seam
- 扩展依赖抽象包（`agent`），不依赖实现包（`agent-loop`）。
- capabilities 暴露为 service seam（定义/提供/消费三角色），一个 provider 可全产品替换。

---

## 学习路线建议

按"概念 → 结构 → 循环 → 扩展 → 溯源"的顺序：

| 步骤 | 主题 | 必读文件 | 对应 Lesson |
|---|---|---|---|
| 1 | Cordis 基础 | `docs/cordis-primer.md` + `vendor/cordis/src/{context,events,service}.ts` | L1 |
| 2 | 全局结构 | `docs/architecture.md` + `docs/subsystems/core.md` | L2 |
| 3 | 主循环 | `packages/core/agent-loop/src/agent.ts`（精读 `turn`/`preStep`） | L3 |
| 4 | 事件扩展 | `packages/core/agent/src/runtime-types.ts` | L4 |
| 5 | 事件溯源 | `packages/core/session/src/index.ts`（读 `deriveMessages`） | L5 |
| (进阶) | 动手插件 | `docs/cordis-tutorial/` 七章 | — |

> 进阶建议：读完上述后，用 `examples/agent-spine-demo` 或写一个最小的 `agent/pre-step` hook，把概念变成能跑的代码，理解会瞬间加深。

---

## 参考链接

- [架构文档](deepseek-harness/docs/architecture.md) 与 [Core 子系统](deepseek-harness/docs/subsystems/core.md)
- [Cordis Primer](deepseek-harness/docs/cordis-primer.md)
- events（vendor 分发实现）— `deepseek-harness/vendor/cordis/src/events.ts`
- 源码根：`/Users/eric/Project/tests/deepseek-harness/`

---

*本笔记用于学习 DeepSeek Harness 架构与 TypeScript 工程实践。*
