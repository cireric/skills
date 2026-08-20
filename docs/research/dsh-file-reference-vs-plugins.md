# DSH rc.8 官方 @file 功能如何"摧毁"dsh-at-file 类插件

> 调研日期：本会话。官方侧以本地 checkout 为**一手来源**（`D:\Project\source\__TEST__\deepseek-harness`，恰为 `dsh-v0.1.0-rc.8` tag）；插件侧因沙箱无法抓取 raw README 正文，以 GitHub 仓库元数据 + 多轮检索为准，推断处已标注。插件侧原始记录见 `dsh-at-file-research.md`。

## 0. 结论速览

1. **官方 rc.8 内置了 `@file`**：一个三包 seam（`dsh-file-reference` 契约 + `dsh-file-reference-local` 宿主实现 + `dsh-client-ui-reference` Web UI），Web 输入框键入 `@` 即可搜索工作区文件并插入路径 mention。官方 Web bundle 默认挂载，**零安装开箱即用**。
2. **官方版故意不附加文件内容**：候选只含路径；模型看到的是"`@` 前缀路径 = 用户显式引用的文件，需要内容请调 `read`"。这是设计决策——官方明确否决了"选中即附加内容"的方案（上下文浪费 + 绕过可审计的 read 调用链）。
3. **dsh-at-file 的定位**（按仓库描述）："Codex-style @file mentions for DeepSeek Harness: search workspace files in the composer **and attach their contents to prompts**"——即"搜索 + 把**内容**附加进 prompt"。
4. **"失去意义"是部分成立、部分不成立**：
   - 成立的部分：**发现/交互层**（键入 @、搜索工作区、菜单选择）被官方完全吸收且默认内置，插件在这一层的存在价值归零。
   - 不成立/需注意的部分：官方版**不做内容附加**，所以插件描述的"attach contents"差异化点官方**没有**覆盖——但官方用设计理由（token 浪费、绕过 read 审计）把它变成了"平台不认同的行为"，插件继续做这件事等于逆着平台方向，受众急剧萎缩。
5. 用户给出的 `omdsh-dev/dsh-at-file` 地址**无法证实存在**；检索确认的是 `FSMargoo/dsh-at-file`。omdsh-dev 组织本身存在（dsh-hub / dsh-office / dsh_workflow 等），但该组织名下未发现 dsh-at-file。

---

## 1. 官方 rc.8 @file 到底做了什么（一手来源）

### 1.1 结构：三包 seam

| 包 | 角色 | 关键内容 |
|---|---|---|
| `@deepseek-ai/dsh-file-reference` | 契约/seam | `ctx.fileReferences.list(agent, query, signal)` 返回**仅含路径**的候选；浏览器安全语法 `activeAtToken()` / `formatFileMention()`；`FILE_REFERENCE_PROMPT` 模型指引；一元 Remote `fileReferences/list` |
| `@deepseek-ai/dsh-file-reference-local` | 宿主实现 | 每 agent 一个有界 `WorkspaceFileSearch`（根 = 会话 cwd，缺省回退进程 cwd）；`/` 查询直接列目录，裸查询走有界递归模糊索引；不跟随目录 symlink；工具结果事件使索引失效；`read` 可见时安装提示词段 |
| `@deepseek-ai/dsh-client-ui-reference` | Web UI source | 合并 `@file` + `@session` 菜单：并行发起 `fileReferences/list` 与 `sessionReferenceResolver/candidates`，文件排前、会话排后；未闭合的 `@"…` 只搜文件；失败独立降级 |

官方 web bundle（`packages/bundle/web-app/cordis.patch.yml`）默认挂载 `file-reference-local`、`ui-input-trigger`、`ui-commands`、`ui-skill`、`ui-subagent`、`ui-reference`——**即 `dsh --profile web` 开箱即有 @file**。

### 1.2 语法（`packages/context/file-reference/src/grammar.ts`）

