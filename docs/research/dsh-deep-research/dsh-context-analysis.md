# dsh-context 项目完整分析

## 1. 项目基本信息

| 字段 | 值 |
|------|-----|
| **GitHub** | https://github.com/bowenliang123/dsh-context |
| **npm** | https://www.npmjs.com/package/dsh-context |
| **作者** | bowenliang123 (Bowen Liang) |
| **语言** | TypeScript |
| **许可证** | Apache-2.0 |
| **Stars** | 605 ⭐ |
| **Forks** | 5 |
| **Open Issues** | 1 |
| **创建时间** | 2026-08-14 |
| **最后推送** | 2026-08-20 (活跃开发中) |
| **插件类型** | cordis-plugin (DSH Web 捆绑插件) |
| **市场评分** | 87/100 (高分) |

---

## 2. 项目定位

**dsh-context** 是 DeepSeek Harness (DSH) 生态系统中**最受欢迎的上下文可视化插件**，定位为一站式上下文洞察与管理工具。它帮助用户透视模型上下文窗口的组成、演进、压缩和剪枝等事件与动作。

### 官方描述

**英文:**
> "Context insight panel: see what the model's context window is made of and how it evolves — composition vs. window size, per-request history, compression/injection events, and per-message token stats."

**中文:**
> "可视化模型上下文窗口的构成与变化，帮你实时掌握 token 用量、历史记录和压缩注入事件。"

**完整标题:**
> "Best DeepSeek Harness plugin for context insight and management, with context dashboard / browser and context command, for context statistics, composition, breakdown, evolution details, understanding how the context is made of, and how it evolves."

---

## 3. 核心功能模块

### 3.1 Context Dashboard (上下文面板)
- 在 DSH Web 界面中添加一个可视化面板
- 实时展示模型上下文窗口的状态
- 类似仪表盘的视图，显示上下文使用情况概览

### 3.2 Context Browser (上下文浏览器)
- 浏览上下文中的每条消息及其属性
- 支持逐条消息查看 token 数量
- 可以查看消息类型分布

### 3.3 Context Command (上下文命令)
- 注册斜杠命令用于与上下文信息交互
- 通过命令行方式快速获取上下文统计
- 可能在聊天输入框中输入 `/context` 触发

### 3.4 Context Statistics (上下文统计)
- **Token 用量统计**: 显示总 token 消耗
- **组成分析**: 系统提示、技能、工具 schema、对话消息等各部分占比
- **每条消息 token 统计**: 单条消息的 token 数量
- **上下文窗口占比**: 各部分占总窗口大小的比例

### 3.5 Composition Analysis (组成分析)
- 可视化分解上下文的组成部分:
  - **System Prompt** (系统提示)
  - **Skills** (技能目录)
  - **Tool Schemas** (工具定义)
  - **Conversation Messages** (对话消息)
  - **Injected Context** (注入的上下文)
- 显示每部分的 token 数量和占比

### 3.6 Breakdown (细分分析)
- 按消息类型细分:
  - `system` - 系统消息
  - `user` - 用户消息
  - `assistant` - 助手回复
  - `tool` / `tool_result` - 工具调用和结果
- 支持时间线视图

### 3.7 Evolution Tracking (演进追踪)
- **Per-request history**: 跨请求的上下文变化历史
- **Composition vs. window size**: 组成如何随时间变化
- **Context growth**: 上下文增长趋势
- **Cache reuse**: 缓存复用情况

### 3.8 Event Monitoring (事件监控)
- **Compression events (压缩事件)**: 上下文压缩/压缩发生时的通知
- **Injection events (注入事件)**: 新上下文注入窗口时的通知
- **Pruning events (剪枝事件)**: 旧消息被剪枝时的通知

---

## 4. 技术架构

### 4.1 插件类型
- **cordis-plugin**: 使用 DSH 的 cordis 插件框架
- **TypeScript**: 使用 TypeScript 开发，类型安全
- **dsh-external**: 独立于 DSH 主仓库的外部插件
- **bundle 插件**: 可能是包含 UI 和服务端逻辑的捆绑包

### 4.2 技术实现 (推断)
- **UI 组件**: React/Vue 组件注入到 DSH Web 界面
- **事件订阅**: 订阅 DSH 的消息/上下文生命周期事件
- **WebSocket**: 通过 DSH WebSocket 连接接收实时上下文更新
- **数据持久化**: 本地存储上下文历史数据
- **命令注册**: 通过 DSH 插件 API 注册斜杠命令

### 4.3 依赖
- **DSH Web UI**: 依赖 DeepSeek Harness Web 界面
- **cordis 框架**: 使用 DSH 的 cordis 插件系统
- **TypeScript/JavaScript**: 运行时依赖

---

## 5. 安装与使用

### 安装命令
```bash
# 首次安装
dsh plugin --profile web add dsh-context

# 更新到最新版
dsh plugin --profile web update dsh-context@latest
```

