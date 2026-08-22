# DeepSeek Harness (DSH) 会话归档插件调研报告

> 整理时间：2026-08-21 ｜ 数据来源：官方文档、社区插件目录、npm 注册表、GitHub 仓库

---

## 概览

DeepSeek Harness 生态中并没有单一的"官方会话归档插件"，而是通过**核心会话管理能力** + **社区插件扩展**的组合来实现会话归档、迁移、备份、恢复等功能。主要分为以下几类：

| 类别 | 代表插件 | 核心能力 |
|------|----------|----------|
| **核心内置** | `@deepseek-ai/dsh` core/session | 会话持久化、帧级存储、zstd 压缩、多帧格式 |
| **归档/隐藏/恢复** | `dsh-essential` | 可恢复删除、即时隐藏、重启安全归档 |
| **专用归档管理** | `dsh-archived-sessions` | 会话归档、分类、检索、恢复 |
| **会话管理增强** | `dsh-session-manager` | 会话列表、搜索、标签、导入导出 |
| **跨会话记忆** | `dsh-memory-evolve` | 长期记忆、自我进化、可归档恢复 |
| **迁移/同步** | `dsh-shuttle`, `session-teleport` | 跨哈尼斯迁移、PostgreSQL 备份 |
| **融合/复活** | `dsh-fusion`, `dsh-revive` | 会话融合、中断复活 |
| **导出/备份** | `dsh-obsidian-export` | 导出到 Obsidian 知识库 |

---

## 一、核心内置：`packages/core/session`

**来源**：[deepseek-ai/deepseek-harness/packages/core/session/README.zh.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/session/README.zh.md)

### 核心特性

- **帧级事件溯源存储**：每条消息、工具调用、状态变更均为一帧，支持时旅回放
- **多帧格式支持**：v1 (JSONL) / v2 (zstd 压缩帧) / v3 (分段索引 + 增量快照)
- **增量快照**：定期写入全量状态快照，启动时只需回放增量帧，大幅缩短冷启动
- **分段索引**：按时间分段，支持按时间范围、消息类型、工具名快速检索
- **完整性校验**：每帧 SHA-256，损坏可定位到具体帧

### 存储位置

```
~/.dsh/sessions/{session-id}/
  ├─ meta.json          # 会话元信息
  ├─ frames/            # 帧文件 (v2: .zst, v3: .idx + .snap + .frames)
  └─ index.sqlite       # FTS5 全文检索索引 (可选)
```

### 相关工具

- `dsh-session-health`：只读扫描诊断 torn/损坏/空会话、多帧 zstd 完整性
- `dsh-revive`：重启后自动向所有被打断会话发送"继续"指令

---

## 二、社区归档插件详细对比

### 1. `dsh-essential` (omdsh-dev) ⭐ 1