- 仅识别**输入开头或空白后**的 `@path` 或未闭合的 `@"path with spaces`（避免邮件地址误触发）。
- 文件 = 原子行内引用（文件图标 + 业务色文件名）；目录 = 可编辑路径文本 + 文件夹图标，尾部斜杠后继续补全下一层。
- 序列化形式就是 `@path` 纯文本。

### 1.3 关键设计：path-only，不附加内容

包 README 原文（`packages/context/file-reference/README.md`）：

> "Selecting a candidate does not read or attach file contents."
> "**No file-content reference object** — selected files remain ordinary prompt text and require an explicit model tool call before their contents become model-visible."

模型指引（`FILE_REFERENCE_PROMPT`，`read` 可见时注入系统提示词）：

> "Paths prefixed with @ are files explicitly referenced by the user. Use the read tool when their contents are needed; do not claim to have inspected a file before reading it."

Agent Note（`2026-07-27-web-file-and-session-references.md`）的 Alternatives considered 明确记录否决理由：

> "**Eagerly attach selected file contents.** Rejected because selection would spend context before relevance is known and bypass the logged, auditable `read` call/result sequence."

### 1.4 配套：产物文件链接 + 行内代码提及

- `2026-07-31-web-workspace-file-links`：轮次结束的"产物文件行"，点路径用宿主默认浏览器打开。
- `2026-08-07-web-inline-file-mentions`：模型收尾消息里 `\`path\`` 行内代码若命中本轮成功写入的路径 → 可点击打开；提示词指引模型"用精确路径把变更文件写成行内代码"。

### 1.5 与当前 GUI 的关系

本会话（DeepSeek Harness Web GUI）的系统提示词即包含官方 rc.8 的 `FILE_REFERENCE_PROMPT` 原句（"Paths prefixed with @ are files explicitly referenced by the user…"）——说明当前运行的正是 rc.8 组合，@file 能力在线上生效。当前工作区规则里 `@` 前缀文件引用（本会话系统提示词、`@read` 语义）即此特性。

---

## 2. dsh-at-file 是什么（基于仓库元数据，README 正文未读到）

- 仓库：**FSMargoo/dsh-at-file**（确认存在）——描述原文：*"Codex-style @file mentions for DeepSeek Harness: search workspace files in the composer and attach their contents to prompts."*
- 核心功能（由描述推断）：
  1. composer 键入 `@` 触发 Codex 风格文件提及；
  2. 搜索当前工作区文件并给出选择/补全；
  3. **把文件"内容"附加到 prompt**（而非仅路径）。
- 发布：GitHub + npm（`@freespace8/dsh-at-file`，发布者与仓库作者关系未确认）。
- 目标 DSH 版本 / 使用 API：无直接证据；按 DSH 插件体系（Cordis client plugin + 宿主服务）推断为 client plugin。
- 作者对被内置取代的表态：**未找到任何**（superseded/deprecated/archived 等检索均无命中）。
- `omdsh-dev/dsh-at-file`：**未发现存在证据**；omdsh-dev 组织真实存在（dsh-hub、dsh-office、dsh_workflow、DSH-better-sidebar、dsh-drag-and-drop）。

同类生态（可能同样受官方 @file 影响）：`zhxqc/dsh-oh-my-theme`（含 @file mentions）、`SIMON-WORLD/dsh-toolkit`（含 @文件引用）、`HongMing-Huang/dsh-file-upload`、`chengzhi43/dsh-file`、`re-ITRT/dsh-file-fix`、`loudMore/dsh-drop-to-path` 等。

---

## 3. 对比：官方摧毁了什么、没摧毁什么

