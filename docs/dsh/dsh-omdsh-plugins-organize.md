# Oh My DSH（omdsh-dev）插件目录分类整理

> 数据来源：GitHub API 实时抓取（2026-08-20），共 **103 个 source 仓库**。
>
> ⚠️ **性质澄清**：omdsh-dev（Oh My DSH）是**独立、非官方的社区插件生态**，组织 README 明确声明与 DeepSeek 及其关联主体不存在隶属、授权、合作或背书关系；"收录不等于安全/兼容性认证"。它是目前 DSH 插件覆盖最全的社区目录，配套 [OMDSH Hub](https://hub.omdsh.dev) 插件市场。

---

## 总览

| 维度                     | 数据                                                            |
| ------------------------ | --------------------------------------------------------------- |
| 仓库总数                 | 103（含 3 个组织/治理仓库，非插件）                             |
| 主力语言                 | TypeScript（约 70%），其次 JavaScript、Go                       |
| Stars Top 3              | DSH-better-sidebar (2430) · dsh-at-file (438) · dsh-genui (262) |
| 官方社区精选（Featured） | Better Sidebar / @File / GenUI / Workflow / DSH Hub / Community |
| 社区活跃度               | 绝大多数仓库 8 月中下旬仍在推送，生态处于快速生长期             |

**社区自己的六大方向分类**（组织 README）：界面与交互 / Agent 与工作流 / 开发者工具 / 研究与数据 / 集成与通知 / 安全与诊断。以下整理在此基础上细化。

---

## 一、组织与治理（3 个，非插件）

| 仓库                                                            | 说明                                                |
| --------------------------------------------------------------- | --------------------------------------------------- |
| [.github](https://github.com/omdsh-dev/.github)                 | 组织主页 profile（即"Oh My DSH"目录入口与精选榜单） |
| [community](https://github.com/omdsh-dev/community)             | 社区中心：插件提交、贡献者入门、讨论与组织治理      |
| [org-discussions](https://github.com/omdsh-dev/org-discussions) | 组织级 Discussions 仓库                             |

## 二、生态基础设施与插件开发（9 个）

| 仓库                                                                | 说明                                                                                                 | 语言 | ⭐  | 最近推送 |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-plugin-check](https://github.com/omdsh-dev/dsh-plugin-check)   | 插件健康检查：清单协议/patch 格式/构建陷阱/hub 收录状态扫描                                          | TS   | 24  | 08-20    |
| [dsh-plugin-dev](https://github.com/omdsh-dev/dsh-plugin-dev)       | 插件开发踩坑档案（skill+文档）：cordis 双副本、tsconfig 三件套、Windows junction、多帧 zstd 实测记录 | —    | 13  | 08-20    |
| [dsh-plugin-skills](https://github.com/omdsh-dev/dsh-plugin-skills) | 插件开发/测试的 Agent skills（脚手架→测试分级）                                                      | —    | 11  | 08-11    |
| [plugin-template](https://github.com/omdsh-dev/plugin-template)     | 插件模板仓库（基于原 turtle ui 官方仓库）                                                            | JS   | 11  | 08-20    |
| [dsh-hub-workshop](https://github.com/omdsh-dev/dsh-hub-workshop)   | 插件市场/目录/注册表工作台                                                                           | JS   | 6   | 08-20    |
| [dsh-hub](https://github.com/omdsh-dev/dsh-hub)                     | 插件管理器/市场/注册表（hub.omdsh.dev 后端）                                                         | JS   | 4   | 08-13    |
| [omdsh-runtime](https://github.com/omdsh-dev/omdsh-runtime)         | 插件运行时/profile 管理（无描述，据主题推断）                                                        | JS   | 2   | 08-15    |
| [omdsh](https://github.com/omdsh-dev/omdsh)                         | 发行/分发工具（无描述，据主题推断）                                                                  | JS   | 1   | 08-13    |
| [omdsh-plugin-lab](https://github.com/omdsh-dev/omdsh-plugin-lab)   | 插件试用结果/问题回执/修复通知/复测飞轮                                                              | TS   | 0   | 08-17    |

另有 [dsh-skill-stats](https://github.com/omdsh-dev/dsh-skill-stats)（skill 使用统计，社区镜像，⭐1）。

## 三、界面与交互增强（15 个）

| 仓库                                                                  | 说明                                                                                   | 语言 | ⭐   | 最近推送 |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---- | ---- | -------- |
| [DSH-better-sidebar](https://github.com/omdsh-dev/DSH-better-sidebar) | **生态头牌**。开放侧边栏底座，支持三方注册新页面；内置文件渲染编辑/终端/Git/子代理页面 | TS   | 2430 | 08-20    |
| [dsh-at-file](https://github.com/omdsh-dev/dsh-at-file)               | Codex 风格 @file：输入框搜索并引用工作区文件                                           | JS   | 438  | 08-20    |
| [dsh-genui](https://github.com/omdsh-dev/dsh-genui)                   | GenUI：对话内联渲染交互式布局/图表/表单/quiz/mermaid/3D 场景 + 动作事件回路            | TS   | 262  | 08-20    |
| [dsh-annotation](https://github.com/omdsh-dev/dsh-annotation)         | Web 选中批注：选文字→批注→随消息发送，回复逐条对照                                     | HTML | 82   | 08-20    |
| [dsh-tui](https://github.com/omdsh-dev/dsh-tui)                       | 终端 UI 前端（基于 pi-tui 的 Cordis 插件）：transcript/工具卡片/覆盖层/斜杠命令/主题   | TS   | 0    | 08-17    |
| [ex-setting](https://github.com/omdsh-dev/ex-setting)                 | DSH 设置扩展                                                                           | TS   | 2    | 08-20    |
| [dsh-input-history](https://github.com/omdsh-dev/dsh-input-history)   | 输入历史：Ctrl+Up/Down 终端式召回已发送消息                                            | TS   | 3    | 08-14    |
| [dsh-paste-input](https://github.com/omdsh-dev/dsh-paste-input)       | 文件输入增强：Ctrl+V 粘贴 + 拖拽 + 选择文件                                            | JS   | 2    | 08-20    |
| [dsh-drag-and-drop](https://github.com/omdsh-dev/dsh-drag-and-drop)   | 拖拽支持（org copy）                                                                   | JS   | 5    | 08-14    |
| [dsh-ui-progress](https://github.com/omdsh-dev/dsh-ui-progress)       | 会话进度条：todos 真实进度/token 速率/中断态/待办提醒                                  | TS   | 2    | 08-14    |
| [dsh-ui-whale](https://github.com/omdsh-dev/dsh-ui-whale)             | 全手绘像素鲸鱼伙伴（会动、会喷水、会睡觉）                                             | TS   | 2    | 08-14    |
| [web-components](https://github.com/omdsh-dev/web-components)         | web-components 支持                                                                    | TS   | 2    | 08-09    |
| [dsh-webbridge](https://github.com/omdsh-dev/dsh-webbridge)           | Web 桥接（无描述，据名称推断）                                                         | JS   | 2    | 08-14    |
| [dsh-web-ui-notify](https://github.com/omdsh-dev/dsh-web-ui-notify)   | Web UI 通知（无描述，据名称推断）                                                      | TS   | 3    | 08-14    |
| [dsh-meep](https://github.com/omdsh-dev/dsh-meep)                     | 可自定义桌宠，独立进程，关键时刻提醒                                                   | JS   | 1    | 08-14    |

## 四、Agent 编排 · 工作流 · 记忆（9 个）

| 仓库                                                                | 说明                                                                                                        | 语言 | ⭐  | 最近推送 |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-mnemon](https://github.com/omdsh-dev/dsh-mnemon)               | 三层记忆控制面：持久运行时上下文 + 可检索项目文档 + 可插拔长期记忆，智能路由/监督式 agent/WebUI             | TS   | 130 | 08-19    |
| [dsh-deep-research](https://github.com/omdsh-dev/dsh-deep-research) | 自适应深度研究编排器（官方 workflow 引擎，控制论/信息论设计）                                               | TS   | 17  | 08-12    |
| [dsh-advisor](https://github.com/omdsh-dev/dsh-advisor)             | 副模型：每轮被动审查并注入见解（双模型搭档）                                                                | TS   | 15  | 08-20    |
| [fabric](https://github.com/omdsh-dev/fabric)                       | 类 MC Fabric 的 dsh hook 处理器                                                                             | TS   | 15  | 08-20    |
| [dsh_workflow](https://github.com/omdsh-dev/dsh_workflow)           | 把 Claude Code 的 UltraCode 模式带给 DSH：一次性多 Agent 调度升级为可生成/保存/治理/观察/恢复的 Workflow 层 | TS   | 89  | 08-13    |
| [dsh-llm-fallbacks](https://github.com/omdsh-dev/dsh-llm-fallbacks) | 按角色（role-based）的模型重试&回退策略                                                                     | TS   | 11  | 08-20    |
| [dsh-sidechain](https://github.com/omdsh-dev/dsh-sidechain)         | 侧会话：/side 持续性（Codex 风格）+ /btw 一次性侧问（Claude 风格），临时 fork 不写主历史                    | TS   | 10  | 08-18    |
| [dsh-inspect](https://github.com/omdsh-dev/dsh-inspect)             | 对抗式闭环：checkup 发现问题 → fix 修复交付 → review 质量复查                                               | JS   | 6   | 08-17    |
| [Qwen-MM-Plugins](https://github.com/omdsh-dev/Qwen-MM-Plugins)     | Qwen 多模态插件支持                                                                                         | TS   | 5   | 08-09    |

## 五、确定性工具集 · dsh-tool-\* 系列（12 个，全部零依赖）

| 仓库                                                                    | 注册工具   | 功能                                              | ⭐  |
| ----------------------------------------------------------------------- | ---------- | ------------------------------------------------- | --- |
| [dsh-toolkit](https://github.com/omdsh-dev/dsh-toolkit)                 | 统一入口   | 下列 10 个工具一键安装合集                        | 23  |
| [dsh-tool-calculator](https://github.com/omdsh-dev/dsh-tool-calculator) | calculator | 安全数学表达式求值（递归下降解析器）              | 7   |
| [dsh-tool-stat](https://github.com/omdsh-dev/dsh-tool-stat)             | stat       | 描述统计/百分位数/频数/相关性                     | 6   |
| [dsh-tool-csv](https://github.com/omdsh-dev/dsh-tool-csv)               | csv        | CSV 解析/查询/统计/转换（RFC 4180 状态机）        | 4   |
| [dsh-tool-time](https://github.com/omdsh-dev/dsh-tool-time)             | time       | 严格 ISO 8601 解析、IANA 时区转换、UTC 日历运算   | 4   |
| [dsh-tool-markdown](https://github.com/omdsh-dev/dsh-tool-markdown)     | markdown   | HTML↔Markdown、GFM 表格规范化、目录生成           | 4   |
| [dsh-tool-diff](https://github.com/omdsh-dev/dsh-tool-diff)             | diff       | 文本/JSON/CSV/Markdown 结构化比较 + unified diff  | 4   |
| [dsh-tool-json](https://github.com/omdsh-dev/dsh-tool-json)             | json       | JMESPath 子集查询                                 | 3   |
| [dsh-tool-encoding](https://github.com/omdsh-dev/dsh-tool-encoding)     | encoding   | base64/url/hex 编解码、md5/sha 系列哈希、UUID     | 3   |
| [dsh-tool-regex](https://github.com/omdsh-dev/dsh-tool-regex)           | regex      | 匹配测试/捕获组提取/安全替换/静态解释（防 ReDoS） | 3   |
| [dsh-tool-schema](https://github.com/omdsh-dev/dsh-tool-schema)         | schema     | JSON Schema validate/paths/explain/normalize      | 3   |
| [dsh-tool-tariff](https://github.com/omdsh-dev/dsh-tool-tariff)         | —          | 峰谷电价、DeepSeek API 余额提醒、Web 状态徽章     | 1   |

## 六、数据 · 研究 · 知识库（6 个）

| 仓库                                                              | 说明                                                                                         | 语言 | ⭐  | 最近推送 |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-data-agent](https://github.com/omdsh-dev/dsh-data-agent)     | 连接数据库做对话式数据分析与商业洞察                                                         | JS   | 100 | 08-20    |
| [dsh-kb-sieve](https://github.com/omdsh-dev/dsh-kb-sieve)         | 知识库：从 md/txt/docx/pdf 构建可审计 KB 包（引用+SQLite FTS5），确定性检索 kb_query/kb_read | TS   | 2   | 08-12    |
| [dsh-science](https://github.com/omdsh-dev/dsh-science)           | 可复现 Python/R 科学计算（conda）                                                            | TS   | 5   | 08-18    |
| [dsh-paddle-ocr](https://github.com/omdsh-dev/dsh-paddle-ocr)     | PaddleOCR-VL 文档版面解析：PDF/图片→Markdown，异步任务+进度追踪                              | TS   | 3   | 08-19    |
| [dsh-book2skill](https://github.com/omdsh-dev/dsh-book2skill)     | 整本书转 skill：fetch→parse→understand→generate→install 五阶段长任务 + 3 个人工闸门          | TS   | 4   | 08-19    |
| [dsh-whale-report](https://github.com/omdsh-dev/dsh-whale-report) | 深迹 DeepTrace：从会话事件日志生成日/周/月/年报，只读不改历史                                | TS   | 1   | 08-20    |

## 七、集成与通知（9 个）

| 仓库                                                                          | 说明                                                              | 语言 | ⭐  | 最近推送 |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-notification](https://github.com/omdsh-dev/dsh-notification)             | 桌面通知：回合完成推送，按结果类型+关键词规则控制                 | JS   | 65  | 08-19    |
| [dsh-open-in-vscode](https://github.com/omdsh-dev/dsh-open-in-vscode)         | Web GUI 中一键用 VS Code 打开工作区目录                           | JS   | 53  | 08-16    |
| [dsh-lark](https://github.com/omdsh-dev/dsh-lark)                             | 飞书 IM bot 通道（Lark/Feishu channel）                           | TS   | 38  | 08-19    |
| [dsh-cron](https://github.com/omdsh-dev/dsh-cron)                             | 定时任务：模型/人可调用的调度，触发 followup/inject 进 agent 会话 | TS   | 2   | 08-20    |
| [dsh-github-integration](https://github.com/omdsh-dev/dsh-github-integration) | GitHub Actions / 工作流自动化（无描述，据主题推断）               | JS   | 2   | 08-14    |
| [dsh-fun-ticker](https://github.com/omdsh-dev/dsh-fun-ticker)                 | 行情跑马灯：加密/汇率/A股/指数/港美股，免 key 数据源              | TS   | 5   | 08-19    |
| [dsh-longbridge](https://github.com/omdsh-dev/dsh-longbridge)                 | 长桥港美股行情/账户/持仓 + 审批闸门下单，内置设置面板             | TS   | 5   | 08-19    |
| [dsh-feishu-notify](https://github.com/omdsh-dev/dsh-feishu-notify)           | 飞书卡片通知：会话结束/等待输入                                   | TS   | 1   | 08-18    |
| [dsh-webhook](https://github.com/omdsh-dev/dsh-webhook)                       | 入站 webhook：签名 HTTP 事件→执行 agent 任务+回执                 | TS   | 0   | 08-18    |

## 八、安全 · 诊断 · 会话管理（11 个）

| 仓库                                                                          | 说明                                                                   | 语言 | ⭐  | 最近推送 |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-security-audit](https://github.com/omdsh-dev/dsh-security-audit)         | 本机安全审计：配置/插件来源/会话/网络暴露面，只读脱敏风险报告          | TS   | 13  | 08-20    |
| [dsh-session-health](https://github.com/omdsh-dev/dsh-session-health)         | 会话文件帧级扫描诊断（torn/损坏/空会话，多帧 zstd），只读              | TS   | 8   | 08-20    |
| [dsh-bash-encoding](https://github.com/omdsh-dev/dsh-bash-encoding)           | bash 输出编码自动识别（UTF-16LE/UTF-8/GBK），修复 WSL/Windows 中文乱码 | TS   | 2   | 08-14    |
| [dsh-revive](https://github.com/omdsh-dev/dsh-revive)                         | 一键复活：重启后给所有被打断的会话自动发「继续」                       | TS   | 3   | 08-19    |
| [dsh-scout](https://github.com/omdsh-dev/dsh-scout)                           | 只读环境探测：运行环境/版本/资源/端口/服务/硬件                        | TS   | 2   | 08-14    |
| [dsh-fusion](https://github.com/omdsh-dev/dsh-fusion)                         | 多个对话融合为一个可继续会话（智能剪枝/话题分组/排序）                 | TS   | 2   | 08-14    |
| [session-teleport](https://github.com/omdsh-dev/session-teleport)             | 会话数据迁移（PostgreSQL，据主题推断）                                 | TS   | 2   | 08-14    |
| [dsh-conversation-share](https://github.com/omdsh-dev/dsh-conversation-share) | 对话分享（无描述，据名称推断）                                         | JS   | 2   | 08-14    |
| [dsh-shuttle](https://github.com/omdsh-dev/dsh-shuttle)                       | DSH ↔ Codex/Claude Code/Pi/Reasonix/OpenCode 对话记录双向迁移          | TS   | 1   | 08-14    |
| [dsh-essential](https://github.com/omdsh-dev/dsh-essential)                   | 可恢复的对话删除：即时隐藏+重启安全归档                                | TS   | 1   | 08-14    |

## 九、沙盒 · 运行时 · 桌面化 · 发行版（9 个）

| 仓库                                                                                              | 说明                                                     | 语言 | ⭐  | 最近推送 |
| ------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ---- | --- | -------- |
| [dsh-web-desktopify](https://github.com/omdsh-dev/dsh-web-desktopify)                             | DSH 桌面应用打包器（Linux/macOS/Windows）                | Go   | 8   | 08-20    |
| [awesome-deepseek-harness-desktop](https://github.com/omdsh-dev/awesome-deepseek-harness-desktop) | ADHD：开箱即用的 Electron 桌面壳                         | JS   | 11  | 08-19    |
| [marisa-distro](https://github.com/omdsh-dev/marisa-distro)                                       | 魔理沙 DSH 整合包发行：29 插件 + 一键安装 + profile 直装 | TS   | 4   | 08-20    |
| [sandbox-mxc](https://github.com/omdsh-dev/sandbox-mxc)                                           | 微软跨平台沙盒支持                                       | TS   | 2   | 08-19    |
| [sandbox-micro](https://github.com/omdsh-dev/sandbox-micro)                                       | microsandbox 支持                                        | TS   | 3   | 08-09    |
| [sandbox-nono](https://github.com/omdsh-dev/sandbox-nono)                                         | nono 沙盒支持                                            | TS   | 3   | 08-11    |
| [dsh-sandbox-micro](https://github.com/omdsh-dev/dsh-sandbox-micro)                               | microsandbox 沙盒（bundle 版，据主题推断）               | TS   | 1   | 08-20    |
| [dsh-container](https://github.com/omdsh-dev/dsh-container)                                       | Docker 容器化封装：安全沙箱+局域网中继+数据持久化        | JS   | 1   | 08-20    |
| [dsh-web-desktopify-template](https://github.com/omdsh-dev/dsh-web-desktopify-template)           | desktopify 配套模板                                      | TS   | 2   | 08-20    |

## 十、通用开发与效率工具（8 个）

| 仓库                                                              | 说明                                                                          | 语言 | ⭐  | 最近推送 |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---- | --- | -------- |
| [dsh-custom-tool](https://github.com/omdsh-dev/dsh-custom-tool)   | Monaco 编辑器创建/管理沙盒化 JS 工具，模型驱动工具生命周期                    | TS   | 24  | 08-16    |
| [dsh-office](https://github.com/omdsh-dev/dsh-office)             | 办公三件套：xlsx / PDF / pptx 的生成、读取、编辑                              | TS   | 15  | 08-16    |
| [dsh-lsp](https://github.com/omdsh-dev/dsh-lsp)                   | LSP 工具面：goto_definition / find_references / diagnostics，惰性多语言客户端 | TS   | 2   | 08-15    |
| [dsh-voice-funasr](https://github.com/omdsh-dev/dsh-voice-funasr) | 本地离线语音输入（FunASR ONNX + Web Speech 回退 + 可选 LLM 润色）             | TS   | 3   | 08-19    |
| [dsh-ernie-image](https://github.com/omdsh-dev/dsh-ernie-image)   | ERNIE 文生图（无描述，据名称推断）                                            | TS   | 3   | 08-19    |
| [dsh-tool-browser](https://github.com/omdsh-dev/dsh-tool-browser) | 浏览器自动化工具（无描述，据主题推断）                                        | JS   | 1   | 08-13    |
| [dsh-browser4](https://github.com/omdsh-dev/dsh-browser4)         | AI 原生浏览器引擎：自主 agent、智能抽取、大规模 Web 自动化                    | PS   | 0   | 08-17    |
| [toybox](https://github.com/omdsh-dev/toybox)                     | MCP 工具箱（无描述，据主题推断）                                              | TS   | 2   | 08-14    |

## 十一、娱乐与趣味（13 个）

| 仓库                                                                  | 说明                                                                                     | 语言 | ⭐  |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---- | --- |
| [dsh-gomoku](https://github.com/omdsh-dev/dsh-gomoku)                 | 与 AI 下五子棋，或让两个 AI 对弈比棋力                                                   | TS   | 14  |
| [dsh-minigames](https://github.com/omdsh-dev/dsh-minigames)           | 18 款离线小游戏（跳一跳/俄罗斯方块/坦克/扫雷/2048/数独/吃豆人…），等模型回复时的摸鱼神器 | TS   | 6   |
| [dsh-auto-chess](https://github.com/omdsh-dev/dsh-auto-chess)         | Web 自走棋：人机对战或双 AI 对弈                                                         | TS   | 3   |
| [dsh-fun-weather](https://github.com/omdsh-dev/dsh-fun-weather)       | 天气标签页 + 天气跟随主题（Open-Meteo）                                                  | TS   | 3   |
| [dsh-daily-fortune](https://github.com/omdsh-dev/dsh-daily-fortune)   | 每日运势：观音灵签 + 塔罗 + 每日一句                                                     | TS   | 3   |
| [dsh-fun-typewriter](https://github.com/omdsh-dev/dsh-fun-typewriter) | 打字机白噪音（WebAudio，零音频资产）                                                     | TS   | 3   |
| [dsh-pet-corner](https://github.com/omdsh-dev/dsh-pet-corner)         | 悬浮宠物 + 免 key 宠物图代理 + 收藏夹                                                    | TS   | 3   |
| [dsh-deep-sleep](https://github.com/omdsh-dev/dsh-deep-sleep)         | 猫猫早睡提醒                                                                             | TS   | 2   |
| [7d7d](https://github.com/omdsh-dev/7d7d)                             | mini-games（无描述，据主题推断）                                                         | HTML | 4   |
| [dsh-mygo](https://github.com/omdsh-dev/dsh-mygo)                     | 无描述，据名称推断为 MyGO!!!!! 主题趣味插件                                              | TS   | 11  |
| [dsh-daily-progress](https://github.com/omdsh-dev/dsh-daily-progress) | 每日进度（无描述，据名称推断）                                                           | TS   | 3   |
| [dsh-meme](https://github.com/omdsh-dev/dsh-meme)                     | meme 相关（无描述，据名称推断）                                                          | JS   | 2   |
| [dsh-skill-stats](https://github.com/omdsh-dev/dsh-skill-stats)       | 见「生态基础设施」（社区镜像）                                                           | TS   | 1   |

---

## 观察与建议（结合你的 dsh 研究方向）

1. **必看头部项目**：DSH-better-sidebar（2430⭐，事实上已是 DSH Web 的"标准工作台"）、dsh-at-file（438⭐）、dsh-genui（262⭐，对话内交互 UI 范式）。
2. **与你的分层路由策略直接相关**：`dsh-advisor`（副模型每轮审查，天然适配 Pro 审查 + Flash 执行的架构）和 `dsh-llm-fallbacks`（按角色配模型重试/回退）——这两个正好是你"Pro 规划/Flash 实现"工作流的插件化载体。
3. **Windows 环境注意**：`dsh-bash-encoding` 专修 WSL/Windows bash 中文乱码，与你的 Git Bash 环境直接相关；`dsh-plugin-dev` 的开发档案里记录了 Windows junction 踩坑。
4. **与你 Codex/OpenCode 多 harness 并存相关**：`dsh-shuttle` 支持对话在 DSH ↔ Codex/Claude Code/OpenCode/Reasonix 间双向迁移。
5. **风险提示**：组织自我声明"收录不等于认证"，安装前建议过一遍 `dsh-plugin-check` 的健康检查思路（清单协议/patch 格式/构建陷阱），金融类插件（longbridge 下单、fun-ticker 行情）尤其注意密钥权限。

---

_数据快照时间：2026-08-20 19:50 (GMT+8) · 由 GitHub API (`/orgs/omdsh-dev/repos`) 抓取整理_
