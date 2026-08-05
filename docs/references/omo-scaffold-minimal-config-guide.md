# 把 oh-my-openagent 当作脚手架：中高价值保留配置指南

> **适用版本**：`oh-my-openagent` v4.19.4（dev 分支 @ `9cee074d`，2026-08-04）；`opencode` SDK `@opencode-ai/plugin` + `@opencode-ai/sdk` 1.15.13（omo `doctor` 最低要求 opencode ≥ 1.4.0）。
>
> **版本偏移警告**：本文 §3.5 的 hook 完整名单基于 v3.x 时期整理的 56 个 hook（详见 [`oh-my-openagent-architecture.md` §13.1](../research/oh-my-openagent-architecture.md#L1390-L1405)），v4 系列可能有增删。落地后请以 `bunx oh-my-openagent doctor` 的实际输出为准，并把任何差异回填本文。
>
> **场景**：已在使用 `opencode` + `oh-my-openagent`(omo)，希望把这个偏重的编排框架裁剪为「仅屏蔽低价值项、中高价值全保留」的个人全局脚手架。
>
> **策略**：以「价值指数」为唯一阈值——极高/高/中 → 保留，低 → 屏蔽。结论是一份可直接落盘的 `~/.config/opencode/oh-my-openagent.jsonc`。
>
> **证据**：本文所有功能名录、默认值、屏蔽键均来自 omo 官方 GitHub 仓库（文档 + 源码），详见文末「证据来源」。每条证据附 commit / release / PR 锚点。

---

## 目录

1. [背景与策略](#1-背景与策略)
2. [omo 架构与裁剪机制](#2-omo-架构与裁剪机制)
3. [功能取舍清单](#3-功能取舍清单)
4. [最终配置](#4-最终配置)
5. [落地步骤](#5-落地步骤)
6. [验证清单](#6-验证清单)
7. [风险提醒](#7-风险提醒)
8. [证据来源](#8-证据来源)

---

## 1. 背景与策略

### 1.1 环境特征

- 运行时：`opencode`（SDK 1.15.13，≥1.4.0 满足 omo doctor 门槛）+ `oh-my-openagent`(omo) v4.19.4 插件。
- 自有 **provider**：`astroncodingplan` / `deepseek`，**无** GPT / Claude / Gemini 等 omo 默认模型。
- 已有自有 skills 仓库（`cireric-skills`：`book-grill` / `info-collector` / `reading-grill` / `url2md` 等）与项目级 `AGENTS.md` 双层规则体系。

### 1.2 取舍策略演进

| 阶段 | 策略 | 问题 |
|---|---|---|
| 初版 | 极简：主 agent 仅留 sisyphus，其余一概关 | 过激进，砍掉 prometheus/atlas 等编排核心价值 |
| 定稿 | **平衡**：中/高价值全保留，仅屏蔽低价值项 | —— |

### 1.3 价值指数与阈值

基于本环境（自有 skills、无 GPT/Claude/Gemini、当脚手架用）评估：

| 等级 | 含义 | 动作 |
|---|---|---|
| 极高 | 框架运行依赖或不可替代的核心 | 保留 |
| 高 | 强增值、无模型/环境依赖 | 保留 |
| 中 | 有用、可替代或需配合其他功能 | 保留 |
| 低 | 冗余、环境不可用、或纯通知/提示噪音 | 屏蔽 |

**阈值：极高/高/中 → 保留；低 → 屏蔽。**

### 1.4 环境约束（非价值因素）

- **`hephaestus`**：源码硬性要求 GPT 家族模型（`isHephaestusSupportedModel` 校验 + `requiresProvider` 限定 openai/github-copilot/venice/opencode/vercel）。**无 GPT 环境下无法复活**——omo 自身也会跳过它。复活必须接入 GPT provider，而非把模型覆盖到非 GPT provider。→ 屏蔽。
- **`multimodal-looker`**：低价值（无图像模型）→ 屏蔽。
- **`team_mode`**：独立重型功能（非 agent/skill/command/mcp 范畴），默认关，按需再开，不在「中高保留」讨论内。

---

## 2. omo 架构与裁剪机制

### 2.1 功能面总览

omo（Ultimate Edition for OpenCode）是一套多 agent 编排框架：

| 模块 | 体量 | 说明 |
|---|---|---|
| 11 个内置 agent | 重 | sisyphus（主）→ atlas / oracle / librarian / explore / prometheus … 按任务类型委托 |
| 50+ 生命周期 hooks | 重 | 分多层：Session / Tool Guard / Transform / Continuation / Skill |
| 内置 skills（13+） | 中 | playwright×4、git-master、frontend、review-work、security-research、hyperplan、ast-grep 等 |
| 内置 MCPs（4） | 轻 | websearch(Exa) / context7 / grep_app / lsp，运行时注入 |
| 内置 commands（斜杠） | 轻 | ralph-loop / ulw-loop / start-work / handoff / hyperplan / refactor 等 |
| Team Mode / tmux / browser | 中 | 默认关；12 个 `team_*` 工具 |
| 分类路由 categories | 轻 | 任务按 intent 路由到模型 |

### 2.2 配置分两层（关键）

| 文件 | 归属 | 内容 |
|---|---|---|
| `~/.config/opencode/opencode.jsonc` | 基座（自有） | `provider` / `mcp` / `skills.paths` / `plugin` |
| `~/.config/opencode/oh-my-openagent.jsonc` | omo 插件 | 所有「关掉什么」的开关（`disabled_*`）与插件专属项 |

**脚手架思路**：基座不动，所有裁剪都落在 `oh-my-openagent.jsonc`。

### 2.3 屏蔽机制

omo 提供一组 `disabled_*` 键（均在插件配置中）：

- `disabled_agents` / `disabled_skills` / `disabled_hooks` / `disabled_commands` / `disabled_mcps` / `disabled_tools` / `disabled_providers`
- 另有 `team_mode.enabled`、`auto_update`、`hashline_edit`、`new_task_system_enabled`、`runtime_fallback` / `model_fallback`
- `claude_code.{mcp,commands,skills,agents,hooks,plugins}`：opencode 原生已支持，应全关

### 2.4 安全类 hooks（勿关）

官方明文警告：以下 hooks 保护安全 / 权限 / provider 协议正确性，**仅在你可信的本地审计调试时才可动**：

`team-tool-gating`、`write-existing-file-guard`、`bash-file-read-guard`、`webfetch-redirect-guard`、`prometheus-md-only`、`rules-injector`、`tool-pair-validator`、`thinking-block-validator`。

此外 `no-sisyphus-gpt` 官方明确标注 **「do not disable」**（它拦截不兼容的 GPT 模型、同时放行专用 GPT 路径）。本配置均保留这些 hooks。

### 2.5 关键坑

- **配置名一致性**：omo 探测优先旧名 `oh-my-opencode` 而非 `oh-my-openagent`；同一目录别两个 basename 混用，统一用 `oh-my-openagent`。
- **`sisyphus` 不可完全 disable**：主 agent，插件依赖它。
- **categories 必须重映射**：默认 categories 指向 `claude-opus / gpt-5.5 / gemini` 等你可能没有的模型，须映射到你实际可用的模型（如 `astroncodingplan/astron-code-latest`、`deepseek/deepseek-v4-pro`），否则触发分类路由报 model not found。
- **安装不覆盖**：`bunx oh-my-openagent install` 会改写全局 `opencode.jsonc` 注册插件，需手动 merge 保留自有 `provider`/`mcp`。

---

## 3. 功能取舍清单

阈值：极高/高/中 → 保留；低 → 屏蔽。

### 3.1 Agents（11）

> **同名实体澄清**：`atlas` 在 §3.5 D 还存在一个**同名 hook**（参与 boulder-state 续接、计划文件解析等副作用），与 agent 是不同实体。下面表格只针对 agent；hook 是否保留见 §3.5 D。

| Agent | 作用 | 动作 | 理由 |
|---|---|---|---|
| sisyphus | 主编排 agent（插件依赖） | **留** | 框架运行依赖，不可 disable |
| oracle | 架构/调试咨询 | **留** | 高增值、只读、无模型/环境依赖 |
| librarian | 文档/代码检索 | **留** | 中高增值、无环境依赖 |
| explore | 快 grep | **留** | 中高增值、无环境依赖 |
| metis | plan 顾问 | **留** | 中增值；虽然常配 prometheus，但 prometheus 关闭后 metis 仍可作为独立 plan 顾问被委托 |
| momus | 严厉 critic | **留** | 中增值、无环境依赖 |
| sisyphus-junior | 轻量子 agent（分类委托） | **留** | 中增值、无环境依赖 |
| prometheus | 规划访谈 | **关** | 规划评审循环**不收敛**——多轮审稿总能从不同角度发现问题、缺终止条件，且整体过度流程化。详见下方决策块 |
| atlas | Todo 编排执行 | **关** | 最佳表现**依赖** prometheus 元数据契约；二者绑定，留 atlas 必留 prometheus，否则退化为即兴分解。详见下方决策块 |
| hephaestus | 工程/实现 | **关** | 硬性要求 GPT 家族（`isHephaestusSupportedModel` + `requiresProvider` 限定 openai/github-copilot/venice/opencode/vercel），无 GPT 环境下无法复活 |
| multimodal-looker | 多模态看图 | **关** | 无图像模型，环境不可用 |

`disabled_agents`: `["hephaestus","multimodal-looker","prometheus","atlas"]`

> **关于 `prometheus` + `atlas` 关闭决策的完整论证**
>
> 在「已有工程纪律 + 用 `grill-with-docs` 做需求发现、无 GPT」的场景下，二者**净收益为负**：
> - `prometheus` 是唯一产出 Atlas 结构化元数据（`Parallel Execution Graph` / `Delegation Recommendation` 等）的环节，但其规划评审循环**不收敛**——多轮审稿总能从不同角度发现问题、缺终止条件，且整体过度流程化。
> - `atlas` 的最佳表现**依赖** prometheus 的元数据契约（见 §8 证据），二者绑定：留 atlas 必留 prometheus（否则退化为即兴分解）。故同关，仅保留 `grill-with-docs` 作为规划甜点区。
>
> **收敛约束（仅当未来重启 prometheus 时需要）**：给 review 循环加终止条件——① 单一收敛权威（你手动喊停）；② 事前 DoD / 验收闸门；③ 严重度分级（仅 `blocking` 触发下一轮）；④ 轮次 / 视角预算封顶。omo 本身不提供，需手动补。
>
> **工程经验复用（notepad）剥离保留**：Atlas 的 `.omo/notepads/{scope}/` 记录机制（目录约定 + 读前/附后提示词协议 + 可选 append-only 守卫）与 Atlas **解耦**，已抽成独立 skill（本仓库 `skills/learnings`，任何 agent 可复用，不依赖 omo 插件）。机制证据见 §8。

### 3.2 Skills（内置）

> **同名实体澄清**：`comment-checker` 在 §3.5 还存在一个**同名 hook**（Session 类，拦截 AI-slop 注释的运行时执行体），与 skill 是不同实体——skill 是可被 agent 调用的能力，hook 是生命周期回调。两者均保留。

| Skill | 作用 | 动作 | 理由 |
|---|---|---|---|
| git-master | 原子提交/变基/历史检索（无模型依赖） | **留** | 高增值、无环境依赖 |
| comment-checker | 拦截 AI-slop 注释 | **留** | 高增值、无环境依赖；同名 hook 亦保留 |
| ast-grep | 25 语言结构化搜索/改写 | **留** | 中增值、无环境依赖 |
| frontend-ui-ux | 设计优先 UI | **留** | 中增值、无环境依赖 |
| review-work | 5-agent 并行 review（走普通 `task()` 子 agent，**非** team 专属） | **留** | 中增值、无环境依赖 |
| $omo:remove-ai-slops | 清 AI 味代码 | **留** | 中增值、无环境依赖 |
| init-deep | 自动生成分层 AGENTS.md | **留** | 中增值、无环境依赖 |
| playwright / playwright-cli / agent-browser / dev-browser | 浏览器自动化（MCP / CLI / Bash / 持久页四通道） | **留** | 中增值、无环境依赖 |
| frontend | UI 实现 | **留** | 中增值、无环境依赖 |
| security-research | Team Mode 驱动安全审计 | **关** | 依赖 Team Mode，本配置 team 关闭 |
| security-review | alias | **关** | 同上 |
| team-mode | team 工具技能 | **关** | 依赖 Team Mode，本配置 team 关闭 |
| hyperplan | 5 critics 对抗规划（built on Team Mode） | **关** | 依赖 Team Mode，本配置 team 关闭 |

`disabled_skills`: `["security-research","security-review","team-mode","hyperplan"]`

### 3.3 Commands（斜杠）

> **同名实体澄清**：`start-work` 在 §3.5 D 还存在一个**同名 hook**（参与 boulder.json 的 RESUME/INIT 流程），与 command 是不同实体。下面表格只针对 command；hook 是否保留见 §3.5 D。**注意**：禁用 `/start-work` 命令不影响 `start-work` hook 的运行。

| Command | 作用 | 动作 | 理由 |
|---|---|---|---|
| ralph-loop / ulw-loop / cancel-ralph | 自循环开发 | **留** | 中增值、无环境依赖 |
| refactor | LSP+AST+TDD 重构 | **留** | 中增值、无环境依赖 |
| handoff | 生成换 session 摘要 | **留** | 中增值、无环境依赖 |
| init-deep / remove-ai-slops | 生成 AGENTS / 清 AI 味 | **留** | 中增值、无环境依赖 |
| start-work | spawn prometheus 访谈 | **关** | prometheus 已关，命令失效；同名 hook 保留 |
| stop-continuation | 停循环+续接 | **关** | 急停按钮，非日常工具；配套 hook 已禁用 |
| hyperplan | 对抗规划（依赖 team） | **关** | 依赖 Team Mode，本配置 team 关闭 |

`disabled_commands`: `["stop-continuation","hyperplan","start-work"]`

### 3.4 MCPs（内置）

| MCP | 作用 | 动作 | 理由 |
|---|---|---|---|
| context7 | 库官方文档 | **留** | 高增值、无环境依赖 |
| lsp | 诊断/跳转/重命名 | **留** | 高增值、无环境依赖 |
| websearch (Exa) | 联网搜索 | **留** | 中增值、无环境依赖 |
| grep_app | GitHub 代码搜索 | **留** | 中增值、无环境依赖 |

`disabled_mcps`：无（4 个全留）。

### 3.5 Hooks（v3.x 时期 56 个，分组）

> **完整性声明**：以下 A-D 组保留的 40 个 hook + E 组屏蔽的 16 个 hook = 56 个，与 [`oh-my-openagent-architecture.md` §13.1](../research/oh-my-openagent-architecture.md#L1390-L1405) v3.x 时期整理的 56 个基础 hook 一致。v4 系列实际数量可能不同，以 `bunx oh-my-openagent doctor` 输出为准。
>
> **`thinking-block-validator` 例外**：本配置 §2.4 列出的安全类 hook 中包含 `thinking-block-validator`，但 §13.1 的 56 hook 名单中**找不到**此项，可能是 v4 新增或文档遗漏。本配置**保留**它（不进入 `disabled_hooks`），但因不在 56 个计数内，下列 A-D 组不显式列出。落地时若 doctor 报"未知 hook 名"，无需调整 `disabled_hooks`——保留项不在校验范围内。

**A. 安全/防护（8 个，全留，勿关）**：

`rules-injector`、`write-existing-file-guard`、`bash-file-read-guard`、`webfetch-redirect-guard`、`prometheus-md-only`、`tool-pair-validator`、`team-tool-gating`、`no-sisyphus-gpt`(官方标注勿关)。

> 另：`thinking-block-validator`（见上方例外说明）也属安全类、保留，但不计入 56 个名单。

**B. 上下文/压缩（5 个，留）**：

`preemptive-compaction`、`compaction-context-injector`、`compaction-todo-preserver`、`directory-agents-injector`、`directory-readme-injector`。

> `directory-agents-injector`：opencode 1.1.37+ 原生支持 AGENTS.md 后，此 hook 检测到原生支持会自动停用（避免重复注入）。当前环境 opencode 1.15.13 ≥ 1.1.37，hook 已自动停用，无需手动 disable。

**C. 稳定性/恢复（10 个，留）**：

`tool-output-truncator`、`empty-task-response-detector`、`edit-error-recovery`、`json-error-recovery`、`delegate-task-retry`、`non-interactive-env`、`interactive-bash-session`、`runtime-fallback`、`task-resume-info`、`model-fallback`(hook)。

**D. 编排/模式（17 个，留）**：

`keyword-detector`(IntentGate)、`think-mode`、`auto-slash-command`、`start-work`(同名 command 已禁用，hook 保留参与 boulder 流程)、`atlas`(同名 agent 已禁用，hook 保留参与续接)、`sisyphus-junior-notepad`、`unstable-agent-babysitter`、`todo-continuation-enforcer`、`category-skill-reminder`、`notepad-write-guard`(强制 notepad append-only)、`hephaestus-agents-md-injector`(agent 已禁用，hook 无触发场景但保留)、`codegraph-bootstrap`、`ast-grep-sg-provision`、`monitor-status-injector`、`goal`(continuation)、`comment-checker`(同名 skill 亦保留)、`plan-format-validator`。

> 注：v3.x §13.1 名单中**不存在** `ralph-loop` 这个 hook——`ralph-loop` 是 command 不是 hook，旧版文档此处有误，已删除。

**E. 屏蔽（低价值：通知/提示/兼容/环境专属，16 个）**：

`session-notification`、`background-notification`、`startup-toast`、`auto-update-checker`、`agent-usage-reminder`、`fsync-skip-warning`、`legacy-plugin-toast`、`question-label-truncator`、`claude-code-hooks`、`stop-continuation-guard`、`tasks-todowrite-disabler`、`todo-description-override`、`read-image-resizer`、`hashline-read-enhancer`、`anthropic-context-window-limit-recovery`、`no-hephaestus-non-gpt`。

```jsonc
"disabled_hooks": [
  "session-notification","background-notification","startup-toast",
  "auto-update-checker","agent-usage-reminder","fsync-skip-warning",
  "legacy-plugin-toast","question-label-truncator",
  "claude-code-hooks","stop-continuation-guard","tasks-todowrite-disabler",
  "todo-description-override","read-image-resizer","hashline-read-enhancer",
  "anthropic-context-window-limit-recovery","no-hephaestus-non-gpt"
]
```

> A–D 组共 40 个 hooks 均保留（不进入 `disabled_hooks`）。

### 3.6 其他模块

| 模块 | 默认 | 推荐 | 说明 |
|---|---|---|---|
| team_mode | 关 | 保持关 | 独立重型功能，按需开 |
| auto_update | 开 | **关** | 脚手架场景需可复现，关闭自动更新 |
| hashline_edit | 关 | 保持关 | hashline 注入争议较大，opencode 原生行号已够用 |
| new_task_system_enabled | 关 | 保持关 | 新 task 系统未稳定，沿用旧系统 |
| runtime_fallback | 关 | **开**（覆盖默认） | 防 429/5xx 自动切模型；需配合 `fallback_models` 或 category 链中备用模型 |
| claude_code.* | 开 | **全关** | opencode 原生已支持 hooks/commands/skills/agents/mcp/plugins，兼容层多余 |
| tmux / browser_automation_engine | — | 关 tmux；`browser_automation_engine` 保持默认(playwright MCP) | 其余浏览器技能按需可用 |
| monitor / openclaw / codegraph / babysitting | — | 关 | 默认即关 |

### 3.7 Team Mode 相关项（确认全屏蔽）

`team_mode.enabled: false` 是总开关：所有 team 专属 hook / 事件处理器均带条件注册门禁，关掉后根本不加载。

| 类别 | 项 | team 专属 | 屏蔽方式 | 状态 |
|---|---|---|---|---|
| Skill | `team-mode` | 是（`shouldLoad: team_mode.enabled`） | `disabled_skills` | ✅ |
| Skill | `hyperplan` | 是（built on Team Mode） | `disabled_skills` | ✅ |
| Skill | `security-research` / `security-review` | 是（Team Mode driven / alias） | `disabled_skills` | ✅ |
| Command | `/hyperplan` | 是（加载 hyperplan skill） | `disabled_commands` | ✅ |
| MCP | — | 无专属 MCP（team_* 是 ToolRegistry 工具，非 MCP） | — | 无需屏蔽 |
| Hook | `team-tool-gating` / `team-mode-status-injector` / `team-mailbox-injector` | 是（条件注册） | 主开关 `team_mode.enabled:false` | ✅ 未注册 |
| Hook | `team-idle-wake-hint` / `team-lead-orphan-handler` / `team-member-error-handler` / `team-member-status-handler` | 是（event.ts 直接处理器，条件注册） | 同上 | ✅ 未注册 |

> `team-tool-gating` 属安全类 hook（§2.4），仅在 team 开启时注册；team 关时本就不加载，**不应**列入 `disabled_hooks`。

---

## 4. 最终配置

落盘：`~/.config/opencode/oh-my-openagent.jsonc`

```jsonc
{
  // 屏蔽：hephaestus（硬性要求 GPT 家族，无 GPT 不可复活）、multimodal-looker（无图像模型）、
  // prometheus（规划评审不收敛、过度流程化）、atlas（依赖 prometheus 元数据，绑定关闭）
  // 其余 7 个 agent（sisyphus/oracle/librarian/explore/metis/momus/sisyphus-junior）保留
  "disabled_agents": ["hephaestus","multimodal-looker","prometheus","atlas"],

  // 仅屏蔽依赖 Team Mode 的 4 项；playwright 全家桶、frontend、review-work 等中高价值全留
  "disabled_skills": ["security-research","security-review","team-mode","hyperplan"],

  // 屏蔽 stop-continuation / hyperplan / start-work（prometheus 已关，start-work 无意义）
  "disabled_commands": ["stop-continuation","hyperplan","start-work"],

  // 4 个内置 MCP 全保留（context7 / lsp / websearch / grep_app）；disabled_mcps 省略

  // 仅屏蔽 16 个低价值 hook（见 §3.5 E）；其余 30+ 全保留（含 8 个安全类 hook）
  "disabled_hooks": [
    "session-notification","background-notification","startup-toast",
    "auto-update-checker","agent-usage-reminder","fsync-skip-warning",
    "legacy-plugin-toast","question-label-truncator",
    "claude-code-hooks","stop-continuation-guard","tasks-todowrite-disabler",
    "todo-description-override","read-image-resizer","hashline-read-enhancer",
    "anthropic-context-window-limit-recovery","no-hephaestus-non-gpt"
  ],

  "team_mode": { "enabled": false },
  "auto_update": false,
  "hashline_edit": false,
  "new_task_system_enabled": false,
  "runtime_fallback": true,            // 防 429/5xx 自动切模型

  // opencode 原生已支持，关掉 claude-code 兼容层
  "claude_code": {
    "mcp": false,"commands": false,"skills": false,
    "agents": false,"hooks": false,"plugins": false
  }
}
```

> **关于 `hephaestus`**：源码 `isHephaestusSupportedModel` 强制仅 GPT 家族模型可用，omo 在无 GPT provider 时会自行跳过该 agent。因此本环境无法通过「模型覆盖到非 GPT provider」复活——若要启用，须先接入 OpenAI/GPT provider 并将 `agents.hephaestus.model` 指向 `openai/gpt-5.5` 等受支持模型。

> 基座 `opencode.jsonc` 需确保 omo 插件已注册（在 `plugin` 数组加入 omo 项）。当前该文件只有 `superpowers` 插件；若 omo 未注册，先 `bunx oh-my-openagent install` 再 merge，保留自有 `provider`/`mcp`/`plugin:["superpowers…"]`。

---

## 5. 落地步骤

1. **确认 omo 插件已在 `opencode.jsonc` 注册**。若未注册：先 `bunx oh-my-openagent install`，再 merge（保留 `provider` / `mcp` / `superpowers` 插件，补 omo 插件段），勿让安装器覆盖 providers。
2. 新建 `~/.config/opencode/oh-my-openagent.jsonc`（§4 内容）。
3. 若需 `cireric-skills` 全局可用：在 `opencode.jsonc` 的 `skills.paths` 加该仓库绝对路径，或在 `~/.config/opencode/skills/` 建 symlink。
4. 把 `categories` 重映射到实际可用模型（避免 model not found）。
5. 重启 opencode。

---

## 6. 验证清单

- `opencode` 启动无配置报错；若装了 omo CLI，`doctor` 通过。
- sisyphus / oracle / librarian / explore / metis / momus / sisyphus-junior 均可见、可委托；hephaestus / multimodal-looker / prometheus / atlas 不可见。
- 内置 `git-master` / `comment-checker` / `ast-grep` / `playwright` 全家桶 / `frontend` / `review-work` / `init-deep` / `remove-ai-slops` 可用；仅 team-mode / hyperplan / security-* 不可触发。
- 斜杠命令 `ralph-loop` / `ulw-loop` / `refactor` / `handoff` / `init-deep` / `remove-ai-slops` 可用；`stop-continuation` / `hyperplan` / `start-work` 不可见。
- 4 个 MCP（context7 / lsp / websearch / grep_app）均在线。
- 触发一次长会话，验证 `preemptive-compaction` 与 `compaction-*` 压缩 hooks 生效。
- 制造一次模型错误，验证 `runtime_fallback` 自动切换。

---

## 7. 风险提醒

- **版本偏移**（v4 新增风险）：本文 §3.5 的 56 个 hook 名单基于 v3.x 整理，v4.19.4 实际数量可能不同。升级 omo 后必须重跑 `bunx oh-my-openagent doctor` 校验 `disabled_hooks` 是否仍全部存在、是否漏列新增低价值 hook。
- `disabled_hooks` 若误列了 8 个安全类 hook 之一，omo 启动会 toast 警告；以 §2.4 清单为准。
- 配置名统一用 `oh-my-openagent`，别与旧 `oh-my-opencode` 混用（旧名优先级更高会赢）。
- `runtime_fallback: true` 会在模型错误时自动切换，请确保 `fallback_models` 或 category 链中有可用备用模型，否则回退到默认。
- 升级 omo 后，复查 `disabled_*` 是否仍覆盖新增功能（omo 持续加入新 hook / skill）。
- `hephaestus` 在本无 GPT 环境下无法启用；接入 GPT provider 后方可复活（见 §4 附注）。

---

## 8. 证据来源

本文结论均可在 omo 官方仓库 `code-yeongyu/oh-my-openagent` 核验。**版本锚定**：本文档基于 v4.19.4（release tag `v4.19.4`，发布于 2026-08-01）撰写，dev 分支最新 commit `9cee074d`（2026-08-04）。下表中 PR 编号、commit hash、release tag 均为可追溯锚点。

| 结论 | 来源文件 | 锚点 |
|---|---|---|
| 功能面总览、hooks 分层、commands、MCPs 名录 | `docs/reference/features.md`、`docs/reference/configuration.md` | v4.19.4 |
| 11 个 agent 名称与作用 | `src/agents/AGENTS.md`、`src/config/schema/agent-names.ts` | v4.19.4 |
| skills 名录与说明（含 review-work、team-mode 条件加载） | `src/features/builtin-skills/AGENTS.md` | v4.19.4 |
| `disabled_*` 键与 schema（`team_mode` / `auto_update` / `runtime_fallback` / `claude_code` 等） | `packages/omo-opencode/src/config/schema/oh-my-opencode-config.ts` | v4.19.4 |
| 安全类 hooks 清单与「勿关」警告；`no-sisyphus-gpt` 勿关；`directory-agents-injector` 自动停用 | `docs/reference/configuration.md` | v4.19.4 |
| `hephaestus` 硬性要求 GPT 家族（`isHephaestusSupportedModel` + `requiresProvider`），无 GPT 时 omo 自行跳过 | `docs/guide/agent-model-matching.md`、`packages/omo-opencode/src/agents/builtin-agents/hephaestus-agent.ts` | v4.19.4 |
| `review-work` 用普通 `task()` 子 agent 并行，**非** Team Mode 专属 | `packages/shared-skills/skills/review-work/SKILL.md` | v4.19.4 |
| `team-mode` 条件加载（`shouldLoad: team_mode.enabled`）；`hyperplan` / `security-research` 依赖 Team Mode | `src/features/builtin-skills/skills/team-mode.ts`、`docs/guide/team-mode.md` | PR #3493 |
| Prometheus 写计划到 `.sisyphus/plans/*.md`、`/start-work` 建 `boulder.json`；Atlas 宽松消费计划、无严格解析器、缺 Prometheus 元数据时退化为即兴分解 | `docs/guide/orchestration.md` | PR #2602（"tighten plan contract"） |
| Atlas notepad 机制：`.omo/notepads/{plan-name}/` 分类文件、`<notepad_protocol>` 读前/附后协议、跨 task 注入 "Inherited Wisdom"、`notepad-write-guard` hook 拒绝 Write 强制 append-only、数据默认被动需主动复盘 | `docs/guide/orchestration.md`、`src/agents/atlas/gpt.ts`、`src/hooks/notepad-write-guard/index.ts`、`src/hooks/atlas/verification-reminders.ts` | commit `565d099`、PR #4082 / #3685、Issue #1364 |
| 配置名优先级 `oh-my-opencode` > `oh-my-openagent` | `README.md` | v4.19.4 |
| 两层配置与安装 merge 方式 | `docs/guide/installation.md` | v4.19.4 |
| `doctor` 最低 OpenCode 版本 `>= 1.4.0`；SDK 依赖 `@opencode-ai/plugin` + `@opencode-ai/sdk` 1.15.13 | `packages/omo-opencode/package.json`、`src/cli/commands/doctor.ts` | v4.19.4 |
| v3.x 时期 56 个 hook 完整名单（本文 §3.5 A-E 分组的来源） | [`oh-my-openagent-architecture.md` §13.1](../research/oh-my-openagent-architecture.md#L1390-L1405) | v3.x 时期整理，v4 待核 |
