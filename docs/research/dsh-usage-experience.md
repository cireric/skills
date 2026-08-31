# DeepSeek Harness（dsh）使用经验分享

> 文档性质：基于对 dsh 仓库源码、用户文档与 CLI 参考的逐条核查整理而成的一份"如何稳定使用、如何选插件"的实战经验。
> 核查基准版本：`0.1.2-alpha.2`。DSH 迭代极快，本文反映的是该时间点的现实，升级前请以最新官方文档与发布说明为准。

---

## 0. 三个必须先接受的现实

1. **DSH 是 developer preview，破坏性更新是官方承诺会发生的。**
   根目录 `README.md` 原文大写加粗写着：**"THERE WILL BE COMPATIBILITY-BREAKING CHANGES."** 这不是"可能变"，是"一定会变"。

2. **没有对外公开的"插件 ↔ DSH 版本兼容契约"。**
   核查结论：bundle 的 `package.json` 里虽然声明了 `peerDependencies`，但全部是仓库内部的 `workspace:^` 引用（见 `packages/bundle/base/package.json`、`packages/bundle/web-app/package.json`）；`dsh.bundle` / `dsh.profile` 清单里也没有任何 `dshVersion` / `apiVersion` 字段。也就是说，**当前没有一个机制让插件作者声明"我支持 DSH 的某个版本范围"**，兼容性默认全部落到使用者自己头上。

3. **它本质是"执行代码的 agent"，不是被动的库。**
   `SAFETY.md` 明确：实验性、未经安全审计、非生产级；能加载第三方插件、执行模型生成的命令、访问网络/进程/凭据/文件。沙箱和审批能"降险"，但**不能保证隔离**。

基于这三点，下面的策略核心只有一句话：

> **把 DSH 当成"随时会变的实验场"而不是"稳定平台"，用「版本冻结 + profile 隔离 + 升级自检 + 保留回滚快照」来对抗破坏性更新。**

---

## 1. DSH 的插件模型（30 秒版）

DSH 是 **everything-is-a-plugin** 架构，底层是 Cordis：

- 插件 = 一个导出 `apply(ctx)` 的模块，可选导出 `name`、`inject`（依赖）、`Config`（Schemastery 校验 schema）。
- 所有注册走 `ctx.*`（`ctx.on` / `ctx.tools.register` / `ctx.effect` 等），**插件卸载时自动清理**——这是它能支持热替换（HMR）的关键。

安装模型是 **两层概念**：

| 概念 | 是什么 | manifest 字段 |
|---|---|---|
| **bundle** | 一个 npm 包，贡献一层配置（一个 patch 文件） | `dsh.bundle.patch` → 指向 `cordis.patch.yml` |
| **profile** | `$DSH_HOME/profiles/<name>` 下的一份可运行组合 | `dsh.profile.bundles`（bundle 顺序列表）、`dsh.profile.patchReload` |

- 一个包**要么是 bundle、要么是 profile，不能两者都是**。
- 没有 `dsh.bundle` 声明的包装进来只是"普通依赖库"，不激活配置层；`dsh plugin` 会打一条 warning。

安装命令就是对 pnpm 的转发：`dsh plugin --profile <name> add/remove/update/why ...`。

---

## 2. 使用 DSH 的策略

### 2.1 冻结版本，不追 `latest`

- 安装 DSH 时锁死精确版本：`npx @deepseek-ai/dsh@0.1.2-alpha.2 ...`，不要用裸版本号 / `latest`。
- 注意上游对运行环境的约束：根 `package.json` 里 `engines.node: ^22.19.0 || >=24.0.0`、`packageManager: pnpm@11.7.0`。**升级 DSH 时往往要连 Node/pnpm 一起对版本**。
- 插件的依赖由 profile 目录下的 `pnpm-lock.yaml` 管理。**别删 lockfile**，它是你回滚的锚。

### 2.2 用 profile 隔离，杜绝"一个大杂烩"

每类用途建一个独立 profile：

```sh
dsh plugin --profile work add <工作流插件>
dsh plugin --profile tui  add github:deepseek-harness/turtle-ui   # git 安装会触发 allowBuilds，见 §3.2
dsh --profile work
```

好处：**一个坏插件只拖垮它所在的 profile**；要做实验就新建 profile，坏了直接弃用，不影响其他用途。

### 2.3 升级前：先自检，再换，留后路

有效配置是**分层叠加**的（后者逐行覆盖前者，且 patch 是**整行替换配置、不深合并**）：