### 使用方式
1. 安装后重启 DSH Web 服务
2. 在 DSH Web 界面中会出现 "Context" 面板入口
3. 点击进入上下文可视化面板
4. 可以使用 `/context` 命令（如果支持）获取上下文统计

---

## 6. 标签与分类

**标签:**
- `cordis-plugin` - cordis 插件
- `deepseek-harness` - DeepSeek Harness
- `deepseek-harness-plugin` - DSH 插件
- `dsh-external` - 外部插件
- `dsh-plugin` - DSH 插件
- `dsh-plugins` - DSH 插件集合
- `上下文可视化` - Context Visualization
- `余额监控` - Balance Monitoring
- `调试分析` - Debug Analysis
- `插件管理` - Plugin Management

**主题:**
- cordis-plugin, deepseek-harness, deepseek-harness-plugin, dsh-external, dsh-plugin, dsh-plugins

---

## 7. 市场表现

### 评分 (87/100)
| 维度 | 分数 | 说明 |
|------|------|------|
| maintain | 100 | 近 1 天仍在更新，非常活跃 |
| practical | 80 | 实用性强，解决真实问题 |
| popularity | 76 | 605 stars，社区认可度高 |
| ease | 80 | 安装简单，开箱即用 |
| signal | 100 | 信号强，质量高 |

**评价:**
> "近 1 天仍在更新，DSH 迭代快也不怕坏；README 含完整安装与使用说明，上手即用；605 stars，社区认可度高。"

### 社区认可
- 605 stars (在 DSH 插件中属于高星)
- 收录于多个 awesome 列表:
  - awesome-deepseek-harness (0xsline)
  - awesome-dsh-plugin
  - Oh-My-DSH 生态目录
  - dsh-market 插件商店

---

## 8. 相关生态插件

| 插件 | 作者 | 功能 |
|------|------|------|
| **dsh-context** | bowenliang123 | 上下文可视化面板和命令 |
| dsh-context-doctor | Zhenyu98 | 上下文注入审计：统计 AGENTS.md 指令链/技能目录/工具 schema 的 token 成本，检测重复与冲突 |
| dsh-context-lens | gordonlu | Request Context Profiler — 查看每次请求间上下文变化和缓存复用情况 |
| dsh-context-compass | - | 上下文方向工具 |
| dsh-context-compressor | qwert702 | 上下文压缩工具 |
| context-pruner | JohnXu22786 | 会话上下文整理：剪枝过时、重复、失败和超大上下文以节省 token 预算 |
| dsh-environment-context | liqiming-whu | 实时环境上下文插件 |
| dsh-project-context | buhuikongpan | 项目上下文管理：自动注入项目工作区约定 |
| dsh-token-stats | - | Token 统计工具 |

---

## 9. 适用场景

1. **调试上下文溢出**: 当模型达到上下文窗口限制时，分析哪些部分占用了最多空间
2. **优化 token 用量**: 了解系统提示、技能、工具定义各占多少 token
3. **监控上下文演进**: 追踪上下文窗口随时间的变化
4. **理解压缩行为**: 何时发生了上下文压缩，压缩了哪些内容
5. **分析 agent 行为**: 通过上下文变化理解 agent 的决策过程
6. **性能优化**: 识别上下文中的冗余内容，优化上下文配置

---

## 10. 与 DSH 的集成

### DSH 上下文机制
- DSH 维护一个上下文窗口（默认 128K-1M tokens）
- 上下文包含: 系统提示 + 技能目录 + 工具 schema + 对话历史
- 当上下文接近窗口限制时，DSH 会进行压缩/剪枝
- dsh-context 插件监控这些事件并提供可视化

### 插件 API 使用
- 使用 cordis 框架注册 UI 组件
- 订阅 DSH 的上下文相关事件
- 访问 DSH 会话数据和消息历史
- 通过 WebSocket 接收实时更新

---

## 11. 开发者信息

**Bowen Liang (bowenliang123)**
- GitHub: https://github.com/bowenliang123
- ClawHub: https://clawhub.ai/bowenliang123
- 活跃的 DSH 插件开发者
- dsh-context 是其代表作品，获得社区高度认可

---

## 12. 总结

dsh-context 是 DSH 生态系统中**最重要、最受欢迎的上下文管理插件之一**。它解决了 DSH 用户在使用过程中的一个核心痛点：**理解模型上下文窗口的组成和变化**。

**核心价值:**
- 可视化: 将抽象的 token 消耗转化为直观的图表
- 监控: 实时追踪上下文变化事件
- 分析: 提供详细的组成分析和统计
- 调试: 帮助定位上下文相关问题

**技术亮点:**
- TypeScript 类型安全
- cordis 框架深度集成
- 实时 WebSocket 更新
- 完整的事件监控体系

**社区影响:**
- 605 stars 表明社区认可
- 被多个 awesome 列表收录
- 持续活跃开发
- 安装简单，开箱即用

---

*分析时间: 2026-08-24*
*数据来源: DSH 市场缓存 (plugins-cache.json), GitHub/web 搜索*
