# learnings — 需求与设计文档

> 本文基于与用户的对话产出：从 oh-my-openagent (omo) 的 Atlas `notepads` 系统出发，
> 验证其实现机制，得出"机制与 Atlas 解耦、可独立剥离"的结论，并据此设计了一个
> **不依赖 omo 插件、任何 agent 可复用**的 `learnings` skill。
>
> 配套实现：`skills/learnings/SKILL.md`、`skills/learnings/scripts/learnings.py`、
> `skills/learnings/tests/test_learnings.py`。

---

## 1. 背景与目标

### 1.1 来源

omo 的 `atlas` agent 在执行计划时会把工程经验写入 `.omo/notepads/{plan-name}/` 下的
分类 markdown 文件，并在每次委派子 agent 前读回、作为 "Inherited Wisdom" 注入。
用户在实际使用中认可其**跨 session / 跨 agent 复用工程经验、避免重复踩坑**的价值。

### 1.2 动机

在对 omo 做"中高价值保留"裁剪时，用户决定**关闭 `prometheus` + `atlas`**（规划评审不收敛、
过度流程化、二者绑定、净收益为负）。但 notepad 这套经验复用思路被判定为**最高价值之一**，
值得保留——于是产生需求：**把 notepad 机制从 Atlas 中剥离，做成独立 skill**。

### 1.3 目标

- 复用 omo notepad 的"目录约定 + 读前/附后协议"范式，但**不依赖 omo 插件**。
- 任何 agent（不限于 omo）都能 `retrieve` 历史经验、`capture` 新踩坑。
- 经验可跨 session 持久化，并能在用户主导下**升级为永久规则**（AGENTS.md / 技能）。

---

## 2. 调研：omo notepad 机制（实证）

以下结论均来自 omo 官方仓库 `code-yeongyu/oh-my-openagent` 的源码 / 文档（见 §7）。

### 2.1 存储结构（落盘即持久化）

```
.omo/notepads/{plan-name}/
  learnings.md    # 约定、模式、成功做法
  decisions.md    # 架构选择与理由
  issues.md       # 踩过的坑、blocker、gotcha
  verification.md # 测试结果、验证结论
  problems.md     # 未解决问题、技术债
```

分类文件 append-only；经验靠文件落盘跨 session 存活。

### 2.2 写入触发（谁写、怎么写）

- **无专用 notepad 工具**：omo 工具注册表中没有 notepad tool，实际写入就是 agent 用普通
  `Edit`/`Write` 往 `.omo/notepads/{plan-name}/*.md` 追加。
- 触发靠 **Atlas 系统提示词里的 `<notepad_protocol>` 协议块**（commit `565d099`）：
  - **每次委派前**：`Glob(".omo/notepads/{plan-name}/*.md")` → `Read` 各分类 → 抽取相关经验，
    作为 "Inherited Wisdom" 注入子 agent prompt。
  - **每次完成后**：指令子 agent **append** 发现，格式 `## [TIMESTAMP] Task: {task-id}\n{content}`。
- `start-work` hook（`/start-work` 命令）负责初始化目录与分类文件、把 session 切到 Atlas。
- `src/hooks/atlas/verification-reminders.ts` 的 STEP 5 也会读子 agent 写回的 learnings/issues/problems，
  用于指导下一次委派、调整计划、传播经验。

### 2.3 跨 session / task 复用（怎么读回去）

- 复用完全靠**文件落盘 + Atlas 协议里的"委派前全局读"**。经验不是自动 RAG 检索，
  而是 Atlas 在每次委派时把整个 notepad 目录读进来、手工挑相关条目注入子 agent prompt。
- **数据默认是被动的**（Issue #1364 "Session Debrief"）：若没有 agent 去读，经验就沉睡。
  #1364 提议的"原生复盘"功能（计划完成后自动把 friction/分辨率 upcycle 进 AGENTS.md/Skills）
  被合并进 RFC #1397，**并非开箱默认行为**。

### 2.4 append-only 保护（notepad-write-guard hook）

- `notepad-write-guard`（`src/hooks/notepad-write-guard/index.ts`，PR #4082 / #3685）：
  在 `tool.execute.before` 阶段，若工具是 `Write` 且路径命中 `.omo/notepads/**`（及旧
  `.sisyphus/notepads/**`），**直接抛错拒绝**——Write 会覆盖、破坏历史；Edit（追加）允许。
