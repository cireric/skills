# Agent Rules

项目级规则。全局规则见 `~/.config/opencode/AGENTS.md`，项目级规则不可削弱全局规则。
目录结构、CLI 命令、运行方式等说明见 `README.md`。

## 必做

| 规则             | 说明                                                                                                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 使用 venv Python | 所有 Python 命令用 venv Python：Linux/Mac `.venv/bin/python`，Windows `.venv\Scripts\python.exe`。禁止 bare `python`。**必须配合 `workdir=项目根目录` 使用**，确保相对路径 `.venv/` 可解析 |
| 不改 config.json | 预配置文件，运行期间修改会破坏可复现性                                                                                                                                                     |
| 依赖先查后装     | 执行 skill 脚本前，先 `pip list` 或 `import` 检查第三方库是否已安装；缺失时用 venv pip 安装                                                                                                |

## 约定

- `conftest.py` 将 skill 目录加入 `sys.path` 以支持 import
- 用 `tmp_path` fixture 做文件隔离，不污染工作目录
- 用 `monkeypatch` 覆盖 `_SKILL_DIR`（集成测试）
- CLI 测试直接构造 `Namespace` args，不启动子进程

## 任务规划

按任务复杂度选择规划方式。详见 `docs/task-planning-workflow.md`。

核心规则：

1. grill-with-docs 不可跳过 — 术语不对齐 = 后续 skill 各说各话
2. 每层约束逐级收紧 — PRD 约束 issues，issue 的 acceptance criteria 约束执行
3. 同文件 issue 串行执行 — 并行写同一文件会丢失改动

## 知识层级

| 位置             | 定位                       | 生命周期            |
| ---------------- | -------------------------- | ------------------- |
| `AGENTS.md`      | 行为规则（必做/禁做/约定） | 持久                |
| `skills/<skill>/docs/adr/` | 不可逆架构决策快照（per skill） | 持久，可 supersede  |
| `.omo/notepads/` | 临时踩坑记录               | 临时 — 被吸收后删除 |

notepads 清理规则：

- 踩坑经验已写入 AGENTS.md 规则 → 删除 notepads 条目
- 踩坑已触发架构决策入 ADR → 删除 notepads 条目
- 尚未被任何规则/ADR 吸收 → 保留
- 流程缺陷尚未解决 → 保留

`.omo/` 归档规则：

项目任务完成后，`.omo/` 下仅保留 `notepads/`（未吸收的踩坑经验），其余目录删除。

| 目录                | 归档操作                             |
| ------------------- | ------------------------------------ |
| `notepads/`         | 保留（清理已吸收的条目后）           |
| `boulder.json`      | 删除（运行时进度，任务完成即失效）   |
| `drafts/`           | 删除（中间产物暂存）                 |
| `evidence/`         | 删除（QA 证据，测试通过即失效）      |
| `plans/`            | 删除（计划已完成，决策在 ADR）       |
| `run-continuation/` | 删除（会话续接状态，会话结束即失效） |
