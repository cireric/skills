# Agent Rules

项目级规则。全局规则见 `~/.config/opencode/AGENTS.md`，项目级规则不可削弱全局规则。
目录结构、CLI 命令、运行方式等说明见 `README.md`。

## 必做

| 规则             | 说明                                                                                                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 使用 venv Python | 所有 Python 命令用 venv Python：Linux/Mac `.venv/bin/python`，Windows `.venv\Scripts\python.exe`。禁止 bare `python`。**必须配合 `workdir=项目根目录` 使用**，确保相对路径 `.venv/` 可解析 |
| 不改 config.json | 预配置文件，运行期间修改会破坏可复现性                                                                                                                                                     |
| 依赖先查后装     | 执行 skill 脚本前，先 `pip list` 或 `import` 检查第三方库是否已安装；缺失时用 venv pip 安装                                                                                                |

## 每日聚焦提醒

每个新会话开始时，检查 `.omo/daily-focus/YYYY-MM-DD.md`（今日文件，`YYYY-MM-DD` 取系统当天日期）是否存在：

- **不存在** → 向用户提一句「今天还没做每日聚焦，要跑 `/daily-focus` 吗？」，随后**立即回到用户的原始请求**，不阻塞、不展开。
- **存在** → 静默跳过。

规则约束：只提醒一次（本次会话已提醒过则跳过）；不判断星期（周末是否做聚焦由用户决定）。

## 约定

- `conftest.py` 将 skill 目录加入 `sys.path` 以支持 import（包化 skill 改用 `pytest.ini` 的 `pythonpath`）
- skill 顶层模块名全局唯一：全局跑 test 时多个 skill 共享一个进程，同名顶层模块会被 `sys.modules` 缓存遮蔽（守卫测试 `skills/tests/test_module_names_unique.py` 把关）；顶层 `cli.py` 薄壳只作按路径执行的入口，禁止被测试 import
- 用 `tmp_path` fixture 做文件隔离，不污染工作目录
- 用 `monkeypatch` 覆盖 `_SKILL_DIR`（集成测试）
- CLI 测试直接构造 `Namespace` args，不启动子进程
- ADR supersede 维护：新 ADR 必须列出所有被取代的旧 ADR 编号；旧 ADR 只改 Status 行为 `Superseded by ADR-NNNN`，不改正文；部分 supersede 也改 Status

## 任务规划

按任务复杂度选择规划方式。详见 `docs/task-planning-workflow.md`。

核心规则：

1. grill-with-docs 不可跳过（有决策点时）— 兼具需求发现和需求对齐双重职责，术语不对齐 = 后续 skill 各说各话
2. 逐级收紧是原则而非强制 PRD — PRD 是常用方式，grill 对话结论也可作为约束源
3. 同文件 issue 串行执行 — 并行写同一文件会丢失改动；不同文件可用 worktree 隔离并行
4. 按依赖分组执行 — 独立+简单→todo，有依赖/复杂→依赖连通子图→orchestrator+TDD worker
5. 角色分离 — orchestrator 规划调度不写代码，worker 实施不规划
6. Prometheus→Atlas 为备选 — 大多数时候用 TDD worker，特别复杂 issue 可用 Prometheus→Atlas

## task-observer 激活

当加载可观察 skill 时，plugin 自动触发 task-observer 加载。无需手动激活。

新增本地 skill 时，按 3 维度评估是否加入观察列表：执行步数（多阶段/有门控=高）、合规风险（agent 有动机偷懒=高）、改进价值（有脚本/ADR 可改=高）。≥2 个维度为高 → 加入 plugin 的 OBSERVABLE_SKILLS 集合。

task-observer 观察范围：skill 文件缺陷（L1）、skill 间协作（L2）、工作流/方法论缺陷（L3）。项目经验、agent 行为、工具 quirks 归 `learnings` skill。

## 知识层级

| 位置                       | 定位                                  | 生命周期                                 |
| -------------------------- | ------------------------------------- | ---------------------------------------- |
| `AGENTS.md`                | 行为规则（必做/禁做/约定）            | 持久                                     |
| `skills/<skill>/docs/adr/` | 不可逆架构决策快照（per skill）       | 持久，可 supersede                       |
| `.omo/notepads/`           | 临时踩坑记录（learnings skill）       | 临时 — 被吸收后删除                      |
| `.omo/skill-observations/` | skill 改进观察（task-observer skill） | 临时 — 被 ACTIONED/DECLINED 并归档后清理 |
| `.omo/daily-focus/`        | 每日聚焦数据（daily-focus skill）     | 持久 — 跨天延续依赖此目录                |
| `.omo/specs/`              | specs/PRD 文档                        | 持久 — 交付物                            |

notepads 清理规则：

- 踩坑经验已写入 AGENTS.md 规则 → 删除 notepads 条目
- 踩坑已触发架构决策入 ADR → 删除 notepads 条目
- 尚未被任何规则/ADR 吸收 → 保留
- 流程缺陷尚未解决 → 保留

`.omo/` 归档规则：

项目任务完成后，`.omo/` 下仅保留 `notepads/`（未吸收的踩坑经验）、`skill-observations/`（未归档的观察记录）、`daily-focus/`（用户每日聚焦数据）和 `specs/`（specs/PRD 交付物），其余目录删除。

| 目录                  | 归档操作                                     |
| --------------------- | -------------------------------------------- |
| `notepads/`           | 保留（清理已吸收的条目后）                   |
| `skill-observations/` | 保留（归档已 ACTIONED/DECLINED 条目后）      |
| `daily-focus/`        | 保留（用户每日聚焦数据，跨天延续依赖此目录） |
| `specs/`              | 保留（specs/PRD 交付物）                     |
| `boulder.json`        | 删除（运行时进度，任务完成即失效）           |
| `drafts/`             | 删除（中间产物暂存）                         |
| `evidence/`           | 删除（QA 证据，测试通过即失效）              |
| `plans/`              | 删除（计划已完成，决策在 ADR）               |
| `run-continuation/`   | 删除（会话续接状态，会话结束即失效）         |

## Agent skills

### Issue tracker

Local Markdown — specs/PRDs in `.omo/specs/`, issues in `.scratch/<feature>/issues/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context — root `CONTEXT-MAP.md` + per-skill `CONTEXT.md`/`docs/adr/`. See `docs/agents/domain.md`.
