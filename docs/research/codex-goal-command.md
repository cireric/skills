# Codex /goal 命令调研

> **调研日期**：2026-08-14
> **调研对象**：OpenAI Codex CLI（openai/codex，Rust 版 `codex-rs`）的 `/goal` slash command
> **当前版本基线**：0.128.0 引入；截至调研日最新稳定版 0.147.0（2026-08-07 发布）；本文以 `main` 分支源码 + 官方文档为准
> **来源策略**：以 OpenAI 官方文档、官方 release notes、官方 GitHub 源码为 Tier 1 依据；社区文章一律标注 Tier 3

## TL;DR（结论摘要）

`/goal` 是 Codex CLI（v0.128.0+）的 slash command，用于给当前 thread 挂一个**持久化的目标（objective）**，让 Codex 在每轮 turn 结束后自动评估目标是否达成，未达成且预算未耗尽则**自动继续执行**，直到完成、被用户暂停/清除、被预算截断或遇到无法解决的阻塞。官方定位：把"prompt → diff → 等用户"的单次交互，变成"work → check → continue or complete"的持续循环（[OpenAI Cookbook: Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)）。

核心事实速查：

| 维度 | 结论 | 来源 |
|---|---|---|
| 本质 | 持久化的 thread 级状态（thread-scoped state），**不是**全局记忆，**不是** AGENTS.md 项目指令 | [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) |
| 命令面 | `/goal <objective>` 设置、`/goal` 查看、`/goal edit` 修订、`/goal pause`、`/goal resume`、`/goal clear` | [官方 slash-commands 文档](https://developers.openai.com/codex/cli/slash-commands) |
| 引入版本 | 0.128.0（2026-04-30，5 个 PR #18073–#18077 + #20082，作者 Eric Traut） | [0.128.0 release notes](https://github.com/openai/codex/releases/tag/rust-v0.128.0) |
| 启用方式 | 0.128 需 `[features] goals = true`；0.129 起标记 experimental 可用 `/experimental` 开关；**0.133.0 起默认启用**；当前 `main` 中该 feature 为 Stable、default_enabled=true | [0.129.0](https://github.com/openai/codex/releases/tag/rust-v0.129.0)、[0.133.0](https://github.com/openai/codex/releases/tag/rust-v0.133.0)、[codex-rs/features/src/lib.rs](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs) |
| 存储位置 | `$CODEX_HOME/goals_1.sqlite`（专用 SQLite 库，`thread_goals` 表，2026-05 起从主 state db 迁出） | [codex-rs/state/src/sqlite.rs](https://github.com/openai/codex/blob/main/codex-rs/state/src/sqlite.rs)、[codex-rs/state/src/runtime.rs](https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime.rs) |
| 生命周期状态 | 协议/存储层：`active` / `paused` / `blocked` / `usage_limited` / `budget_limited` / `complete`；TUI 展示文案为 pursuing / paused / achieved / unmet / budget-limited | [codex-rs/protocol/src/protocol.rs](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs)、[issue #20536](https://github.com/openai/codex/issues/20536) |
| 模型工具 | `get_goal` / `create_goal` / `update_goal`（update 只能标记 complete/blocked，且 blocked 需同一阻塞连续 3 轮） | [codex-rs/ext/goal/src/spec.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/spec.rs) |
| objective 限制 | 非空、≤4000 字符；超长时官方建议写入文件并在 goal 里指向该文件（TUI 会自动物化为 `$CODEX_HOME/attachments/<uuid>/goal-objective.md`） | [slash-commands 文档](https://developers.openai.com/codex/cli/slash-commands)、[codex-rs/tui/src/goal_files.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/goal_files.rs) |
| 关键区分 | 交互式 TUI 命令；**exec 模式不支持**（ephemeral session 有专门报错）；与 `/plan`、`/resume`、`/fork`、`/compact` 各有交互 | 见"与其他命令的关系"节 |

---

## 1. `/goal` 是什么：定义与设计意图

### 1.1 官方定义

官方 slash-commands 文档把 `/goal` 列为一等内置命令，功能描述为："Set, edit, pause, resume, view, or clear a task goal. Give Codex a persistent target to track while a larger task runs."（[官方文档](https://developers.openai.com/codex/cli/slash-commands)）。

官方使用场景页（[Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals)）进一步定义：使用 `/goal` 时，Codex 不再在一轮普通 turn 后停下，而是"can work independently for multiple hours without needing your input"，并把它定性为"a background task you don't need to monitor"。

官方 Cookbook（2026-05-09，Raj Pathak & Stefano Fabbri 撰写，[Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)）给出了最完整的定义：

> "Goals are persistent objectives in Codex that keep a thread working toward a defined outcome across turns. A Goal gives Codex a completion condition: what should be true, how success should be checked, and what constraints must stay intact."
> "A Goal is not background autonomy without boundaries. It is a scoped, user-controlled completion contract."

### 1.2 与普通 prompt 的对比（设计意图）

官方 Cookbook 用两个公式概括设计意图：

| 模式 | 循环形态 | 说明 |
|---|---|---|
| 普通 prompt | ask → work → result → wait | 执行完当前指令就停，等用户下一句 |
| Goal | work → check → continue or complete | 每轮结束检查证据，未达成且预算内则自动续跑 |

来源：[OpenAI Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)

官方明确的目标用户场景是"next step depends on what Codex learns along the way"（下一步动作取决于本轮学到什么）的任务——这类任务"do not need a bigger prompt. They need a persistent objective."

### 1.3 设计边界（官方措辞）

官方对 Goal 的三个设计约束（均出自 [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)）：

1. **线程作用域**："Goals are implemented as persisted thread state, not as global memory and not as project-level instructions."——目标属于承载上下文的 thread，而非全局或项目级（这直接划清了与 AGENTS.md `/init` 机制的界限）。
2. **事件驱动续跑而非裸循环**："Codex checks for continuation only at safe boundaries: after a turn has finished, when no other work is pending, when no user input is queued, and when the thread is idle."；plan-only 工作不触发续跑；中断会暂停目标；续跑 turn 若无实际活动会被抑制（源码 `goals.rs` 模块注释亦有同款描述，[codex-rs/core/src/goals.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/goals.rs)）。
3. **完成必须基于证据审计**："A Goal should not be marked complete because the model believes it is probably done."——`update_goal` 的 complete 调用前必须对照文件、测试、日志、benchmark 输出等具体证据逐项核验（提示词模板 [continuation.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/continuation.md) 里有完整的 completion audit 指令）。

### 1.4 命名与社区背景

Codex 团队成员 Felipe Coury 在 0.128.0 发布当天把 `/goal` 称为 Codex 对社区"Ralph loop"（固定目标驱动 agent 持续自循环）的产品化实现——"keep a goal alive across turns. Don't stop until it's achieved."（转引自第三方文章 [AI Catchup](https://aicatchup.com/news/codex-cli-0-128-persisted-goal)，Tier 3；官方 release notes 本身只列功能清单未用此词，[0.128.0](https://github.com/openai/codex/releases/tag/rust-v0.128.0)）。

---

## 2. 使用场景

### 2.1 官方文档点名的场景

| 场景 | 官方出处 | 说明 |
|---|---|---|
| 代码迁移（migration） | [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals)、[Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) | 目标栈、对等性检查、约束都明确时，Codex 可自主跑完整个迁移 |
| 大型重构 | [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) | 每个 checkpoint 后跑测试 |
| 实验/游戏/原型 | [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) | "keep improving a working artifact"，可用 PLAN.md 指导第一版 |
| Prompt/benchmark 调优 | [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) | 有 eval 套件时循环"看失败→改 prompt→重跑 eval"直到分数达标或到达停止条件 |
| 性能优化（如 p95 延迟） | [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) | 官方示例：`/goal Reduce p95 checkout latency below 120 ms...` |
| flaky test 排查、bug 复现 | [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) | "bug hunts that require reproduction" |
| 研究型任务（产出证据化报告） | [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) | 官方示例："Produce the strongest evidence-backed reproduction of the paper..." |

### 2.2 适用判据

官方 [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) 页给出的选型原则：**"A good goal is bigger than one prompt but smaller than an open-ended backlog."**——应明确定义四件事：要达到什么、不应改什么、如何验证进展、何时停止；并明确反例："Avoid using a goal for a loose list of unrelated work."

官方 Cookbook 给出了官方认可的写作模板（六要素契约）：

```
/goal <desired end state> verified by <specific evidence> while preserving <constraints>.
Use <allowed inputs, tools, or boundaries>.
Between iterations, <how Codex should choose the next best action>.
If blocked or no valid paths remain, <what Codex should report and what would unlock progress>.
```

（[Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)，完整示例见第 3 节）

### 2.3 何时**不**用（官方 + 社区交叉）

- 官方：一次性的编辑、无法定义"完成"的任务、松散的无关工作清单不该用（[Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals)）。
- 社区（Tier 3）共识补充：单纯探索/头脑风暴、30 分钟内能做完的小事不值得付出续跑机制开销；目标必须"audit-ready"（有可验证停止条件），否则 agent 会"keep moving while still losing the actual job"（[LaoZhang AI 文章](https://blog.laozhang.ai/en/posts/codex-goal)、[J.D. Hodges](https://www.jdhodges.com/blog/codex-goal-feature-review/)）。

### 2.4 官方推荐的实施流程（6 步）

官方 [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) 页的"Set up the loop"：

1. 只定一个目标和一个停止条件；
2. 把要优先读的文件/文档/issue/日志/计划指给 Codex；
3. 定义能证明进展的命令或产物；
4. 要求以 checkpoint 方式工作并维护简短进度日志；
5. 运行中用 `/goal` 查看状态；
6. 完成、受阻或转向时 pause/resume/clear。

官方还建议：状态变模糊时"tighten the goal rather than adding more one-off instructions"（收紧目标而不是继续追加一次性指令）；并推荐让 Codex 自己起草 goal 再人工审查（"Help me turn this into a strong `/goal`: ..."）。

---

## 3. 使用方法

### 3.1 命令语法

官方 slash-commands 文档（[链接](https://developers.openai.com/codex/cli/slash-commands)）的 "Set or view a task goal with `/goal`" 一节：

| 命令 | 作用 | 官方原文 |
|---|---|---|
| `/goal <objective>` | 设置目标 | "Type `/goal ` to set the goal, for example `/goal Finish the migration and keep tests green`" |
| `/goal` | 查看当前目标 | "Type `/goal` to view the current goal" |
| `/goal edit` | 修订目标 | "Use `/goal edit` to revise the objective" |
| `/goal pause` | 暂停 | "Use ... `/goal pause` ... to pause" |
| `/goal resume` | 恢复 | "... `/goal resume` ..." |
| `/goal clear` | 清除 | "... or `/goal clear` to pause, resume, or remove it" |

官方 Cookbook 的生命周期速览（[Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)）：

```
/goal      	View the current Goal
/goal pause    Pause an active Goal
/goal resume   Resume a paused Goal
/goal clear    Remove the current Goal
```

约束（官方文档原文）："Goal objectives must be non-empty and at most 4,000 characters. For longer instructions, put the details in a file and point the goal at that file."（[slash-commands](https://developers.openai.com/codex/cli/slash-commands)）——4000 字符上限在源码里是常量 `MAX_THREAD_GOAL_OBJECTIVE_CHARS = 4_000`（[codex-rs/protocol/src/protocol.rs](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs)）。

### 3.2 启用步骤（版本相关）

| 版本 | 启用方式 |
|---|---|
| 0.128.0 | 默认**不启用**；手动在 `~/.codex/config.toml` 加 `[features] goals = true`，或 `codex features enable goals`（官方 [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) 页保留此说明；maintainer 在 [issue #20548](https://github.com/openai/codex/issues/20548) 确认 0.128 需手动加 flag） |
| 0.129.0 | 标记为 experimental，可用 `/experimental` 开关（[0.129.0 release notes](https://github.com/openai/codex/releases/tag/rust-v0.129.0)；maintainer 在 #20548 留言说明） |
| 0.133.0+ | **默认启用**："Goals are now enabled by default, backed by dedicated storage"（[0.133.0 release notes](https://github.com/openai/codex/releases/tag/rust-v0.133.0)） |
| 当前 main | feature stage 为 `Stable`，`default_enabled: true`，config key 为 `goals`（[codex-rs/features/src/lib.rs](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs)） |

### 3.3 官方示例

Cookbook 示例（弱 vs 强目标，[Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)）：

```
/goal Reduce p95 checkout latency below 120 ms without regressing correctness tests

/goal Reduce p95 checkout latency below 120 ms, verified by the checkout benchmark, while
keeping the correctness suite green. Use only the checkout service, benchmark fixtures, and
related tests. Between iterations, record what changed, what the benchmark showed, and the
next best experiment to try. If the benchmark cannot run or no valid paths remain, stop with
the attempted paths, the evidence gathered, the blocker, and the next input needed.
```

官方 [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) 页建议的进度报告格式：状态更新应点名"current checkpoint、what was verified、what remains、whether Codex is blocked"。

### 3.4 与其他命令/机制的关系

| 命令/机制 | 与 /goal 的关系 | 来源 |
|---|---|---|
| `/plan`（plan mode） | **不触发** goal 续跑：turn 进入 plan mode 时 runtime 清空当前 turn 的 goal 归属（`accounting.clear_current_turn_goal()`）；0.138 又专门修了 "idle auto-turns stay out of Plan mode" | [codex-rs/ext/goal/src/extension.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/extension.rs)、[0.138.0](https://github.com/openai/codex/releases/tag/rust-v0.138.0) |
| `/resume`（session 续接） | thread resume 时恢复 goal 运行时状态（`on_thread_resume → restore_after_resume`）；0.129 起 paused 的 goal 跨 resume 保持暂停 | [extension.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/extension.rs)、[0.129.0](https://github.com/openai/codex/releases/tag/rust-v0.129.0) |
| `/fork` | fork 时继承源 thread 的 goal snapshot（`inherit_thread_goal_snapshot`，校验 objective 合法性） | [codex-rs/app-server/src/request_processors/thread_fork_goal.rs](https://github.com/openai/codex/blob/main/codex-rs/app-server/src/request_processors/thread_fork_goal.rs) |
| `/compact` | 历史上 compaction 后 goal 续跑提示可能丢失导致提前完成（[issue #19910](https://github.com/openai/codex/issues/19910)）；maintainer 在 0.129 修了相关的无工具续跑抑制 bug（[#20523](https://github.com/openai/codex/pull/20523)） | [issue #19910](https://github.com/openai/codex/issues/19910) |
| `/statusline`（TUI footer） | goal 状态（含 token budget）显示在 status line，可用 `/statusline` 配置 footer 项 | [codex-rs/tui/src/chatwidget/tests/status_and_layout.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/chatwidget/tests/status_and_layout.rs) |
| `codex exec` | **不支持** `/goal`：`/goal` 是 TUI slash command，不是 shell 命令；0.134 为 ephemeral session 加了专门的错误提示 | [0.134.0](https://github.com/openai/codex/releases/tag/rust-v0.134.0)（#23796）、Tier 3 文章 [docs-slash-goal.md](https://github.com/davidondrej/jailbreak-autoresearch/blob/main/docs-slash-goal.md) |
| `AGENTS.md` / `/init` | 项目级持久指令（随仓库走），goal 是 thread 级运行时状态；官方明确区分 "not ... project-level instructions" | [Cookbook](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) |
| `features.goals` config | 只是启用开关，不存 goal 内容；goal 内容存 `goals_1.sqlite` | 见第 4 节 |

---

## 4. 实现细节

### 4.1 代码结构：一个独立 extension crate

`/goal` 的全部运行时逻辑位于 [codex-rs/ext/goal/](https://github.com/openai/codex/tree/main/codex-rs/ext/goal)（"Extension crate for the `/goal` feature"），挂接在 app-server 的 extension 体系上（`GoalExtension`），而非写死在 TUI 或 core 主循环里。TUI 的 `/goal` slash dispatch 见 [codex-rs/tui/src/chatwidget/slash_dispatch.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/chatwidget/slash_dispatch.rs)（无参 `/goal` 打开 goal 菜单 `OpenThreadGoalMenu`；带参则发 set-goal 事件）。

主要文件：

| 文件 | 职责 |
|---|---|
| `ext/goal/src/extension.rs` | `GoalExtension`：注册 thread/turn/tool/token-usage 生命周期钩子；注入 `get_goal`/`create_goal`/`update_goal` 三个工具（仅当 feature 启用且 thread 有持久状态且非 review subagent） |
| `ext/goal/src/spec.rs` | Responses API 工具定义（名称、描述、参数 schema） |
| `ext/goal/src/tool.rs` | `GoalToolExecutor`：三个工具的 handler（create/update 校验、budget 兜底） |
| `ext/goal/src/runtime.rs` | `GoalRuntimeHandle`：续跑调度、状态机、steering 注入 |
| `ext/goal/src/api.rs` | `GoalService`：供 app-server RPC 调用的 set/get/clear 服务层 |
| `ext/goal/templates/goals/` | 三个提示词模板：`continuation.md`、`budget_limit.md`、`objective_updated.md` |
| `core/src/goals.rs` | core 侧 goal 事件策略（`goal_runtime_apply` dispatcher）、模板渲染 |
| `state/src/runtime/goals.rs` | `GoalStore`：SQLite 读写 + token/墙钟会计 |
| `tui/src/goal_files.rs` | 超长 objective/粘贴/图片物化为附件文件 |

（各文件链接见第 7 节来源列表）

### 4.2 存储：`goals_1.sqlite` + `thread_goals` 表

Goal 存于**独立的专用 SQLite 库** `$CODEX_HOME/goals_1.sqlite`（源码常量 `GOALS_DB_FILENAME: &str = "goals_1.sqlite"`，[codex-rs/state/src/sqlite.rs](https://github.com/openai/codex/blob/main/codex-rs/state/src/sqlite.rs)；`StateRuntime` 用独立的 `goals_pool` 打开，[codex-rs/state/src/runtime.rs](https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime.rs)）。**注意：不存在 `~/.codex/goals.md` 之类的 Markdown 文件**——早期社区猜测的 markdown 存储已被源码证伪。

当前表结构（migration 0033 定型，[0033_thread_goal_stopped_statuses.sql](https://github.com/openai/codex/blob/main/codex-rs/state/migrations/0033_thread_goal_stopped_statuses.sql)）：

```sql
CREATE TABLE thread_goals (
    thread_id        TEXT PRIMARY KEY NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    goal_id          TEXT NOT NULL,          -- UUID（新 goal 替换旧 goal 时换新 id）
    objective        TEXT NOT NULL,          -- ≤4000 字符（协议层校验）
    status           TEXT NOT NULL CHECK(status IN
                     ('active','paused','blocked','usage_limited','budget_limited','complete')),
    token_budget     INTEGER,                -- 可选；goals.max_goal_token_budget 是上限兼默认值
    tokens_used      INTEGER NOT NULL DEFAULT 0,
    time_used_seconds INTEGER NOT NULL DEFAULT 0,   -- 墙钟会计（0.129 起支持多日时长显示）
    created_at_ms    INTEGER NOT NULL,
    updated_at_ms    INTEGER NOT NULL
);
```

存储演进：0029 建表（只有 active/paused/budget_limited/complete）→ 0033 增加 `blocked`/`usage_limited` → 0034 从主 state db 删除 `thread_goals` 表（迁移到专用 goals db，对应 0.133.0 "backed by dedicated storage"，[0.133.0](https://github.com/openai/codex/releases/tag/rust-v0.133.0)）。

### 4.3 状态机与协议字段

协议层 `ThreadGoalStatus` 枚举（`active/paused/blocked/usage_limited/budget_limited/complete`，camelCase 序列化，[protocol.rs](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs)）。状态转移规则（[spec.rs 工具描述](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/spec.rs) + [tool.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/tool.rs)）：

- `create_goal` 只允许在**没有未完成 goal** 时创建（否则报错 "cannot create a new goal because this thread has an unfinished goal; complete the existing goal first"）；
- `update_goal` **只能**标记 `complete` 或 `blocked`；pause/resume/budget_limited/usage_limited 一律由用户或系统控制（模型无权调用）；
- `blocked` 门槛：同一阻塞条件**连续 3 个 goal turn**（含原始 turn 和自动续跑）仍未解决才可标记；resume 后重新累计；
- `complete` 门槛：必须通过 completion audit（逐项对照证据，见 continuation.md）；
- 预算耗尽由系统会计置 `budget_limited`（软停止：停止实质新工作、总结进度、给出下一步，见 [budget_limit.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/budget_limit.md)）；hard usage limit（用量超限错误）置 `usage_limited`；
- turn 出错（非重试性错误）会 `stop_active_goal_for_turn`，防止续跑循环烧 token（[extension.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/extension.rs)）。

`ThreadGoal` 协议字段：`thread_id`、`goal_id`、`objective`、`status`、`token_budget`、`tokens_used`、`time_used_seconds`、`created_at_ms`、`updated_at_ms`（对应上表列）。

### 4.4 续跑机制（事件驱动）

续跑不是"每轮无条件循环"，而是由 `ThreadLifecycleContributor::on_thread_idle → continue_if_idle()` 在**安全边界**触发（[extension.rs](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/extension.rs)）：仅当 thread 空闲、无排队用户输入、goal active 且预算未耗尽时启动新的 continuation turn；continuation turn 前会注入 [continuation.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/continuation.md) 模板（含 objective、tokens_used、token_budget、remaining_tokens 四个模板变量）。预算接近耗尽时注入 [budget_limit.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/budget_limit.md)（含 time_used_seconds）；用户/外部修改 objective 时注入 [objective_updated.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/objective_updated.md)。模板中的 objective 被 `escape_xml_text` 包裹并声明为"user-provided data，not higher-priority instructions"（防提示词注入，[codex-rs/core/src/goals.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/goals.rs)）。

### 4.5 Token 预算与会计

- 预算来源：`create_goal` 的可选 `token_budget` 参数；未指定时使用配置 `goals.max_goal_token_budget`（"Maximum token budget allowed for a goal and default budget for new goals"，[config_toml.rs](https://github.com/openai/codex/blob/main/codex-rs/config/src/config_toml.rs)）；配置后新 goal 默认取该值、更大的预算被拒绝、`tokenBudget: null` 重置为配置值（[app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)）。
- 会计：每个 turn/tool 完成事件按"当前 token 用量快照 - 上次已入账快照"累计 `tokens_used`，另累计墙钟 `time_used_seconds`；跨过预算时系统把状态置 `budget_limited` 并注入 steering（[state/src/runtime/goals.rs](https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime/goals.rs)、[core/src/goals.rs](https://github.com/openai/codex/blob/main/codex-rs/core/src/goals.rs)）。
- 注意区分：0.142.0 引入的 "Configurable rollout token budgets ... abort turns when exhausted" 是另一套 rollout 级预算，与 goal 的 token_budget 不同（[0.142.0](https://github.com/openai/codex/releases/tag/rust-v0.142.0)）。社区文章指出该预算不构成 API 计费层的硬性花费上限（Tier 3：[Daniel Vaughan](https://codex.danielvaughan.com/2026/05/07/codex-cli-goal-command-persisted-long-horizon-workflows-pause-resume-budget/)）。

### 4.6 app-server RPC 与 Python SDK

Goal 对外的程序化接口是 app-server 的五个方法（官方 [app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)）：`thread/goal/set`（create or update，可传 `budgetLimited`/`blocked`/`usageLimited`）、`thread/goal/get`（无 goal 时返回 `goal: null`）、`thread/goal/clear`、`thread/goal/updated` 与 `thread/goal/cleared`（服务端通知）。TUI 自身也通过这套 RPC 操作 goal（[app_server_session.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/app_server_session.rs)）。Python SDK 提供 `set_goal` / `pause_goal` 等封装（[sdk/python client.py](https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/client.py)）。TUI 处理超长/粘贴/图片：物化为 `$CODEX_HOME/attachments/<uuid>/` 下的文件，超长 objective 整体写入 `goal-objective.md`，goal 正文替换为文件引用（`Read the Codex goal objective file at <path> before continuing.`，[goal_files.rs](https://github.com/openai/codex/blob/main/codex-rs/tui/src/goal_files.rs)；对应 0.140.0 "`/goal` now preserves oversized text, large pasted blocks, and image attachments"）。

---

## 5. 版本历史

| 版本 | 日期 | 与 /goal 相关变更 | 官方来源 |
|---|---|---|---|
| 0.128.0 | 2026-04-30 | **引入**：persisted `/goal` workflows（app-server APIs、model tools、runtime continuation、TUI create/pause/resume/clear 控件），5 个 PR #18073–#18077 + #20082，作者 @etraut-openai（Eric Traut）；默认未启用 | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.128.0) |
| 0.129.0 | 2026-05-07 | 标记 **experimental**（#20083）；可发现性改进（slash 弹窗可见）；**paused 跨 resume 保持暂停**；更清晰的校验报错与多日时长显示（#20790、#20746、#20558）；移除无工具续跑的抑制（#20523） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.129.0) |
| 0.132.0 | 2026-05-20 | 修复：goal 续跑在 usage limit/重复 blocker 下不再循环烧 token（#23094）；完成时 token 用量报告措辞改进（#22907） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.132.0) |
| 0.133.0 | 2026-05-21 | **默认启用** + **专用存储**（goals db）+ 跨 active turns 跟踪进度（#23300、#23685、#23696、#23732） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.133.0) |
| 0.134.0 | 2026-05-26 | ephemeral session 的 `/goal` 报错改进（#23796）；completed goal 替换时跳过确认提示（#23792）；budget-limited goal 的 extension turn steering（#23718） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.134.0) |
| 0.138.0 | 2026-06-08 | `/goal edit` 多行粘贴不再提前提交；idle auto-turn 不进 Plan mode；terminal turn 失败后停止自动续跑（#26047、#26147、#26690） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.138.0) |
| 0.140.0 | 2026-06-15 | `/goal` 保留超长文本、大粘贴块、图片附件（含 remote app-server 会话）（#27508–#27510） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.140.0) |
| 0.142.0 | 2026-06-22 | 修复 goal-first threads 不再被 `thread/list`、`thread/search` 返回的问题（#28808） | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.142.0) |
| 0.147.0（当前） | 2026-08-07 | 最新稳定版；`main` 分支 feature stage 已为 Stable、默认启用 | [release notes](https://github.com/openai/codex/releases/tag/rust-v0.147.0) |

演进叙事：0.128 以 feature flag 形式低调上线（官方 docs 当时完全没提，社区一度质疑其真实性，见 [issue #20536](https://github.com/openai/codex/issues/20536)）；0.129 标记 experimental 并允许 `/experimental` 开关；0.133 默认启用并迁到专用存储——至此 `/goal` 成为一等公民。整个过程中状态机从 4 态扩到 6 态（加了 blocked/usage_limited），续跑策略持续收紧（防烧 token、防 plan mode 误触发、防 terminal 失败后死循环）。另有社区来源声称"v0.116 左右就有一个丢失状态的早期 goal mode"（[Daniel Vaughan](https://codex.danielvaughan.com/2026/04/30/codex-cli-v0128-goal-workflows-keymap-self-update/)，Tier 3），但官方 0.116.0 release notes 无任何 goal 相关内容，该 claim 无法用一手来源证实，仅记录存疑。

---

## 6. 已知限制与 FAQ

| 问题 | 答案 | 来源层级 |
|---|---|---|
| 为什么我的 CLI 里没有 `/goal`？ | 版本 <0.128.0 没有此命令；0.128–0.132 需手动启用（`[features] goals = true` 或 `codex features enable goals`）；0.133+ 默认启用；改了 config 需重启会话 | Tier 1：[#20548](https://github.com/openai/codex/issues/20548)（maintainer 答复）、[0.133.0](https://github.com/openai/codex/releases/tag/rust-v0.133.0) |
| 官方文档当时为什么没写 `/goal`？ | 0.128–0.132 期间官方 slash-commands 文档确实未收录；[issue #20536](https://github.com/openai/codex/issues/20536)（2026-05-01 提出）于 2026-05-14 由 maintainer 关闭，指向新上线的 [Follow a goal](https://developers.openai.com/codex/use-cases/follow-goals) 页 | Tier 1：[#20536](https://github.com/openai/codex/issues/20536) |
| goal 会不会"提前宣布完成"？ | 官方设计对此有专门防线：completion 必须通过基于证据的 audit（见 continuation.md）；但社区实测发现 compaction 场景下 audit 指令可能丢失导致提前完成（[#19910](https://github.com/openai/codex/issues/19910)），maintainer 未复现但修了相关 bug（#20523）；官方 Cookbook 建议完成后人工复核 | Tier 1 + Tier 4（issue 作者自述） |
| `/goal` 在 `codex exec` 里能用吗？ | 官方将其定义为 TUI slash command；0.134 为 ephemeral session 加了专门报错（#23796），表明 exec/ephemeral 场景不受支持；社区实测 `codex exec "/goal ..."` 不生效 | Tier 1（[0.134.0](https://github.com/openai/codex/releases/tag/rust-v0.134.0)）+ Tier 3 |
| 有 `/goal status` 或 `/goal budget` 吗？ | 没有。查看状态用裸 `/goal`；预算经 `create_goal` 的 token_budget 参数或 `goals.max_goal_token_budget` 配置；早期社区文章（2026-05 初）误报"没有 /goal edit"，当前官方文档已含 `/goal edit` | Tier 1（[slash-commands](https://developers.openai.com/codex/cli/slash-commands)）；Tier 3 早期文章如 [J.D. Hodges](https://www.jdhodges.com/blog/codex-goal-feature-review/) |
| 每个平台都能用吗？ | CLI 各平台均有实现；Mac 桌面 App 曾有 slash 菜单显示 "No commands" 的问题（[#21125](https://github.com/openai/codex/issues/21125)），不同 surface 支持度可能不同 | Tier 1（issue 记录） |
| 需要 ChatGPT 订阅吗？ | 社区文档声称 `/goal` 只在 ChatGPT 账号（Plus/Pro/Business/Edu/Enterprise）下激活，API-key 认证不启用，因为依赖 ChatGPT app-server 持久化层（[docs-slash-goal.md](https://github.com/davidondrej/jailbreak-autoresearch/blob/main/docs-slash-goal.md)，Tier 3）；官方文档未明确此限制，未能以 Tier 1 来源证实或证伪 | 仅 Tier 3 |
| 预算达到后会发生什么？ | 系统置 `budget_limited` 并注入收尾提示词：停止新实质工作、总结进度/阻塞、给出下一步；可在新会话 `/goal resume` 继续（官方 [budget_limit.md](https://github.com/openai/codex/blob/main/codex-rs/ext/goal/templates/goals/budget_limit.md) 模板；resume 提示见 Tier 3 社区文档） | Tier 1（模板源码）+ Tier 3 |
| 安全边界如何？ | `/goal` 不改变权限/沙箱模型——approval 策略、sandbox、goal 文本里的约束仍由用户负责；社区提醒"一个坏 goal 会让 agent 跑一个小时" | Tier 1（官方文档无特权声明）+ Tier 3（[J.D. Hodges](https://www.jdhodges.com/blog/codex-goal-feature-review/)） |
| 社区常见的错误命令形式？ | `/goal create "..."`（v0.128 早期社区文章写法，官方从未采用——设置直接是 `/goal <objective>`）；`/goals`（复数）；`/goal set`；均为误传/误写 | Tier 3（[LaoZhang AI](https://blog.laozhang.ai/en/posts/codex-goal) 对此有专门澄清）；官方语法见 [slash-commands](https://developers.openai.com/codex/cli/slash-commands) |

---

## 7. 来源列表

### Tier 1：官方文档

1. OpenAI Developers — Slash commands in Codex CLI（`/goal` 命令表 + "Set or view a task goal" 教程）：https://developers.openai.com/codex/cli/slash-commands
2. OpenAI Developers — Follow a goal（Codex use cases）：https://developers.openai.com/codex/use-cases/follow-goals
3. OpenAI Cookbook — Using Goals in Codex（2026-05-09，Raj Pathak & Stefano Fabbri）：https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex

### Tier 1：官方 release notes

4. 0.128.0（2026-04-30）：https://github.com/openai/codex/releases/tag/rust-v0.128.0
5. 0.129.0（2026-05-07）：https://github.com/openai/codex/releases/tag/rust-v0.129.0
6. 0.132.0（2026-05-20）：https://github.com/openai/codex/releases/tag/rust-v0.132.0
7. 0.133.0（2026-05-21）：https://github.com/openai/codex/releases/tag/rust-v0.133.0
8. 0.134.0（2026-05-26）：https://github.com/openai/codex/releases/tag/rust-v0.134.0
9. 0.138.0（2026-06-08）：https://github.com/openai/codex/releases/tag/rust-v0.138.0
10. 0.140.0（2026-06-15）：https://github.com/openai/codex/releases/tag/rust-v0.140.0
11. 0.142.0（2026-06-22）：https://github.com/openai/codex/releases/tag/rust-v0.142.0
12. 0.147.0（2026-08-07，调研日最新稳定版）：https://github.com/openai/codex/releases/tag/rust-v0.147.0

### Tier 1：官方源码（openai/codex `main` 分支）

13. `ext/goal/` extension crate：https://github.com/openai/codex/tree/main/codex-rs/ext/goal
14. `ext/goal/src/extension.rs`（生命周期钩子与工具注入）：https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/extension.rs
15. `ext/goal/src/spec.rs`（get_goal/create_goal/update_goal 工具定义）：https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/spec.rs
16. `ext/goal/src/tool.rs`（工具 handler 与状态限制）：https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/tool.rs
17. `ext/goal/src/api.rs`（GoalService）：https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/api.rs
18. `ext/goal/src/runtime.rs`（续跑调度）：https://github.com/openai/codex/blob/main/codex-rs/ext/goal/src/runtime.rs
19. 提示词模板 `continuation.md` / `budget_limit.md` / `objective_updated.md`：https://github.com/openai/codex/tree/main/codex-rs/ext/goal/templates/goals
20. `core/src/goals.rs`（goal 运行时事件策略与模板渲染）：https://github.com/openai/codex/blob/main/codex-rs/core/src/goals.rs
21. `state/src/runtime/goals.rs`（GoalStore SQL 与会计）：https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime/goals.rs
22. `state/src/runtime.rs`（goals_pool 专用连接）：https://github.com/openai/codex/blob/main/codex-rs/state/src/runtime.rs
23. `state/src/sqlite.rs`（`goals_1.sqlite` 文件名）：https://github.com/openai/codex/blob/main/codex-rs/state/src/sqlite.rs
24. `state/src/model/thread_goal.rs`（状态枚举与行模型）：https://github.com/openai/codex/blob/main/codex-rs/state/src/model/thread_goal.rs
25. migrations 0029/0033/0034（thread_goals 表演进）：https://github.com/openai/codex/tree/main/codex-rs/state/migrations
26. `protocol/src/protocol.rs`（`MAX_THREAD_GOAL_OBJECTIVE_CHARS = 4_000`、ThreadGoalStatus）：https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs
27. `features/src/lib.rs`（Feature::Goals：key "goals"、Stable、默认启用）：https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs
28. `config/src/config_toml.rs`（GoalsToml.max_goal_token_budget）：https://github.com/openai/codex/blob/main/codex-rs/config/src/config_toml.rs
29. `tui/src/goal_files.rs`（附件物化）：https://github.com/openai/codex/blob/main/codex-rs/tui/src/goal_files.rs
30. `tui/src/chatwidget/slash_dispatch.rs`（/goal slash dispatch）：https://github.com/openai/codex/blob/main/codex-rs/tui/src/chatwidget/slash_dispatch.rs
31. `app-server/README.md`（thread/goal/* RPC 官方文档）：https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md
32. `app-server/src/request_processors/thread_goal_processor.rs`：https://github.com/openai/codex/blob/main/codex-rs/app-server/src/request_processors/thread_goal_processor.rs
33. `app-server/src/request_processors/thread_fork_goal.rs`（fork 继承）：https://github.com/openai/codex/blob/main/codex-rs/app-server/src/request_processors/thread_fork_goal.rs
34. Python SDK `sdk/python/src/openai_codex/client.py`（set_goal/pause_goal）：https://github.com/openai/codex/blob/main/sdk/python/src/openai_codex/client.py

### Tier 1：官方 issue / PR

35. Issue #20536 — 文档缺口（2026-05-01 提出，2026-05-14 由 @etraut-openai 关闭）：https://github.com/openai/codex/issues/20536
36. Issue #20548 — WSL 上 /goal unrecognized（maintainer 确认 0.128 需 feature flag）：https://github.com/openai/codex/issues/20548
37. Issue #19910 — compaction 后 goal 审计指令丢失（@etraut-openai 回复 + 修复 PR #20523）：https://github.com/openai/codex/issues/19910

### Tier 3：社区文章（仅作佐证，正文已用限定词标注）

38. Daniel Vaughan — Codex CLI /goal: Persisted Long-Horizon Workflows...（2026-05-07）：https://codex.danielvaughan.com/2026/05/07/codex-cli-goal-command-persisted-long-horizon-workflows-pause-resume-budget/
39. Daniel Vaughan — Codex CLI v0.128: Goal Workflows...（2026-04-30，含"v0.116 早期 goal mode"存疑 claim）：https://codex.danielvaughan.com/2026/04/30/codex-cli-v0128-goal-workflows-keymap-self-update/
40. LaoZhang AI — Codex /goal: What It Does, How to Use It, and Why It May Be Missing（2026-05-04）：https://blog.laozhang.ai/en/posts/codex-goal
41. J.D. Hodges — Codex /goal: How It Works, Setup, and What I Tested（2026-05-08）：https://www.jdhodges.com/blog/codex-goal-feature-review/
42. Chris Ashby（Build Great Products）— Codex CLI /goal — A Guide（2026-05-05）：https://www.buildgreatproducts.com/guides/codex-cli-goal
43. Mehmet Baykar — Codex CLI /goal: Enable the Ralph Loop（2026-05-08）：https://mehmetbaykar.com/posts/enable-goal-mode-in-codex-cli/
44. AI Catchup — Codex CLI 0.128.0 Lands Persisted /goal Workflows（2026-05-01，引用 Felipe Coury 关于 Ralph loop 的发言）：https://aicatchup.com/news/codex-cli-0-128-persisted-goal
45. davidondrej/jailbreak-autoresearch — Codex `/goal` Complete Reference（含 ChatGPT auth 要求等未证实 claim）：https://github.com/davidondrej/jailbreak-autoresearch/blob/main/docs-slash-goal.md