- **Windows 绕过漏洞（commit `7cce0ad` 修复）**：最初用 POSIX 子串匹配，Windows 路径归一化后
  可绕过；修复后用 `normalize() + sep` 并同时覆盖 `.omo` 与 `.sisyphus` 两个根。
  → 自实现时必须用平台无关的路径匹配。

### 2.5 关键结论：机制与 Atlas 解耦

notepad **不是** Atlas 的私有能力，而是"文件 + 提示词纪律"。Atlas 只是遵守 `<notepad_protocol>`
协议的角色。换成自己写的 skill / AGENTS.md 指令，效果等价——这是能剥离的根本原因。

---

## 3. 需求

### 3.1 功能需求（FR）

| 编号 | 需求 | 说明 |
|---|---|---|
| FR-1 | **初始化 scope** | 为某 scope（项目/子系统）创建分类文件（learnings/decisions/issues/problems/verification）。 |
| FR-2 | **Retrieve（任务前读回）** | 按 scope（及可选 category / topic）读取 notepad，供 agent 注入 "Inherited Wisdom"。 |
| FR-3 | **Capture（任务中记录）** | 把踩坑 / 成功模式 append 到对应分类文件；append-only，绝不覆盖历史。 |
| FR-4 | **Debrief（复盘提案）** | 扫描 notepad，输出"重复关键词 + 升级建议"的**提案**。 |

### 3.2 非功能需求（NFR）

| 编号 | 需求 | 说明 |
|---|---|---|
| NFR-1 | **与 omo 解耦** | 不依赖 omo 插件、Atlas、prometheus，纯 stdlib 脚本 + 提示词。 |
| NFR-2 | **跨 agent 复用** | 任何 agent（含非 omo）可读写同一份 `.omo/notepads/`。 |
| NFR-3 | **可测试** | 脚本子命令确定性、可 pytest 覆盖（append-only、检索过滤、debrief 不写 AGENTS.md）。 |
| NFR-4 | **平台无关** | 路径处理用 `pathlib` + `normalize()/sep`，兼容 Windows（吸取 omo 的绕过坑）。 |

### 3.3 约束（用户明确）

| 编号 | 约束 | 来源 |
|---|---|---|
| C-1 | **绝不自动编辑 `AGENTS.md`**。`debrief` 只打印提案，升级动作由用户执行。 | 用户：单次踩坑不应让 agent 自作主张写规则。 |
| C-2 | **Upcycle 用户主动触发**，且须**多次踩坑上升到规则**后才总结进 `AGENTS.md`。 | 用户：避免噪音规则。 |
| C-3 | **Retrieve 在任务开始前**，不是踩完坑再补。 | 经验复用才有意义。 |
| C-4 | 目录命名用稳定 scope（项目/子系统），不用一次性 task id。 | 复用面最大化。 |

---

## 4. 设计

### 4.1 目录约定

```
.omo/notepads/{scope}/
  learnings.md    # 成功模式、约定
  decisions.md    # 架构选择
  issues.md       # 踩坑、blocker、gotcha
  problems.md     # 未解决、技术债
  verification.md # 验证结论
```

`{scope}` 取稳定标识（如项目名或子系统名）。可用环境变量 `LEARNINGS_ROOT` 覆盖根目录（便于测试）。

### 4.2 三阶段流程

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Retrieve    │ → │ Capture     │ → │ Upcycle     │
│ (任务前读)  │   │ (踩坑时记)  │   │ (用户主动)  │
└─────────────┘   └─────────────┘   └─────────────┘
  注入 Wisdom        append-only       仅提案,不写AGENTS.md
```

- **Retrieve**：`learnings.py retrieve --scope X [--category Y] [--topic KW]`。
- **Capture**：`learnings.py capture --scope X --category Y --task-id Z --content "..."`（追加）。
- **Upcycle**：`learnings.py debrief --scope X` → 打印提案；仅当用户要求且坑复现 ≥2 次，
  由用户手动升为 AGENTS.md 规则。

### 4.3 脚本设计（scripts/learnings.py）

| 子命令 | 参数 | 行为 |
|---|---|---|
| `init` | `--scope` | 创建 5 个分类文件（不存在才建）。 |
| `retrieve` | `--scope [--category] [--topic]` | glob + 读，按 topic 过滤，输出供 agent 注入。 |
| `capture` | `--scope --category --task-id --content` | 以 `"a"` 模式追加 `## [时间] Task: id\n内容`，绝不截断。 |
| `debrief` | `--scope` | 统计条目、提取复现关键词、打印**提案**；不写 AGENTS.md。 |