| 维度 | dsh-at-file（按描述） | 官方 rc.8 @file | 结论 |
|---|---|---|---|
| composer 内 `@` 触发 | ✅ | ✅（默认内置） | **插件此层被吸收** |
| 工作区文件搜索/补全 | ✅ | ✅（有界模糊索引，工具结果失效） | **插件此层被吸收** |
| 文件菜单/选择交互 | ✅ | ✅（文件+会话合并菜单，更全） | **插件此层被吸收且更强** |
| 附加**文件内容**进 prompt | ✅（差异化核心） | ❌ 刻意不做（path-only + read 指引） | **官方未覆盖，但平台不认同** |
| 模型侧语义 | 插件自说自话 | 官方提示词定义了 `@` 语义（read 可见时） | 平台定义语义后，插件行为易与官方语义冲突/重复 |
| 安装/维护 | 需安装、跟随 rc 迭代 | 零安装、随 rc.8 发布 | 生态位被默认值取代 |

**核心洞察**：官方吸收的是"@ 文件提及的**交互与发现**"，并刻意留下"**内容附加**"作为空白——但这不是留给插件的机会，而是官方判定该行为不值得做（上下文浪费 + 绕过可审计的 `read` 调用链）。插件若继续主打"附加内容"，等于逆平台设计方向：能用，但用户默认不再需要，且模型行为预期被官方指引改写。

---

## 4. 一般规律：官方功能如何"摧毁"已有插件

1. **吸收循环**：平台 rc 期插件是需求探针——社区最热插件（@file、主题、多模态输入、文件上传）证明用户想要什么；官方随后把高价值者以**更深实现**收编进核心（seam 化、Remote 契约、KV-cache 感知、审计链、默认挂载）。
2. **默认值即生态位**：官方版默认在 web profile 里，插件从"装了才有"变成"不装也有"，安装动机消失；插件能留存的只有官方**刻意不做**的部分。
3. **语义所有权**：官方提示词段定义 `@` 的含义后，第三方插件的同类语法要么重复、要么冲突、要么被模型指引覆盖——第三方无法再拥有"语法语义"。
4. **插件存活策略**（从本案例推导）：
   - 差异化必须落在官方**明确否决**的能力上（如内容附加），且要能说服用户"官方不做是因为保守，我的场景值得"——小众但真实；
   - 或成为官方 seam 的**新 provider**（`ctx.fileReferences` 是 seam，提供方负责命名空间/排序——例如远程/虚拟命名空间、gitignore 语义、不同排名策略），搭平台的车而非对着干；
   - 或转向官方尚未吸收的相邻能力（如文件上传/文档转 Markdown、拖拽到路径、侧边栏工作台——这些目前仍是社区空间）。
5. **对插件作者的警示**：在 rc 期为主流交互写插件 = 短期流量、长期被收编；写"官方设计理由明确拒绝的行为"= 守住差异化但对抗默认值；写 seam 的 provider = 与平台共生。

---

## 5. 来源

**官方一手（本地 checkout @ dsh-v0.1.0-rc.8）**
- `packages/context/file-reference/README(.zh).md`、`src/grammar.ts`、`src/index.ts`、`src/types.ts`
- `packages/context/file-reference-local/README(.zh).md`、`src/index.ts`、`src/search.ts`
- `packages/client/ui-reference/README(.zh).md`、`src/client/index.ts`
- `packages/client/ui-input-trigger/README.md`、`src/core/detect.ts`
- `packages/bundle/web-app/cordis.patch.yml`
- `.agents/notes/implemented/feature/2026-07-27-web-file-and-session-references(.zh).md`
- `.agents/notes/implemented/feature/2026-07-31-web-workspace-file-links.md`
- `.agents/notes/implemented/feature/2026-08-07-web-inline-file-mentions(.zh).md`
- `docs/capability-seams.md`（`ctx.fileReferences` 行）

**插件/生态（web 检索，正文未直接读取）**
- https://github.com/FSMargoo/dsh-at-file
- https://www.npmjs.com/package/@deepseek-ai/dsh-file-reference
- https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.0-rc.8
- https://github.com/omdsh-dev/dsh-hub（omdsh-dev 组织存在性佐证）
- https://github.com/zhxqc/dsh-oh-my-theme 、https://github.com/SIMON-WORLD/dsh-toolkit 、https://github.com/HongMing-Huang/dsh-file-upload
- 插件侧完整记录：`dsh-at-file-research.md`（含链接清单）
