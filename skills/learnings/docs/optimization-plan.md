# Learnings Skill — 优化方案汇总

> 整理自 2026-07-21 ~ 2026-07-22 的复盘与重构讨论。
> 背景：`learnings` 是 omo(oh-my-openagent) `notepads` 机制的轻量独立移植；经对照上游源码复盘后，
> 将用法从"开工前强制 retrieve + 工具层守卫"降级为"开发完成后用户主动 `/learnings` 总结"。

---

## 1. 当前状态（2026-07-22 已验证 + O1/O2 已落地）

| 验证项 | 结果 | 说明 |
|---|---|---|
| pytest 核心不变量 | ✅ 3 passed | append-only / topic 过滤 / debrief 不写 AGENTS.md（O1/O2 后回归仍通过） |
| SKILL.md frontmatter | ✅ 合法 | `name=learnings` / `disable-model-invocation=true` / `argument-hint=[scope]` |
| 临时目录端到端回归 | ✅ 通过 | init→capture→debrief(仅提案)→retrieve --topic(过滤正确) |
| **O1: 无 `--scope` 兜底** | ✅ 已验证 | `init/capture/retrieve/debrief` 不传 `--scope` 时默认落到 `cireric-skills`（当前目录名）桶 |
| **O2: What to capture 标尺** | ✅ 已写入 | SKILL.md 新增 "What to capture (triage rubric)" 小节 |
| 真实落盘 | ✅ 已写 | `.omo/notepads/cireric-skills/{issues,learnings}.md` |

**已知弱点（仍存）**：`debrief` 的复发检测是**单词词频统计**，会把同一任务内重复出现的词误标为
"recurring"（本次回归中 `cross x2` 被误标）。降级模型下可接受，待 O3 修复。

---

## 2. 已完成的优化（本会话）

| # | 优化 | 改动 |
|---|---|---|
| D1 | 删除冗余命令文件 | 删 `.opencode/commands/learnings.md`。OpenCode 中 skills 与 commands 已合并，`skills/learnings/SKILL.md`(name=learnings) 本身就是 `/learnings`；同名时 **skill 优先**，原 command 被覆盖且冗余。 |
| D2 | 纯用户触发语义 | SKILL.md frontmatter 加 `disable-model-invocation: true`（仅用户显式 `/learnings` 触发，agent 不擅自加载）+ `argument-hint: "[scope]"`。 |
| D3 | 降级用法模型 | "When to use" 将 post-dev 用户触发设为主模式，`retrieve` 降为可选；Common mistakes 同步。 |
| D4 | scope 自动推断 | 增 Scope 说明：`/learnings myproject` 用参数，省略则由 agent 从 repo/project 名或 cwd 推断，禁用手抛 task id。 |
| D5 | 真实落盘验证 | 本次踩坑("skills/commands 合并""disable-model-invocation 用法")已 capture 进 `.omo/notepads/cireric-skills/`。 |
| D6 | **O1: `--scope` 可选** | 脚本 `init/capture/retrieve/debrief` 的 `--scope` 改为可选，缺省取 `Path.cwd().name`（当前目录名）。代码兜底，防 agent 漏传 scope 报错。纯 stdlib。已验证：无 `--scope` 时正确落到 `cireric-skills` 桶。 |
| D7 | **O2: "What to capture" 标尺** | SKILL.md 新增 "What to capture (triage rubric)" 小节：五类定义表 + 三条捕获测试(复用性 / 非显性 / 成本价值) + 噪音清单。统一每次 `/learnings` 的沉淀口径，解决"什么值得沉淀"无标准问题。 |

---

## 3. 待办优化方案（提案，按优先级）

### P1 — 低风险、高收益（✅ 已落地）

| # | 方案 | 内容 | 状态 |
|---|---|---|---|
| **O1** | `--scope` 改为可选 | 脚本 `capture/retrieve/debrief` 的 `--scope` 缺省时取当前目录 basename，代码兜底防缺参报错。 | ✅ 已完成（见 D6） |
| **O2** | SKILL.md 增 "What to capture" rubric | 五类定义 + "capture or skip" 标尺（复用性 / 非显性 / 成本价值）+ 噪音清单。 | ✅ 已完成（见 D7） |

### P2 — 中风险 / 需设计

| # | 方案 | 内容 | 改动量 | 风险 |
|---|---|---|---|---|
| **O3** | debrief 复发检测去噪 | 改为**跨 entry / 跨 task 去重 + 短语聚类**，消除单词词频误报（同一任务两条记录里的词被算成 recurring）。 | 中（需重设计计数逻辑，仍纯 stdlib） | 中（聚类阈值需调） |
| **O4** | content 正则误切防护 | `debrief` 用正则 `## \[...\] Task:` 切分条目；若某条 content 自身含该形状行会误切。改为分隔符/转义防护。 | 小 | 低 |

### P3 — 可选增强（降级模型下非必需）

| # | 方案 | 内容 | 说明 |
|---|---|---|---|
| **O5** | 接入 AGENTS.md 一句提示 | 在项目 `AGENTS.md` 加"开发完跑 `/learnings`"双保险触发。 | 与现有 "task-observer 激活" 风格一致 |
| **O6** | notepad-write-guard hook | 工具层硬拒绝对 `.omo/notepads/**` 的 `Write`，强制 append-only，防历史被覆盖。 | omo 上游有，learnings 降级后变可选 |
| **O7** | auto-retrieve hook | 任务开始自动 `retrieve` 并注入系统提示，补回"事前预防"。 | 与降级初衷(去 hook)相悖，按需 |

---

## 4. 验证 / 验收清单

每次改动后须满足：

- [ ] `pytest skills/learnings/tests/test_learnings.py` → 3 passed（append-only / 过滤 / 不写 AGENTS.md）
- [ ] `capture` 二次调用**追加而非覆盖**
- [ ] `retrieve --topic` 仅返回相关条目
- [ ] `debrief` 输出含 "DO NOT auto-apply" 且 **AGENTS.md 未被创建/修改**
- [ ] frontmatter 经 YAML 解析：`disable-model-invocation=true`
- [ ] 端到端：`init → capture → debrief → retrieve` 在临时 `LEARNINGS_ROOT` 跑通

---

## 5. 决策建议

1. **O1 + O2 已完成（2026-07-22）**：纯 stdlib / 仅文档，零风险，已消除两个最实际的痛点（scope 缺参、沉淀无标尺）。
2. **下一步候选 O3**：debrief 复发检测去噪（跨 task 去重 + 短语聚类），属质量提升，不影响主流程，建议作为下一个优化项排期。
3. **O5/O6/O7 默认不做**：降级模型刻意去掉 hook 与强制 retrieve，除非用户后续想要"事前预防"强度才启用 O6/O7。

---

## 附：五类 notepad 定义速查

| 分类 | 本质 | 记什么 | 反例（不记） |
|---|---|---|---|
| `learnings` | 成功模式 | 可复用经验（"下次还这么干"） | 一次性手滑 |
| `decisions` | 选型+理由 | 为什么这么做 | 已写 AGENTS.md 的 |
| `issues` | 踩坑/blocker/gotcha | 坑 + 正确做法 | 纯任务进度流水 |
| `problems` | 未解决/技术债 | 悬而未决项 | 随重构即失效的临时态 |
| `verification` | 验证结论 | X 行得通/行不通 | 机密/客户数据 |
