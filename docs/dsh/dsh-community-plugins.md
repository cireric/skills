# DeepSeek Harness (dsh) 社区插件收集清单

> 整理时间：2026-08-19 ｜ 生态现状：GitHub `dsh-plugin` topic 已超 1000 个仓库，社区目录收录 270~1117 个不等
> Star 数为多来源交叉数据（8/14~8/19），生态爆发期数字变化快，安装前以仓库实时数据为准

---

## 一、插件发现入口（先装这几个，再按需挑）

| 入口 | 地址 | 说明 |
|---|---|---|
| dsh-market | github.com/dsh-market/dsh-market | 插件市场，装进设置页后可视化搜索/一键安装/卸载，只允许精选注册表来源 |
| dsh-find-plugin | github.com/awesome-dsh-plugin/dsh-find-plugin | 在会话里直接描述需求搜插件，按 Star 重排，返回安装命令 |
| awesome-dsh-plugin | github.com/beancookie/awesome-dsh-plugin（256⭐） | 手工精选 365 个，11 分类，中英双语，在线站：beancookie.github.io/awesome-dsh-plugin |
| awesome-dsh-plugins | github.com/AdamPlatin123/awesome-dsh-plugins（507⭐） | 自动扫描全量 dsh-plugin topic，2600+ 仓库 |
| awesome-deepseek-harness | github.com/0xsline/awesome-deepseek-harness（227⭐） | 368 条精选，18 分类，含工具与基础设施 |
| Oh-My-DSH | 社区维护目录 | 收录 1117 个插件 / 1521 仓库 / 总 30 万星（8/15 数据） |
| dsh-handbook | github.com/Electricitysheep/dsh-handbook（74⭐） | 中英双语从 0 到 1 手册，含插件开发 |

---

## 二、编程类插件

### 2.1 模型路由（对你最关键的一类）

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-tier-router | github.com/BruceLanLan/dsh-tier-router | 双层路由：强层管规划/建议/审查，便宜层管执行；支持计划模式感知、高危动作升级防护、失败自动升级、子 Agent 分层。规划绑 V4-Pro、执行绑 V4-Flash 的标准玩法 |
| dsh-plan-execute | github.com/dsh-external/dsh-plan-execute | 双模型路由另一实现：plan 模式用推理模型规划，用户批准后自动切换执行模型。⚠️ 仓库不公开，需本机 git 对 dsh-external 的读取权限 |

### 2.2 IDE / 界面工作台

| 插件 | 仓库 | Star | 功能 |
|---|---|---|---|
| dsh-web-ui | github.com/zhu1090093659/dsh-web-ui | ~1.3k | 聚合包：任务看板、Git 图、右侧面板、移动端适配、桌宠、实时 Token 统计、皮肤中心 |
| DSH-better-sidebar | github.com/omdsh-dev/DSH-better-sidebar | ~700 | 侧边栏变 IDE 工作台：文件树、内嵌终端、Git、子 Agent，开放 API 注册三方 Tab |
| dsh-TUI | github.com/ccch1mneyyy/dsh-TUI | ~640 | Claude Code 风格全屏终端：流式思考、上下文进度、TPS 展示、双击 Esc 回滚 |
| dsh-desktop | github.com/anywhere-labs/deepseek-harness-desktop | - | 封装桌面应用：独立窗口 + 系统托盘常驻 |
| dsh-desktop（qufei 版） | github.com/qufei1993/dsh-desktop | - | Windows/macOS 安装包（v0.2.0），免装 Node，内置版本管理器 |
| dsh-launcher | github.com/Ruler4396/dsh-launcher | 40 | Windows 轻量启动器 |

