# 把 oh-my-openagent 当作脚手架：中高价值保留配置指南

> **场景**：已在使用 `opencode` + `oh-my-openagent`(omo)，希望把这个偏重的编排框架裁剪为「仅屏蔽低价值项、中高价值全保留」的个人全局脚手架。
>
> **策略**：以「价值指数」为唯一阈值——极高/高/中 → 保留，低 → 屏蔽。结论是一份可直接落盘的 `~/.config/opencode/oh-my-openagent.jsonc`。
>
> **证据**：本文所有功能名录、默认值、屏蔽键均来自 omo 官方 GitHub 仓库（文档 + 源码），详见文末「证据来源」。

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

- 运行时：`opencode` + `oh-my-openagent`(omo) 插件。
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

| Agent | 作用 | 价值 | 动作 |
|---|---|---|---|
| sisyphus | 主编排 agent（插件依赖） | 极高 | **留** |
| prometheus | 规划访谈（重型、评审不收敛） | 低 | **关** |
| atlas | Todo 编排执行（依赖 prometheus 元数据） | 低 | **关** |
| oracle | 架构/调试咨询 | 高 | **留** |
| librarian | 文档/代码检索 | 中高 | **留** |
| explore | 快 grep | 中高 | **留** |
| metis | plan 顾问（配 prometheus） | 中 | **留** |
| momus | 严厉 critic | 中 | **留** |
| sisyphus-junior | 轻量子 agent（分类委托） | 中 | **留** |
| hephaestus | 工程/实现，**硬性要求 GPT 家族** | 中（无 GPT→不可复活） | **关** |
| multimodal-looker | 多模态看图 | 低（无图像模型） | **关** |

`disabled_agents`: `["hephaestus","multimodal-looker","prometheus","atlas"]`

> **最终决策（已定）：关闭 `prometheus` + `atlas`。**
>
> 在「已有工程纪律 + 用 `grill-with-docs` 做需求发现、无 GPT」的场景下，二者**净收益为负**：
> - `prometheus` 是唯一产出 Atlas 结构化元数据（`Parallel Execution Graph` / `Delegation Recommendation` 等）的环节，但其规划评审循环**不收敛**——多轮审稿总能从不同角度发现问题、缺终止条件，且整体过度流程化。
> - `atlas` 的最佳表现**依赖** prometheus 的元数据契约（见 §8 证据），二者绑定：留 atlas 必留 prometheus（否则退化为即兴分解）。故同关，仅保留 `grill-with-docs` 作为规划甜点区。
>
> **收敛约束（仅当未来重启 prometheus 时需要）**：给 review 循环加终止条件——① 单一收敛权威（你手动喊停）；② 事前 DoD / 验收闸门；③ 严重度分级（仅 `blocking` 触发下一轮）；④ 轮次 / 视角预算封顶。omo 本身不提供，需手动补。
>
> **工程经验复用（notepad）剥离保留**：Atlas 的 `.omo/notepads/{scope}/` 记录机制（目录约定 + 读前/附后提示词协议 + 可选 append-only 守卫）与 Atlas **解耦**，已抽成独立 skill（本仓库 `skills/learnings`，任何 agent 可复用，不依赖 omo 插件）。机制证据见 §8。

### 3.2 Skills（内置）

| Skill | 作用 | 价值 | 动作 |
|---|---|---|---|
| git-master | 原子提交/变基/历史检索（无模型依赖） | 高 | **留** |
| comment-checker | 拦截 AI-slop 注释 | 高 | **留** |
| ast-grep | 25 语言结构化搜索/改写 | 中 | **留** |
| frontend-ui-ux | 设计优先 UI | 中 | **留** |
| review-work | 5-agent 并行 review（走普通 `task()` 子 agent，**非** team 专属） | 中 | **留** |
| $omo:remove-ai-slops | 清 AI 味代码 | 中 | **留** |
| init-deep | 自动生成分层 AGENTS.md | 中 | **留** |
| playwright / playwright-cli / agent-browser / dev-browser | 浏览器自动化（MCP / CLI / Bash / 持久页四通道） | 中 | **留** |
| frontend | UI 实现 | 中 | **留** |
| security-research | Team Mode 驱动安全审计 | 低（依赖 team） | 关 |
| security-review | alias | 低 | 关 |
| team-mode | team 工具技能 | 低（依赖 team） | 关 |
| hyperplan | 5 critics 对抗规划（built on Team Mode） | 低（依赖 team） | 关 |

`disabled_skills`: `["security-research","security-review","team-mode","hyperplan"]`

### 3.3 Commands（斜杠）

| Command | 作用 | 价值 | 动作 |
|---|---|---|---|
| start-work | spawn prometheus 访谈 | 低（prometheus 已关，inert） | 关 |
| ralph-loop / ulw-loop / cancel-ralph | 自循环开发 | 中 | **留** |
| refactor | LSP+AST+TDD 重构 | 中 | **留** |
| handoff | 生成换 session 摘要 | 中 | **留** |
| init-deep / remove-ai-slops | 生成 AGENTS / 清 AI 味 | 中 | **留** |
| stop-continuation | 停循环+续接 | 低 | 关 |
| hyperplan | 对抗规划（依赖 team） | 低 | 关 |

`disabled_commands`: `["stop-continuation","hyperplan","start-work"]`

### 3.4 MCPs（内置）

| MCP | 作用 | 价值 | 动作 |
|---|---|---|---|
| context7 | 库官方文档 | 高 | **留** |
| lsp | 诊断/跳转/重命名 | 高 | **留** |
| websearch (Exa) | 联网搜索 | 中 | **留** |
| grep_app | GitHub 代码搜索 | 中 | **留** |

