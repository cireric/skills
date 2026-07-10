# Oh My OpenAgent (OMO) 内置工具完整清单

> 来源: [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) · v4.15.1 · 65K ⭐
> 调研日期: 2026-07-08
> 两个版本：Ultimate (OpenCode) / Light (Codex CLI)

---

## 一、11 个 Discipline Agents

| Agent | 默认模型 | 角色 | Mode | 工具限制 |
|-------|---------|------|------|---------|
| **Sisyphus** | claude-opus-4-7 max | 主编排器，规划+委派+并行执行，thinking 32K | primary | 无 |
| **Hephaestus** | gpt-5.5 medium | 自主深度 worker，目标导向端到端执行 | primary | 无 |
| **Prometheus** | claude-opus-4-7 max | 战略规划器，面试模式提问+建计划 | primary | 仅写 .md |
| **Atlas** | claude-sonnet-4-6 | Todo 编排器，执行 Prometheus 计划 | primary | 禁 task, call_omo_agent |
| **Oracle** | gpt-5.5 high | 架构咨询/代码审查/调试（只读） | subagent | 禁 write, edit, task, call_omo_agent |
| **Librarian** | gpt-5.4-mini-fast | 文档/OSS 代码搜索 | subagent | 禁 write, edit, task, call_omo_agent |
| **Explore** | gpt-5.4-mini-fast | 快速 codebase grep | subagent | 禁 write, edit, task, call_omo_agent |
| **Multimodal-Looker** | gpt-5.5 medium | PDF/图片/截图分析 | subagent | 仅 read |
| **Metis** | claude-sonnet-4-6 | 计划顾问，预规划分析+识别盲点 | subagent | 无 |
| **Momus** | gpt-5.5 xhigh | 计划审查，验证清晰/可验证/完整 | subagent | 禁 write, edit, task |
| **Sisyphus-Junior** | (按 category 路由) | Category 派生执行器 | subagent | 无 |

### Agent 调用方式

主 agent 自动调用，也可显式调用：

```
Ask @oracle to review this design and propose an architecture
Ask @librarian how this is implemented - why does the behavior keep changing?
Ask @explore for the policy on this feature
```

### Mode 说明

- **primary** — 尊重用户 UI 选择的模型，使用配置的 fallback 链。用于: sisyphus, hephaestus, atlas, prometheus
- **subagent** — 使用自己的 fallback 链，忽略用户 UI 选择。用于: oracle, librarian, explore, multimodal-looker, metis, momus, sisyphus-junior

### planner_enabled / replace_plan 交互逻辑

| `planner_enabled` | `replace_plan` | Prometheus | 原生 plan agent | 效果 |
|:-:|:-:|:-:|:-:|:--|
| `true` | `true` (默认) | 注册为 primary | demote → hidden subagent | plan 选择器只显示 Prometheus |
| `true` | `false` | 注册为 primary | 保留为可见 primary | plan 选择器同时显示两个 |
| `false` | — | 不注册 | 保留为可见 primary | plan 选择器显示原生 plan |

**关键陷阱**：`planner_enabled: false` 禁了 Prometheus，但原生 `plan` agent 会恢复可见。若要同时隐藏两者：

```jsonc
{
  "sisyphus_agent": {
    "planner_enabled": true,
    "replace_plan": true
  },
  "agents": {
    "prometheus": { "mode": "subagent" }
  }
}
```

- `planner_enabled: true` + `replace_plan: true` → 原生 plan 被 hidden demote
- `agents.prometheus.mode: "subagent"` → Prometheus 降为 subagent，不出现在 primary agent 选择器，但 Sisyphus 的 `task(subagent_type="prometheus")` 仍可正常委派

> ⚠️ **`disabled_agents: ["prometheus"]` 对 Prometheus 无效** — Prometheus 的注册由 `planner_enabled` 独立控制（`agent-config-handler.ts` 中 `if (plannerEnabled) { agentConfig["prometheus"] = ... }`），在 `createBuiltinAgents` 之外直接赋值，不受 `disabledAgents` 过滤。`disabledAgents` 只过滤 general agents（oracle, librarian, explore 等）。
>
> **`agents.prometheus.disable: true` 也无效** — `disable` 字段虽在 schema 中定义，但 `applyOverrides` 只做 `deepMerge`，没有代码读取 `disable` 来跳过注册或设 `hidden: true`。它只影响 orchestrator prompt 的 availableAgents 列表（让 Sisyphus 不知道 prometheus 存在），但 agent 仍注册在 `config.agent` 中，TUI 仍显示。
>
> 参考: PR #3444 (hidden flag fix), PR #3620 (prompt 引用 prometheus 而非 plan alias), PR #3992 (hidden agent 从 task 委派中排除), Issue #3443, Issue #3596, Issue #1693 (disabled_agents 不过滤 custom agents)