关键实现点：
- **append-only**：`capture` 用 `open(p, "a")`，且 SKILL.md 明令禁止对 notepad 用 `Write`。
- **drive-safe 相对路径**：`os.path.relpath` 在跨盘（如 cwd=D:、tmp=C:）会抛 `ValueError`；
  改用 `Path.resolve().relative_to(root.resolve())` 并捕获 `ValueError` 回退绝对路径（`_display()`）。
- **debrief 不写 AGENTS.md**：函数只 `print` 提案，test 断言 `AGENTS.md` 不被创建。

### 4.4 纪律红线（bulletproofing，见 SKILL.md）

- 禁止对 notepad 用 `Write`（破坏历史）→ 一律走 `capture`。
- Retrieve 必须在任务开始前。
- 禁止 agent 自写 `AGENTS.md` → debrief 仅提案。
- 单次踩坑不升级为规则 → 等复现。
- scope 用稳定标识，不用临时 task id。

### 4.5 测试策略（TDD：RED → GREEN → REFACTOR）

- **RED（基线）**：无 skill 时 agent 不记录、不读历史、不升级 → 经验随 session 蒸发
  （对应 omo Issue #1364 的"数据被动"）。
- **GREEN（脚本 + 纪律）**：用 pytest 覆盖三条核心不变量：
  1. `capture` 二次调用是**追加**而非覆盖（历史保留）；
  2. `retrieve --topic` 正确过滤（相关才注入）；
  3. `debrief` 后 `AGENTS.md` **不存在**（不越权写规则）。
- 当前 `tests/test_learnings.py`：**3 passed**。

---

## 5. 与 prometheus / atlas 的关系

- `prometheus`/`atlas` 已在 `reports/omo-scaffold-minimal-config-guide.md` 中判定为**关**
  （加入 `disabled_agents` / `disabled_commands` 含 `start-work`）。
- notepad 经验复用**不依赖**二者，故剥离后独立存活于 `learnings` skill。
- 即：关闭重型编排，但保留其最有价值的"经验资产化"能力——与"grill-with-docs 单独是规划甜点区"
  的结论自洽。

---

## 6. 验收标准

- [ ] `init` 为给定 scope 生成 5 个分类文件。
- [ ] `capture` 多次调用追加、不覆盖（历史完整）。
- [ ] `retrieve --topic` 只返回相关条目。
- [ ] `debrief` 输出提案，且全程不创建/不修改 `AGENTS.md`。
- [ ] pytest 全绿（3 passed）。
- [ ] 任何 agent 在 cwd 下运行脚本即可读写同一份 `.omo/notepads/`，无需 omo。

---

## 7. 证据来源

| 结论 | omo 来源 |
|---|---|
| notepad 分类文件结构与 `<notepad_protocol>` 读前/附后协议 | `docs/guide/orchestration.md`、`src/agents/atlas/gpt.ts`（commit `565d099`） |
| 无专用 notepad 工具，靠 Edit/Write + 协议写入 | `src/tools/AGENTS.md`（13 个工具目录无 notepad） |
| `notepad-write-guard` 拒绝 Write、强制 append-only | `src/hooks/notepad-write-guard/index.ts`（PR #4082 / #3685） |
| Windows 路径绕过漏洞与修复（`normalize()+sep`，覆盖 `.omo`/`.sisyphus`） | commit `7cce0ad` |
| 数据默认被动、需主动复盘（debrief/upcycle 非默认） | Issue #1364 "Session Debrief"（合并入 RFC #1397） |
| verification-reminders STEP 5 读回 notepad 指导下次委派 | `src/hooks/atlas/verification-reminders.ts` |
| Atlas 依赖 prometheus 元数据、二者绑定 → 同关 | `docs/guide/orchestration.md`、PR #2602（见 `omo-scaffold-minimal-config-guide.md` §8） |