### 2.3 文件 / 代码操作

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-at-file | -（dsh-plugin topic 可搜） | Codex 风格 @文件 引用，输入 @login.ts 直接注入文件内容 |
| dsh-workspace-search | github.com/tsonglew/dsh-workspace-search | 工作区全文搜索：函数/类定义、配置项、接口调用点、变量全部引用 |
| dsh-file-upload | github.com/HongMing-Huang/dsh-file-upload | 回形针+拖拽上传 PDF/Word/Excel/PPT/日志，转 Markdown，提供 read_document 工具，支持 @ 引用 |
| dsh-change-review | github.com/cirelir/dsh-change-review | 追踪会话内所有写入/编辑，Diff 展示，子 Agent 改动汇总，支持撤回 |
| dsh-office | - | 让模型直接编辑 Office 文档，Web 端带 docx/pdf 预览 |
| dsh-undo / dsh-turn-rewind | dsh-undo；github.com/Anionex/dsh-turn-rewind（25⭐） | 上下文/代码状态回退，救回跑崩的会话 |
| dsh-record-replay | - | 录制一段动作序列，之后回放复用 |
| dsh-github-connector | - | 会话内直接执行 GitHub 操作 |

### 2.4 视觉能力（给纯文本 DeepSeek 补眼睛）

| 插件 | 仓库 | Star | 功能 |
|---|---|---|---|
| modlens | github.com/liustack/modlens | ~1.2k | 视觉引擎先读图（OCR+版面+语义），结构化证据再交 DeepSeek；识别报错截图、UI、表格 |
| dsh-vision-toolkit | github.com/Anionex/dsh-vision-toolkit | ~260 | 意图图片问答、长截图 OCR、UI 还原 |
| dsh-deepseek-vision | github.com/siegfly/dsh-deepseek-vision | - | 桥接 Qwen VL 等 OpenAI 兼容视觉模型，需两套 key |
| dsh-vision | - | - | 加 view_image 工具，桥接任意 OpenAI 兼容视觉模型 |

### 2.5 联网搜索

| 插件 | 功能 |
|---|---|
| dsh-web-search-exa | Exa 搜索，可无 key 降级 |
| dsh-web-search-pro | 多引擎路由：DeepSeek/Exa/DuckDuckGo/Bing/Jina/GitHub/B站/YouTube |
| modsearch | liustack 出品，联网查询时效性资料 |

### 2.6 MCP 与工具管理

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-mcp-manager | github.com/Js2Hou/dsh-mcp-manager | 设置页 MCP 管理界面：增删启停、连接状态、已注册工具数（你迁移 Magic Context/CodeGraph 必备） |

### 2.7 多 Agent / 工作流（生态最弱项）

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-agent-teams | github.com/dsh-external/dsh-agent-teams（⚠️ 私有） | 队长/成员/依赖任务/消息机制组队，Web GUI 树状状态总览 |
| dsh_workflow | -（49⭐） | 多 Agent 调度存成可治理工作流：运行记录、成本追踪、中断恢复、权限控制 |
| 官方桥接：dsh-hooks-claude-code / dsh-hooks-codex | 官方仓库 | 把现有 Claude Code / Codex 的 hooks.json 翻译成 dsh hook 扩展点，复用而非重写 |

---

## 三、个人效率类插件

### 3.1 成本与用量审计

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-cost-meter | github.com/Han-1413141/dsh-cost-meter | 每次对话/每日成本、预算百分比、官方余额、历史面板；一键同步官方价格表（含 8/17 后的峰谷分层） |
| dsh-usage-stats | github.com/Make0209/dsh-usage-stats | Token 构成、7/30 天趋势、模型占比、GitHub 风格年度热力图 |
| dsh-cost-tracker | github.com/yflmq001/dsh-cost-tracker | 按模型记输入/缓存/输出，会话费用，第三方模型需手填单价 |
| TokenTracker | - | 本地优先，覆盖 DSH/Claude Code/Codex/Cursor 多工具总账 |
| context-vista | - | 按每条消息显示 token 消耗 |