1. base bundle（`@deepseek-ai/dsh-base`）
2. 你按顺序装进去的每个插件 bundle
3. profile 自己的 `cordis.patch.yml`
4. 机器级 `$DSH_HOME/cordis.patch.yml`
5. `--patch` 命令行 overlay（按 argv 顺序）

升级后的**不启动（不 boot）的自检**工具：

```sh
dsh --profile <name> --dump-config          # 含 profile/home/--patch 层
dsh --profile <name> --dump-default-config  # 只看 bundle 层
```

- 它会打印完整组合树，并用注释标出**每一行来自哪个文件、被哪个 overlay 改过**；
- 配置解析（parse）、schema 校验、模块解析（resolution）、插件启动（boot）任一失败都会非零退出——**升级后先跑一次，就能看出组合树是否还解析得动；失配的 overlay 目标（unmatched）会报告到 stderr**；
- 注意：dump 会把缺失的 profile 文件**初始化写盘**（并非完全无副作用），但绝不 boot、也不执行应用命令行 provider。

回滚路径比"原地降级"可靠：**保留「旧 DSH 版本 + 旧 profile + lockfile」三者一起的快照**，坏了切回旧 profile，而不是在一套东西上反复折腾。

### 2.4 认清两个"生效边界"

| 操作 | 生效时机 |
|---|---|
| `dsh plugin add/remove/update`（bundle 成员变更） | **重启 profile 才生效** |
| 编辑 `cordis.patch.yml`（profile / home 两层） | **默认 live 热重载** |

混淆这两者会误判"我改了为什么没生效"。自定义 profile 的 `patchReload` 默认是 `live`，可显式改为 `startup`（一次加载）。

### 2.5 能力上"内置优先，按需引入"

`dsh-base` 已内置几乎全套能力（会话/agent loop、subagent 与 workflow、goal、plan-mode、todo、沙箱、bash/pwsh、文件系统、`web_search`/`web_fetch`、skill 等，见 `apps/cli/composition.md`）。**能用内置就别上第三方**；确需扩展（如 Codex/Claude Code subagent provider、turtle-ui）才按需装，并放独立 profile。

```sh
dsh plugin --profile <name> add @deepseek-ai/dsh-subagent-codex
dsh plugin --profile <name> add @deepseek-ai/dsh-subagent-claude-code
```

---

## 3. 如何选择 DSH 插件

### 3.1 来源：官方 / 熟人优先，git 安装必须 pin 到 commit

- 首选 `@deepseek-ai/*` 官方包，或 README 提到的、打了 `dsh-plugin` topic 的知名仓库。
- **git 安装（`github:you/plugin`）一定要写成 `github:you/plugin#<sha>`**。文档明确警告：git 安装取的是**源码**而非构建产物，后续 push 会"静默改变装机时要执行的代码"。

### 3.2 安装方式：优先已构建产物，而非 git 源码

这是最容易踩的安全点：

- git 源码安装会触发包的 `prepare` 构建脚本——**等于在 agent 沙箱之外执行该包的代码**，pnpm ≥10 会要求你在 profile 的 `pnpm-workspace.yaml` 里 `allowBuilds` 白名单它后才放行。
- 把那条 `allowBuilds` 理解成：**"我授权该包在安装时跑任意代码"**。只对你看过源码、信任的包这么干。
- **npm 已构建产物（`dsh plugin add 你的包`）或 `pnpm pack` 出来的 tarball 不需要任何构建授权**。对不熟悉的插件，优先级：npm 构建产物 > tarball > git 源码。

### 3.3 看耦合度：是否 import 了 DSH 内部包

这是"大多数插件某天会坏"的根因：

- 好插件只依赖**相对稳定的 `@deepseek-ai/cordis` 插件框架契约**（`apply` / `inject` / `ctx.*`）。
- 差插件会直接 import 内部 `@deepseek-ai/dsh-*` 包、依赖某个 `ctx.llm`/`ctx.tools`/`ctx.session` 的精确 service 形态、或覆盖 base 的内部行——**这些精确形态正是破坏性更新的主要变化源，几乎必挂**。

排查手段：

```sh
dsh plugin --profile <name> why <包名>   # 看依赖树
```

再翻它的 `cordis.patch.yml`，看它覆盖了哪些 row id、有没有动 base 的关键行。

### 3.4 看它是否按 DSH 的设计原则写