---

## 二、Native Tools（12 常驻 + 19 条件）

### 常驻 12 工具

| 分组 | 工具 | 说明 |
|------|------|------|
| Search | `grep`, `glob` | 代码搜索 |
| Sessions | `session_list`, `session_read`, `session_search`, `session_info` | 会话历史管理 |
| Background | `background_output`, `background_cancel` | 后台 agent 控制 |
| Delegation | `task`, `call_omo_agent` | 委派（task 支持 category+skill；call_omo_agent 仅 explore/librarian） |
| Skill/MCP | `skill`, `skill_mcp` | 加载 skill / 调用 skill-embedded MCP |

### 条件工具（按配置门控）

| 工具 | 门控条件 | 说明 |
|------|---------|------|
| `look_at` | multimodal-looker 未禁用 | 图片/PDF 分析 |
| `interactive_bash` | tmux 配置启用 | 交互式终端（REPL/调试器/TUI） |
| `task_create/get/list/update` | `experimental.task_system` | Sisyphus 任务系统 |
| `edit` (hashline) | `hashline_edit: true` | LINE#ID 哈希锚定编辑，零 stale-line 错误 |
| 12 个 `team_*` 工具 | `team_mode.enabled: true` | Team Mode 多 agent 协作 |

### 12 个 team_* 工具

| 工具 | 用途 |
|------|------|
| `team_create` | 创建团队+成员会话 |
| `team_delete` | 拆除团队（邮箱+任务+worktree+tmux） |
| `team_shutdown_request` | 成员请求自身关闭 |
| `team_approve_shutdown` | Lead 确认关闭 |
| `team_reject_shutdown` | Lead 拒绝关闭 |
| `team_send_message` | 异步消息（指定成员或 `*` 广播） |
| `team_task_create` | 创建共享任务 |
| `team_task_list` | 列出任务（按状态/负责人过滤） |
| `team_task_update` | 认领/完成/删除（原子文件锁） |
| `team_task_get` | 获取单个任务 |
| `team_status` | 团队全状态 |
| `team_list` | 列出已声明+活跃团队 |

---

## 三、Built-in MCPs（5 个）

| MCP | Tier | 工具 | 说明 |
|-----|------|------|------|
| **Exa** (`websearch`) | Tier-1 内置 | web search | Web 搜索 |
| **Context7** | Tier-1 内置 | doc query | 官方文档查询 |
| **Grep.app** | Tier-1 内置 | GitHub code search | GitHub 代码搜索 |
| **LSP** | Tier-1 内置 | `lsp_diagnostics`, `lsp_goto_definition`, `lsp_find_references`, `lsp_rename` | IDE 级精确导航+重构 |
| **AST-Grep** | Tier-1 内置 | `ast_grep_search` 等 | 25 语言模式感知搜索+重写 |

注意：内置 MCP 由 plugin 运行时注入，不会出现在 `opencode mcp list` 中。

---

## 四、Built-in Skills（2 个）

| Skill | 说明 |
|-------|------|
| **playwright** | 浏览器自动化 |
| **git-master** | 原子提交 |

---

## 五、Slash Commands（8 个）

| 命令 | 说明 |
|------|------|
| `/init-deep` | 自动生成层级 AGENTS.md 知识库 |
| `/ralph-loop` | 自引用开发循环，不停直到完成 |
| `/ulw-loop` | ultrawork 循环，持续 ultrawork 模式 |
| `/cancel-ralph` | 取消活跃 Ralph Loop |
| `/refactor` | 智能重构（LSP + AST-grep + 架构分析 + TDD 验证） |
| `/start-work` | 从 Prometheus 计划启动 Sisyphus 工作会话 |
| `/stop-continuation` | 停止所有延续机制（ralph loop / todo continuation / boulder） |
| `/handoff` | 创建详细上下文摘要，用于新会话续接 |