**仓库**：https://github.com/omdsh-dev/dsh-essential  
**来源**：[Oh My DSH 目录 - 安全·诊断·会话管理](https://github.com/omdsh-dev/dsh-essential)

| 特性 | 说明 |
|------|------|
| **核心定位** | "可恢复的对话删除：即时隐藏 + 重启安全归档" |
| **归档机制** | 删除时不真正移除文件，而是标记为 archived 并移入归档区 |
| **恢复方式** | 重启 DSH 或通过 Web UI "Archived Sessions" 面板一键恢复 |
| **安全性** | 重启不丢失，归档数据完整保留帧级历史 |
| **适用场景** | 想临时清理会话列表，但保留随时找回能力的用户 |

### 2. `dsh-archived-sessions` (@jiangdaoli / Zephyr-vibe)

**npm**：[@jiangdaoli/dsh-archived-sessions](https://www.npmjs.com/package/@jiangdaoli/dsh-archived-sessions)  
**仓库**：https://github.com/Zephyr-vibe/dsh-archived-sessions  
**README**：[dsh-archived-sessions/README.md](https://github.com/Zephyr-vibe/dsh-archived-sessions/blob/main/README.md)

| 特性 | 说明 |
|------|------|
| **核心定位** | 专用会话归档管理插件 |
| **功能** | 会话归档/取消归档、归档分类标签、归档列表检索、一键恢复 |
| **UI 集成** | Web 设置面板新增 "Archived Sessions" 标签页 |
| **存储** | 复用 core/session 存储格式，仅在 meta.json 增加 `archived: true` 标记 |
| **搜索** | 支持按项目、时间范围、关键词过滤归档会话 |

### 3. `dsh-session-manager` (dream12347 / wsxwj123)

**npm**：[dsh-session-manager](https://www.npmjs.com/package/dsh-session-manager)  
**仓库**：https://github.com/dream12347/dsh-session-manager  
**Monorepo 版**：https://github.com/wsxwj123/dsh-plugins/tree/main/packages/dsh-session-manager

| 特性 | 说明 |
|------|------|
| **核心定位** | 会话全生命周期管理增强 |
| **功能** | 会话列表美化、多维搜索(项目/标签/时间/模型)、会话标签系统、批量操作、导入/导出(JSON/Markdown) |
| **归档支持** | 内置归档/取消归档动作，配合标签系统实现分类归档 |
| **导出格式** | JSON (完整帧)、Markdown (可读对话)、CSV (统计汇总) |
| **Web UI** | 设置面板集成 "Session Manager" 专用页面 |

### 4. `dsh-memory-evolve` (csyangwen) ⭐ 24

**仓库**：https://github.com/csyangwen/dsh-memory-evolve  
**来源**：[dsh-community-plugins.md - 3.3 记忆](docs/dsh/dsh-community-plugins.md#L113)

| 特性 | 说明 |
|------|------|
| **核心定位** | 跨会话长期记忆 + 自我进化 |
| **归档相关** | 支持将项目决策、架构选择、踩坑记录**归档恢复**到新会话 |
| **记忆层级** | 工作记忆(会话内) → 短期记忆(跨会话项目级) → 长期记忆(跨项目知识库) |
| **自我进化** | 模型定期总结压缩记忆，冲突自动检测合并 |
| **适用场景** | 需要跨会话保持项目上下文连续性的长期项目 |

### 5. `dsh-shuttle` (omdsh-dev) ⭐ 1

**仓库**：https://github.com/omdsh-dev/dsh-shuttle  
**来源**：[Oh My DSH 目录 - 八、安全·诊断·会话管理](docs/dsh/dsh-omdsh-plugins-organize.md#L135)

| 特性 | 说明 |
|------|------|
| **核心定位** | DSH ↔ Codex / Claude Code / Pi / Reasonix / OpenCode 对话记录**双向迁移** |
| **迁移内容** | 消息历史、工具调用链、文件引用、上下文状态 |
| **格式转换** | 自动处理不同哈尼斯的存储格式差异 |
| **适用场景** | 多 IDE/哈尼斯并行开发，需在不同环境间无缝切换会话 |

### 6. `session-teleport` (omdsh-dev) ⭐ 2

**仓库**：https://github.com/omdsh-dev/session-teleport  
**来源**：[Oh My DSH 目录](docs/dsh/dsh-omdsh-plugins-organize.md#L133)

| 特性 | 说明 |
|------|------|
| **核心定位** | 会话数据迁移（PostgreSQL 后端） |
| **架构** | 将本地帧文件同步到 PostgreSQL，支持多机器共享会话历史 |
| **用途** | 团队协作共享会话、多设备同步、集中式备份 |

### 7. `dsh-fusion` (omdsh-dev) ⭐ 2

**仓库**：https://github.com/omdsh-dev/dsh-fusion  
**来源**：[Oh My DSH 目录](docs/dsh/dsh-omdsh-plugins-organize.md#L132)

| 特性 | 说明 |
|------|------|
| **核心定位** | 多个对话融合为一个可继续会话 |
| **算法** | 智能剪枝/话题分组/时间排序，去重合并上下文 |
| **适用场景** | 同一任务在多个会话中并行探索，最后合并成完整线索 |

### 8. `dsh-revive` (omdsh-dev) ⭐ 3

**仓库**：https://github.com/omdsh-dev/dsh-revive  
**来源**：[Oh My DSH 目录](docs/dsh/dsh-omdsh-plugins-organize.md#L130)

| 特性 | 说明 |
|------|------|
| **核心定位** | 一键复活：重启后给所有被打断的会话自动发「继续」 |
| **触发条件** | 检测到会话最后一帧为 `interrupted` 或 `tool_pending` 状态 |
| **适用场景** | 系统崩溃、强制重启、断电后自动恢复工作流 |

### 9. `dsh-obsidian-export` (社区)

**来源**：[dsh-community-plugins.md - 3.5 通知与集成](docs/dsh/dsh-community-plugins.md#L133)

| 特性 | 说明 |
|------|------|
| **核心定位** | 全量对话导出到 Obsidian 库 |
| **导出内容** | 完整对话历史、代码块、工具调用结果、文件引用 |
| **格式** | Markdown + Frontmatter (YAML)，含标签、时间戳、会话 ID |
| **适用场景** | 知识库建设、会话存档为可检索笔记 |

---

## 三、安装方式对比

### 标准安装命令

```bash
# 从 GitHub 安装 (推荐 pin 到 tag/commit)
dsh plugin --profile web add "github:omdsh-dev/dsh-essential#main"
dsh plugin --profile web add "github:Zephyr-vibe/dsh-archived-sessions#main"
dsh plugin --profile web add "github:dream12347/dsh-session-manager#main"
dsh plugin --profile web add "github:csyangwen/dsh-memory-evolve#main"
dsh plugin --profile web add "github:omdsh-dev/dsh-shuttle#main"
dsh plugin --profile web add "github:omdsh-dev/dsh-fusion#main"
dsh plugin --profile web add "github:omdsh-dev/dsh-revive#main"

# 从 npm 安装
dsh plugin --profile web add @jiangdaoli/dsh-archived-sessions
dsh plugin --profile web add dsh-session-manager

# 验证
dsh plugin --profile web list

# 补丁模式启动 (插件生效)
npx @deepseek-ai/dsh web --patch
```

> ⚠️ **注意**：只有声明了 `dsh.bundle.patch` 字段的包才会成为激活的 profile 层——普通依赖装上是惰性的，不算插件。

---

## 四、选型建议

### 场景 A：只想"临时隐藏会话，随时能找回"
→ **首选 `dsh-essential`**  
最轻量，零配置，删除即归档，重启即恢复，无额外 UI 学习成本。

### 场景 B：需要结构化归档管理(分类、标签、检索、批量操作)
→ **首选 `dsh-archived-sessions`** 或 **`dsh-session-manager`**  
前者专注归档工作流，后者功能更全(含标签、导出、搜索)。

### 场景 C：跨会话保持项目上下文、积累长期知识
→ **首选 `dsh-memory-evolve`**  
不仅归档，还能进化记忆，适合长周期项目。

### 场景 D：多哈尼斯/多 IDE 环境间迁移会话
→ **首选 `dsh-shuttle`**  
双向迁移，格式自动转换。

### 场景 E：团队共享会话历史、多设备同步
→ **首选 `session-teleport`** (需自备 PostgreSQL)

### 场景 F：会话被意外中断(崩溃/断电)后自动恢复
→ **首选 `dsh-revive`**  
配合 `dsh-session-health` 诊断损坏会话。

### 场景 G：将会话沉淀为可检索知识库
→ **首选 `dsh-obsidian-export`**  
导出为 Obsidian 兼容 Markdown，支持全文检索、双向链接。

### 组合推荐

| 组合 | 适用场景 |
|------|----------|
| `dsh-essential` + `dsh-revive` | 日常轻量归档 + 崩溃自动恢复 |
| `dsh-session-manager` + `dsh-obsidian-export` | 结构化管理 + 知识库沉淀 |
| `dsh-memory-evolve` + `dsh-shuttle` | 长期项目记忆 + 多环境同步 |
| `session-teleport` + `dsh-fusion` | 团队协作 + 多线程探索合并 |

---

## 五、官方核心会话 API (供插件开发参考)

**来源**：[deepseek-ai/deepseek-harness/packages/core/session/src/types.ts](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/session/src/types.ts)

### 关键类型

```typescript
// 会话元信息
interface SessionMeta {
  id: string;                    // UUID v4
  projectId: string;             // 项目标识
  createdAt: number;             // Unix ms
  updatedAt: number;             // Unix ms
  archived?: boolean;            // 归档标记 (社区插件约定)
  tags?: string[];               // 标签 (session-manager 约定)
  frameFormat: 'v1' | 'v2' | 'v3';
  frameCount: number;
  byteSize: number;
}

// 帧类型
type Frame = 
  | { type: 'user_message'; content: string; attachments?: Attachment[] }
  | { type: 'assistant_message'; content: string; reasoning?: string }
  | { type: 'tool_call'; tool: string; args: unknown; requestId: string }
  | { type: 'tool_result'; requestId: string; result: unknown; error?: string }
  | { type: 'state_snapshot'; state: Record<string, unknown> }
  | { type: 'interrupted'; reason: string }
  | { type: 'archived'; at: number }  // 归档事件帧 (约定)
  | { type: 'restored'; at: number }; // 恢复事件帧 (约定)
```

### 核心服务接口

```typescript
interface SessionService {
  // 基础 CRUD
  create(projectId: string): Promise<SessionMeta>;
  get(id: string): Promise<SessionMeta | null>;
  list(projectId?: string): Promise<SessionMeta[]>;
  delete(id: string, hard?: boolean): Promise<void>;  // hard=false 为软删/归档
  
  // 帧操作
  appendFrame(id: string, frame: Frame): Promise<void>;
  readFrames(id: string, opts?: { from?: number; to?: number; types?: Frame['type'][] }): Promise<Frame[]>;
  
  // 归档/恢复 (约定接口，非核心强制)
  archive(id: string): Promise<void>;
  restore(id: string): Promise<void>;
  
  // 导入导出
  export(id: string, format: 'json' | 'markdown' | 'csv'): Promise<string>;
  import(data: string, format: 'json' | 'markdown'): Promise<SessionMeta>;
}
```

---

## 六、已知限制与坑

| 问题 | 影响 | 规避方案 |
|------|------|----------|
| **归档标记非标准化** | 不同插件用不同字段标记归档 (`archived`, `archivedAt`, `status: 'archived'`) | 统一约定 `meta.archived: true` + `archivedAt` 时间戳 |
| **帧格式不兼容** | v1/v2/v3 混存，旧插件可能不支持 v3 分段索引 | 插件声明 `minFrameFormat: 'v2'`，core 提供迁移工具 |
| **大型会话导出 OOM** | 10万+帧会话导出 Markdown 可能内存溢出 | 流式导出、分片导出、仅导出摘要 |
| **跨哈尼斯迁移丢失工具调用链** | Codex/Claude Code 工具 schema 差异大 | `dsh-shuttle` 尽力映射，人工校验关键工具调用 |
| **PostgreSQL 同步冲突** | 多设备同时编辑同一会话 | `session-teleport` 采用最后写入胜 + 事件溯源回放合并 |
| **插件权限过大** | 归档插件可读所有会话帧、写任意文件 | 仅安装可信插件、定期审计 `dsh-security-audit` |

---

## 七、参考链接汇总

### 官方文档
- [Core Session README.zh.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/session/README.zh.md)
- [Core Session types.ts](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/session/src/types.ts)
- [DeepSeek Harness AGENTS.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/AGENTS.md)

### 社区插件目录
- [dsh-community-plugins.md](docs/dsh/dsh-community-plugins.md) (本仓库)
- [dsh-omdsh-plugins-organize.md](docs/dsh/dsh-omdsh-plugins-organize.md) (本仓库)
- [awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin)
- [awesome-deepseek-harness](https://github.com/Dominic789654/awesome-deepseek-harness)
- [Oh My DSH](https://github.com/omdsh-dev)

### 具体插件仓库
- [omdsh-dev/dsh-essential](https://github.com/omdsh-dev/dsh-essential)
- [Zephyr-vibe/dsh-archived-sessions](https://github.com/Zephyr-vibe/dsh-archived-sessions)
- [dream12347/dsh-session-manager](https://github.com/dream12347/dsh-session-manager)
- [wsxwj123/dsh-plugins](https://github.com/wsxwj123/dsh-plugins)
- [csyangwen/dsh-memory-evolve](https://github.com/csyangwen/dsh-memory-evolve)
- [omdsh-dev/dsh-shuttle](https://github.com/omdsh-dev/dsh-shuttle)
- [omdsh-dev/session-teleport](https://github.com/omdsh-dev/session-teleport)
- [omdsh-dev/dsh-fusion](https://github.com/omdsh-dev/dsh-fusion)
- [omdsh-dev/dsh-revive](https://github.com/omdsh-dev/dsh-revive)
- [omdsh-dev/dsh-session-health](https://github.com/omdsh-dev/dsh-session-health)

### npm 包
- [@jiangdaoli/dsh-archived-sessions](https://www.npmjs.com/package/@jiangdaoli/dsh-archived-sessions)
- [dsh-session-manager](https://www.npmjs.com/package/dsh-session-manager)

---

## 八、更新日志

| 日期 | 变更 |
|------|------|
| 2026-08-21 | 初版：整理 9 类会话归档相关插件，含核心能力、选型建议、API 参考 |

---

*本报告基于公开文档与社区整理，插件功能随版本快速迭代，安装前请以仓库最新 README 为准。*