# learnings — 实施计划

> 配套文档：`skills/learnings/docs/requirements-design.md`（需求设计）。
> 本文给出落地步骤与状态。代码已先行实现（TDD GREEN），本文同时作为"已完成 / 待办"的收尾与推广计划。

---

## 1. 范围

把 omo Atlas 的 `.omo/notepads/` 经验复用机制，剥离为**独立、不依赖 omo**的 `learnings` skill：
- 已实现：调研 → 决策 → 脚本 → SKILL.md → 测试。
- 待办：部署（git）、接入 AGENTS.md、名称确认、可选增强（自动触发 / append-only 守卫 hook）。

---

## 2. 实施步骤（带状态）

### Phase 1 — 机制调研 ✅ 已完成

| 步骤 | 内容 | 产出 |
|---|---|---|
| 1.1 | 检索 omo 仓库 notepad 实现（存储 / 写入 / 复用 / 守卫） | 实证结论（见需求文档 §2、§7） |
| 1.2 | 验证"机制与 Atlas 解耦" | 得出可独立剥离结论 |

### Phase 2 — 裁剪决策 ✅ 已完成

| 步骤 | 内容 | 产出 |
|---|---|---|
| 2.1 | 评估 prometheus/atlas 价值（不收敛、过度流程化、绑定） | 决定关闭二者 |
| 2.2 | 保留 notepad 思路并定为高价值 | 决定抽成独立 skill |
| 2.3 | 更新 `reports/omo-scaffold-minimal-config-guide.md` | prometheus/atlas 标"关"、加入 disabled 列表、补收敛约束与 notepad 指向 |

### Phase 3 — 脚本实现 ✅ 已完成

| 步骤 | 内容 | 产出 |
|---|---|---|
| 3.1 | `scripts/learnings.py`：init / retrieve / capture / debrief | stdlib-only，append-only，drive-safe 相对路径 |
| 3.2 | `LEARNINGS_ROOT` 环境变量注入点 | 测试可重定向根目录 |
| 3.3 | debrief 仅打印提案、不写 AGENTS.md | 满足约束 C-1/C-2 |

### Phase 4 — SKILL.md 与纪律 ✅ 已完成

| 步骤 | 内容 | 产出 |
|---|---|---|
| 4.1 | frontmatter（name/description，仅写触发条件） | 兼容 opencode 自动发现 |
| 4.2 | 三阶段流程 + Quick reference + Common mistakes | 封死 RED 基线失败模式 |
| 4.3 | 明确红线：禁 Write notepad、禁自动写 AGENTS.md、任务前 retrieve | 约束 C-1~C-4 |

### Phase 5 — 测试 ✅ 已完成

| 步骤 | 内容 | 产出 |
|---|---|---|
| 5.1 | pytest：append-only / topic 过滤 / debrief 不写 AGENTS.md | **3 passed** |

### Phase 6 — 部署与推广 ⬜ 待办

| 步骤 | 内容 | 负责人 / 阻塞 |
|---|---|---|
| 6.1 | git 提交 `skills/learnings/`（按 writing-skills 部署要求） | 待用户点头（仓库规则：不自动 commit） |
| 6.2 | 项目 `AGENTS.md` 加一句"开工前 load `learnings` skill" | 待用户确认（否则仅靠 description 自动发现，可能不触发） |
| 6.3 | 名称确认：`learnings` / `notepads` / `记笔记` | 待用户定（目录名随手改） |
| 6.4 | 全局可用：在 `opencode.jsonc` 的 `skills.paths` 加本仓库路径，或 symlink 到 `~/.config/opencode/skills/` | 见 omo 指南 §5 步骤 3 |

### Phase 7 — 可选增强 ⬜ 待办（非必须）

| 步骤 | 内容 | 说明 |
|---|---|---|
| 7.1 | opencode `tool.execute.before` 守卫 hook，拒绝对 `.omo/notepads/**` 的 Write | 镜像 omo `notepad-write-guard`，硬约束 append-only（吸取 Windows `normalize()+sep` 坑） |
| 7.2 | 会话开始自动 `retrieve` 的 hook / 命令 | 降低"任务前忘了读"的纪律依赖 |
| 7.3 | debrief 复现检测增强（按归一化短语聚类，而非单词词频） | 提升"多次踩坑才升级"的判断精度 |
| 7.4 | 支持 `--scope auto` 从 cwd 推导默认 scope | 减少手动传参 |

---

## 3. 里程碑（按对话时序）

1. 验证 Atlas 输入契约（计划文件、跨体系不收敛）→ 关 prometheus/atlas。
2. 调研 notepad 机制 → 确认可剥离。
3. 设计 `learnings` skill（三阶段 + 用户门控 upcycle + helper 脚本）。
4. 实现脚本 + SKILL.md + 测试（3 passed）。
5. 产出需求设计文档 → 本文（实施计划）。

---

## 4. 风险与对策

| 风险 | 对策 |
|---|---|
| agent 忘记任务前 retrieve | SKILL.md 红线 + Phase 7.2 自动 hook |
| agent 用 Write 覆盖 notepad | SKILL.md 禁 Write + Phase 7.1 守卫 hook |
| 单次踩坑被误升为规则 | debrief 仅提案 + 约束 C-2（复现 ≥2 次、用户主动） |
| 跨盘路径报错 | `_display()` 用 `resolve().relative_to()` 并捕获 `ValueError`（已实现） |
| 未提交即丢失 | Phase 6.1 部署到 git |

---

## 5. 验收（同需求文档 §6）

- [x] `init` 生成 5 个分类文件
- [x] `capture` 追加不覆盖
- [x] `retrieve --topic` 正确过滤
- [x] `debrief` 不写 AGENTS.md
- [x] pytest 3 passed
- [x] 任何 agent 在 cwd 下读写同一份 `.omo/notepads/`，无需 omo
- [ ] git 部署（Phase 6.1）
- [ ] AGENTS.md 接入（Phase 6.2）
- [ ] 名称最终确认（Phase 6.3）