自定义命令加载路径：
- `.opencode/command/*.md`（项目级，OpenCode 原生）
- `~/.config/opencode/command/*.md`（用户级，OpenCode 原生）
- `.claude/commands/*.md`（项目级，Claude Code 兼容）
- `~/.config/opencode/commands/*.md`（用户级，Claude Code 兼容）

---

## 六、Working Modes

| 模式 | 触发 | 说明 |
|------|------|------|
| **ultrawork / ulw** | 输入 `ultrawork` 或 `ulw` | 全自动，所有 agent 激活，不停直到完成 |
| **Prometheus** | 按 Tab 或 `@plan` | 面试模式规划，然后 `/start-work` 执行 |
| **search** | — | 搜索优先模式 |
| **analyze** | — | 分析优先模式 |
| **team** | `team_mode.enabled: true` | Lead + ≤8 成员并行 |
| **hyperplan** | Team Mode 下 | 5 个对抗 agent 从正交角度撕碎计划 |
| **security-research** | Team Mode 下 | 3 猎手 + 2 PoC 工程师并行审计 |

---

## 七、Category System（8 个任务路由类别）

| Category | 默认模型 | 适用 |
|----------|---------|------|
| `visual-engineering` | gemini-3.1-pro high | 前端/UI |
| `ultrabrain` | gpt-5.5 xhigh | 硬逻辑/架构 |
| `deep` | gpt-5.5 medium | 自主研究/执行 |
| `artistry` | gemini-3.1-pro high | 创意/设计 |
| `quick` | gpt-5.4-mini | 快速任务 |
| `unspecified-low` | gpt-5.4-mini | 低成本回退 |
| `unspecified-high` | claude-opus-4-7 max | 高质量回退 |
| `writing` | claude-opus-4-7 high | 文档/散文 |

Sisyphus 委派时选择 category 而非模型名，category 自动路由到对应模型。

---

## 八、Productivity Features

| 特性 | 说明 |
|------|------|
| **IntentGate** | 分析用户真实意图后再分类/行动 |
| **Todo Enforcer** | Agent 空闲时系统强制拉回，任务必须完成 |
| **Comment Checker** | 检查注释无 AI 废话 |
| **Rules Injection** | 自动注入 AGENTS.md + .omo/rules/** |
| **Ralph Loop** | 自引用循环，不停直到 100% 完成 |
| **Hash-Anchored Edit** | LINE#ID 哈希验证每次编辑，零 stale-line 错误 |
| **Background Agents** | 5+ 专家并行，上下文精简，完成时通知 |
| **Tmux Integration** | 全交互终端，REPL/调试器/TUI，实时可视化 |
| **Skill-Embedded MCPs** | Skill 携带自身 MCP server，无上下文膨胀 |
| **54+ Lifecycle Hooks** | 全可配置（Team Mode 下 61），可 `disabled_hooks` 关闭 |
| **Doctor Command** | `bunx oh-my-opencode doctor` 诊断注册/配置/模型/环境 |
| **Session Recovery** | 自动会话错误恢复 |
| **OpenClaw** | 双向集成 Discord/Telegram/HTTP/Shell + reply listener daemon |

---

## 九、Light Edition (Codex CLI) 差异

### Light 版包含

- 组件: rules, comment-checker, git-bash, lsp, ultrawork, ulw-loop, start-work-continuation, telemetry
- Plugin-scoped MCPs: grep_app, context7, codegraph, git_bash, lsp
- Skill: ast-grep

### Light 版不含

- 11 Discipline Agents（无 agent 编排）
- team_* 工具（12 个）
- IntentGate
- Background Agents
- AST-Grep MCP（仅保留 ast-grep skill）
- Tmux Integration
- Prometheus / Atlas / Momus / Metis
- Slash commands（除 ulw-loop）
- Hashline edit
- OpenClaw

---

## 十、架构快照

| 维度 | 数量 |
|------|------|
| Feature 模块 | 20 |
| Tool 目录 | 16 → 20~39 工具（按配置门控） |
| Lifecycle Hooks | 54 基础 / 61 (Team Mode) |
| MCP 层级 | 3 (Tier-1 内置 / .mcp.json 加载 / Skill-embedded) |
| Manager | 4 (TmuxSessionManager, BackgroundManager, SkillMcpManager, ConfigHandler) |
| Config Pipeline Phase | 6 (provider → plugin-components → agents → tools → MCPs → commands) |
| 核心 Agent 顺序 | Sisyphus → Hephaestus → Prometheus → Atlas |