`disabled_mcps`：无（4 个全留）。

### 3.5 Hooks（50+，分组）

**A. 安全/防护（全留，勿关）**：`rules-injector`、`write-existing-file-guard`、`bash-file-read-guard`、`webfetch-redirect-guard`、`prometheus-md-only`、`tool-pair-validator`、`thinking-block-validator`、`team-tool-gating`、`no-sisyphus-gpt`(官方标注勿关)。

**B. 上下文/压缩（高价值，留）**：`preemptive-compaction`、`compaction-context-injector`、`compaction-todo-preserver`、`directory-agents-injector`(注：OpenCode 1.1.37+ 原生支持 AGENTS.md 后自动停用)、`directory-readme-injector`。

**C. 稳定性/恢复（中，留）**：`tool-output-truncator`、`empty-task-response-detector`、`edit-error-recovery`、`json-error-recovery`、`delegate-task-retry`、`non-interactive-env`、`interactive-bash-session`、`runtime-fallback`、`task-resume-info`、`model-fallback`(hook)。

**D. 编排/模式（中，留）**：`keyword-detector`(IntentGate)、`think-mode`、`ralph-loop`、`auto-slash-command`、`start-work`、`atlas`、`sisyphus-junior-notepad`、`unstable-agent-babysitter`、`todo-continuation-enforcer`、`category-skill-reminder`。

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

> A–D 组共 30+ 个 hooks 均保留（不进入 `disabled_hooks`）。

### 3.6 其他模块

| 模块 | 默认 | 推荐 |
|---|---|---|
| team_mode | 关 | 保持关（独立重型功能，按需开） |
| auto_update | 开 | 关 |
| hashline_edit | 关 | 保持关 |
| new_task_system_enabled | 关 | 保持关 |
| runtime_fallback | 关 | **开**（`runtime_fallback: true`，防 429/5xx 自动切模型） |
| claude_code.* | 开 | 全关 |
| tmux / browser_automation_engine | — | 关 tmux；`browser_automation_engine` 保持默认(playwright MCP)，其余浏览器技能按需可用 |
| monitor / openclaw / codegraph / babysitting | — | 关（默认即关） |

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

- `disabled_hooks` 若误列了 8 个安全类 hook 之一，omo 启动会 toast 警告；以 §2.4 清单为准。
- 配置名统一用 `oh-my-openagent`，别与旧 `oh-my-opencode` 混用（旧名优先级更高会赢）。
- `runtime_fallback: true` 会在模型错误时自动切换，请确保 `fallback_models` 或 category 链中有可用备用模型，否则回退到默认。
- 升级 omo 后，复查 `disabled_*` 是否仍覆盖新增功能（omo 持续加入新 hook / skill）。
- `hephaestus` 在本无 GPT 环境下无法启用；接入 GPT provider 后方可复活（见 §4 附注）。

---

## 8. 证据来源

本文结论均可在 omo 官方仓库 `code-yeongyu/oh-my-openagent` 核验：

| 结论 | 来源文件 |
|---|---|
| 功能面总览、hooks 分层、commands、MCPs 名录 | `docs/reference/features.md`、`docs/reference/configuration.md` |
| 11 个 agent 名称与作用 | `src/agents/AGENTS.md`、`src/config/schema/agent-names.ts` |
| skills 名录与说明（含 review-work、team-mode 条件加载） | `src/features/builtin-skills/AGENTS.md` |
| `disabled_*` 键与 schema（`team_mode` / `auto_update` / `runtime_fallback` / `claude_code` 等） | `packages/omo-opencode/src/config/schema/oh-my-opencode-config.ts` |
| 安全类 hooks 清单与「勿关」警告；`no-sisyphus-gpt` 勿关；`directory-agents-injector` 自动停用 | `docs/reference/configuration.md` |
| `hephaestus` 硬性要求 GPT 家族（`isHephaestusSupportedModel` + `requiresProvider`），无 GPT 时 omo 自行跳过 | `docs/guide/agent-model-matching.md`、`packages/omo-opencode/src/agents/builtin-agents/hephaestus-agent.ts` |
| `review-work` 用普通 `task()` 子 agent 并行，**非** Team Mode 专属 | `packages/shared-skills/skills/review-work/SKILL.md` |
| `team-mode` 条件加载（`shouldLoad: team_mode.enabled`）；`hyperplan` / `security-research` 依赖 Team Mode | `src/features/builtin-skills/skills/team-mode.ts`、`docs/guide/team-mode.md`、PR #3493 |
| Prometheus 写计划到 `.sisyphus/plans/*.md`、`/start-work` 建 `boulder.json`；Atlas 宽松消费计划、无严格解析器、缺 Prometheus 元数据时退化为即兴分解 | `docs/guide/orchestration.md`、PR #2602（"tighten plan contract"） |
| Atlas notepad 机制：`.omo/notepads/{plan-name}/` 分类文件（learnings/issues/problems/...）、`<notepad_protocol>` 读前/附后协议、跨 task 注入 "Inherited Wisdom"、`notepad-write-guard` hook 拒绝 Write 强制 append-only、数据默认被动需主动复盘（Issue #1364） | `docs/guide/orchestration.md`、`src/agents/atlas/gpt.ts`(commit 565d099)、`src/hooks/notepad-write-guard/index.ts`(PR #4082/#3685)、`src/hooks/atlas/verification-reminders.ts`、Issue #1364 |
| 配置名优先级 `oh-my-opencode` > `oh-my-openagent` | `README.md` |
| 两层配置与安装 merge 方式 | `docs/guide/installation.md` |