下面是"好插件信号"，都能让它随 DSH 演进、热重载更稳：

- 导出 Schemastery `Config` schema（可配置、失败即 loud fail），而不是硬编码魔法值；
- 用 `inject: ['tools','llm', ...]` 显式声明依赖，不靠隐式全局；
- 注册全走 `ctx.on` / `ctx.tools.register` / `ctx.effect`（自动清理、支持 HMR），不自己留 `setInterval` 忘清理；
- 覆盖 base 行时会 **restate 那一行的全部 key**，而非只写要改的 key（因为 patch 是整行替换）。

### 3.5 看影响面：越窄越稳

插件做得越单一、覆盖的行越少，越容易跟着 dsh 更新存活；"大而全"、猛改 base 组合的插件最容易一次性全崩。用 `--dump-config` 的 overlay 注释，能直接量出它动了哪些行。

### 3.6 看活跃度：跟不跟得上 dsh 的节奏

看它最近 commit、README/发布说明是否写明适配的 dsh 版本（机制上目前没有 manifest 字段可声明，只能靠文档口述）、issue 里有没有"升级 dsh 后就坏了"的反馈。明显落后于 dsh 版本节奏、久未维护的插件，即使现在能跑，下次破坏性更新大概率它先倒。

---

## 4. 现在就能做的清单

- [ ] 不用 `latest`，锁死 DSH 精确版本，并对牢 Node/pnpm 版本。
- [ ] 每个用途独立 profile，保留 `pnpm-lock.yaml`。
- [ ] 新插件优先 `@deepseek-ai/*` 或已构建产物；git 装就 pin sha；只在信任代码时给 `allowBuilds`。
- [ ] 升级前 `--dump-config` 自检，留好「旧 DSH + 旧 profile + lockfile」回滚快照。
- [ ] 记住：bundle 增删改要重启；`cordis.patch.yml` 编辑热重载。
- [ ] 优先内置能力，第三方插件按需、按最小影响面引入。
- [ ] 重要机器优先跑在一次性 VM / 容器里，给最小权限，并备份可访问文件（`SAFETY.md` 建议）。

---

## 5. 常用命令速查

| 命令 | 用途 |
|---|---|
| `npx @deepseek-ai/dsh@<精确版本> web` | 精确版本启动 Web UI（`web` 是 `--profile web` 别名） |
| `dsh --profile <name>` | 启动指定 profile |
| `dsh plugin --profile <name> add <pkg-or-git-spec>` | 安装插件（转发 pnpm，可用 pnpm 版本语法） |
| `dsh plugin --profile <name> remove <pkg>` | 移除插件 |
| `dsh plugin --profile <name> update <pkg>` | 更新插件 |
| `dsh plugin --profile <name> why <pkg>` | 查看插件依赖树 |
| `dsh --profile <name> --dump-config` | 不 boot 地打印完整组合树（含所有 overlay + 逐行来源注释；会初始化缺失的 profile 文件） |
| `dsh --profile <name> --dump-default-config` | 只看 bundle 层组合 |

---

## 6. 本文核查依据（源码路径）

- 版本与状态：`package.json`、`README.md`（"Developer preview"）、`SAFETY.md`
- 插件/组合模型与安装：`docs/user/develop/basic/publish.md`、`docs/user/develop/basic/config.md`
- 插件生命周期 / HMR 设计：`docs/user/develop/framework/index.md`
- CLI 行为、层序、dump-config、生效边界、subagent bundle：`apps/cli/reference/README.md`
- `dsh plugin` 实现（pnpm 转发 + bundle 对账）：`apps/cli/src/plugin.ts`
- 内置能力清单：`apps/cli/composition.md`
- "无对外版本兼容契约"结论依据：`packages/bundle/base/package.json`、`packages/bundle/web-app/package.json`（peerDependencies 全为内部 `workspace:^`）

---

## 7. 一句话总结

> 用「版本冻结 + profile 隔离 + `--dump-config` 升级自检 + 旧版本/旧 profile/lockfile 三件套回滚」对抗破坏性更新；选插件用「官方/可信来源、已构建产物、窄耦合、窄影响面、活跃维护」五条卡——这能显著降低"某天突然用不了"的概率。

> ⚠️ 再次提醒：本文基于 `0.1.2-alpha.2` 核查，DSH 变更极快，正式采用前请以最新官方文档（`docs/` 与 `apps/cli/reference/README.md`）和 GitHub 发布说明为准。