### 3.2 上下文管理

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-context | - | 上下文组成/演进/压缩/剪枝事件可视化，逐消息 token 统计，定位"47K 输入到底来自哪" |
| dsh-context-doctor | github.com/Zhenyu98/dsh-context-doctor | 逐项量化指令链/技能目录/工具 schema 的 token 账单，检测重复冲突给裁剪建议，只读安全 |

### 3.3 记忆（跨会话）

| 插件 | 仓库 | 功能 |
|---|---|---|
| dsh-memory-evolve | github.com/csyangwen/dsh-memory-evolve（24⭐） | 跨会话长期记忆+自我进化：记项目决策、架构选择、踩坑、Git 分支，可归档恢复 |
| dsh-memory-vault | - | 长期记忆沉淀，当前主要面向 web-desktop profile |
| dsh-memento / dsh-recall | - | 社区记忆插件（Oh-My-DSH 目录收录） |
| OpenViking memory | volcengine 发布（8/16） | pre-step 自动召回+画像注入，viking://URI 防护 |

### 3.4 会话迁移（降低切换成本）

| 插件 | 功能 |
|---|---|
| dsh-chat-import | 从 13 个 coding agent（Claude Code/Codex/ChatGPT/Cursor/Gemini 等）全保真导入会话，可直接续聊 |
| dsh-plugin-claude-bridge | 导入 Claude 记忆、技能、配置文件 |
| dsh-claude-move | Claude 全量迁移：Session/Memory/Skills/CLAUDE.md，原对话可续 |

### 3.5 通知与集成

| 插件 | 功能 |
|---|---|
| dsh-feishu-bot / dsh-feishu-notify | 会话事件推飞书 |
| dsh-im-hub | 多平台网关：飞书 WebSocket、企业微信、Telegram |
| dsh-share | 生成整段对话分享链接 |
| dsh-obsidian-export | 全量对话导出到 Obsidian 库 |
| dsh-news-plugin | 拉 10+ 中英文 RSS 源结构化输出 |

### 3.6 移动端与语音

| 插件 | 功能 |
|---|---|
| dsh-mobile-gate | 局域网手机访问加首次审批、设备令牌、限流、移动端布局（比裸暴露 3080 端口安全） |
| dsh-mobile / dsh-mobileweb-adapter | UI 适配手机 |
| dsh-mic-input | 浏览器 Web Speech 麦克风输入 |
| dsh-voice / dsh-voice-webspeech | Edge 神经 TTS 朗读+语音转文字 / 免服务器免 key 版 |

---

## 四、娱乐彩蛋（证明架构可塑性）

dsh-minigames（聊天窗 18 款小游戏）、dsh-ads（2005 中文门户风恶搞广告）vs dsh-anti-ads（攻防）、whale-girl（鲸鱼娘桌宠）、dsh-theme-cyberpunk2077（≥0.1.4，早期版会启动失败）。

---

## 五、安装方法与安全提示

**标准安装命令**（`--profile web` 不能省，profile 决定插件挂在哪套配置上）：

```bash
dsh plugin --profile web add "github:owner/repo#main"   # 从 GitHub 装，#main 可 pin 到 tag/commit
dsh plugin --profile web add @nanmicoder/dsh-agent-teams # 从 npm 装
dsh plugin --profile web list                            # 验证已装列表
npx @deepseek-ai/dsh web --patch                          # 补丁模式启动
```

**三个坑**：
1. 只有声明了 `dsh.bundle.patch` 字段的包才会成为激活的 profile 层——普通依赖装上是惰性的，不算插件。
2. `dsh plugin` 底层转发 pnpm，没装 pnpm 会失败；npm 镜像源同步滞后时需显式升级版本。
3. 部分插件需重启 + 硬刷新浏览器才生效。

**安全红线**：插件以当前用户权限运行，可读文件、用凭据、访问网络，工具调用审批**不隔离**插件代码。官方对凭据的原话是"谨慎，不叫边界"。建议：一次只装一个、先看源码和安装脚本、专用低余额 key、不用就卸载。
