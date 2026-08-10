# task-observer

持续捕获技能改进机会的观察者 skill。在任务执行中发现 skill 文件缺陷、协作断裂、流程缺口，记入观察日志供 review。

## 快速开始

### 1. 手动使用

```bash
# 初始化观察日志目录
.venv/Scripts/python.exe skills/task-observer/scripts/task_observer.py init

# 查看观察状态
.venv/Scripts/python.exe skills/task-observer/scripts/task_observer.py status

# 记录一条观察
.venv/Scripts/python.exe skills/task-observer/scripts/task_observer.py append \
  --session-context "正在做什么任务" \
  --skill "skill名称" \
  --type internal \
  --phase "哪个环节" \
  --issue "发生了什么" \
  --improvement "具体怎么改" \
  --principle "可推广的原则"
```

> Windows 路径：`.venv\Scripts\python.exe` / Linux/Mac：`.venv/bin/python`

### 2. 配置自动激活（推荐）

在项目 `.opencode/plugins/` 目录下创建插件，监听 `session.created` 事件，通过 SDK 向新 session 注入 skill 加载指令：

```js
// .opencode/plugins/auto-task-observer.js
export const AutoTaskObserver = async ({ project, client, $, directory, worktree }) => {
  return {
    event: async ({ event }) => {
      if (event.type !== "session.created") return

      const sessionID = event.properties.info.id

      try {
        await client.session.promptAsync({
          path: { id: sessionID },
          body: {
            parts: [
              {
                type: "text",
                text: "[system] Load the task-observer skill now and run its Session Start Protocol (init + status check). Do not reply to this message — proceed silently and wait for the user's first input.",
                synthetic: true,
              },
            ],
            noReply: true,
          },
        })
      } catch (err) {
        console.error("[auto-task-observer] failed to inject skill-load prompt:", err)
      }
    },
  }
}
```

**工作原理：**

| 步骤 | 说明 |
|------|------|
| 1 | opencode 启动时自动加载 `.opencode/plugins/*.{js,ts}` |
| 2 | 新 session 创建 → 触发 `session.created` 事件 |
| 3 | 插件捕获事件，用 `client.session.promptAsync` 异步注入一条 synthetic 消息 |
| 4 | agent 收到消息后加载 task-observer skill 并执行 Session Start Protocol |

**关键设计：**

- `promptAsync` — 异步注入，不阻塞，agent 就绪后自动从队列取消息处理
- `noReply: true` — 注入消息仅作上下文，不触发 agent 回复用户
- `synthetic: true` — 标记为系统注入消息，不显示在对话流中
- V1 Plugin API — 稳定版，不依赖 beta 的 V2 API
- 项目级插件 — 仅对本项目生效，不影响全局

也可以用 `.ts` 替代 `.js`，无需修改 `opencode.jsonc`。

### 3. 在 AGENTS.md 中添加激活指令（备选）

如果不想用插件，可在 AGENTS.md 中写规则让 agent 每次会话主动加载：

```markdown
## task-observer 激活

任何任务导向会话开始时，先加载 task-observer skill。
```

缺点：每个会话都加载，无法按需跳过；依赖 agent 自觉执行，非事件驱动。

## 工作流程

```
会话开始 → session.created 事件 → 插件注入 skill 加载指令 → agent 执行 Session Start Protocol → 全程观察 → 会话收尾 surfacing → weekly review
```

| 阶段 | 触发方式 | 说明 |
|------|----------|------|
| **Init** | 自动（插件）或手动 `/task-observer:init` | 创建 `.omo/skill-observations/` 目录和 log.md；已存在时幂等跳过 |
| **Session Start Protocol** | 插件注入后 agent 自动执行 | init（如需）→ 扫描 OPEN 观察 → 检查 review 状态 |
| **Observe** | 全程被动 | 执行、反馈、review 讨论中持续观察；每 3 个 todo 完成强制检查点；交付物完成时 flush |
| **Surface** | 会话收尾时 agent 主动浮现 | 分组总结观察，询问用户是否处理；默认 log-and-defer |
| **Review** | `/task-observer:review` | 周度 review，归档已处理的观察 |

## 命令

| 命令 | 用途 |
|------|------|
| `/task-observer:init` | 初始化观察日志目录 |
| `/task-observer:review` | 运行周度 review |
| `/task-observer:status` | 查看 OPEN/ACTIONED/DECLINED 统计 |

## 观察范围（L1–L3）

- **L1** — skill 文件缺陷（规则模糊、缺失、违规）
- **L2** — skill 间协作断裂
- **L3** — 工作流/方法论缺口

项目级经验（L4 agent 行为、L5 工具 quirks）归 `learnings` skill。

## 输出目录

```
.omo/skill-observations/
├── log.md              # 观察日志（追加）
├── log.md.bak-YYYY-MM-DD  # mark/archive 写前快照（崩溃回滚点，按天覆盖，保留最近 2 个）
├── archive/log-YYYY-MM-DD.md  # 已解决条目移出账本（永久留存）
├── last-review-date.txt
└── config.json
```

`.bak` 快照仅作回滚用途：已解决条目在 `archive/` 中有永久副本，因此 `.bak` 可安全删除（脚本自动保留最近 `backup_retain_count` 个，默认 2）。

## 参考文档

| 文件 | 用途 |
|------|------|
| `SKILL.md` | agent 行为指令（完整协议） |
| `references/weekly-review.md` | review 流程和策略 |
| `references/skill-authoring.md` | 创建/编辑 skill 的规则 |
| `references/environments.md` | 激活配置、compaction、已知限制 |
