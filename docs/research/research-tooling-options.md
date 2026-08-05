# Research Tooling Options

> **来源**：info-collector 退役后的替代方案调研（ADR 0065）
> **日期**：2026-08-05
> **状态**：决策参考。具体选型由实际调研需求驱动。
> **相关**：[GitHub 开源 deep-research 调研](../references/github-deep-research-opensource.md) 更详细的开源项目列表

## 选型矩阵

按调研深度和场景分三档：

| 档位 | 场景 | 推荐方案 | 风格 |
|---|---|---|---|
| 轻量 | 快速了解某技术 / 框架 / 概念 | Matt Pocock research skill | 纯 prompt，零代码 |
| 中量 | 系统性技术选型 / 竞品对比 / 可行性评估 | Anthropic deep-research 或 omo ulw-research | 内置 pipeline |
| 重量 | 学术调研 / 多轮深挖 / 需要溯源到一手资料 | GitHub 开源 deep-research 生态 | 可定制 |

---

## 轻量调研：Matt Pocock research skill

**位置**：mattpocock/skills 仓库（GitHub 16 万★）

**形态**：单一 SKILL.md，纯 prompt 指令，零代码。

**适用场景**：
- "X 是什么 / 怎么用 / 与 Y 有什么区别"
- 快速技术调研，不需要严格溯源
- 单次会话内可完成的调研

**不适用场景**：
- 需要结构化 claims 验证
- 多轮迭代深挖
- 严格的多源交叉验证

**优势**：
- 零维护，纯 prompt
- 与 Claude Code / OpenCode / Cursor 等 agent harness 兼容
- 社区验证，迭代成熟

**劣势**：
- 无结构化输出
- 无来源验证机制
- 依赖 agent 自律执行

**调用方式**：将 SKILL.md 放入 `.opencode/skills/research/SKILL.md`（或对应 harness 的 skill 目录），agent 自动识别 `/research` 触发。

---

## 中量调研：两个推荐路径

### 路径 A：Anthropic deep-research（推荐）

**位置**：Anthropic 官方提供的 deep-research 能力（Claude 平台内置）

**适用场景**：
- 系统性技术调研
- 需要多源综合 + 引用
- 可接受单次调研（非迭代）

**优势**：
- 官方维护，质量保证
- 内置多源搜索 + 引用追溯
- 无需自己搭 pipeline

**劣势**：
- 闭源，不可定制
- 依赖 Anthropic 平台
- 无法嵌入自己的工作流

**调用方式**：通过 Claude 平台直接使用。

### 路径 B：omo ulw-research（omo 框架内置）

**位置**：oh-my-openagent 框架的内置 skill（见 [docs/research/oh-my-openagent-architecture.md](oh-my-openagent-architecture.md) §10.2）

**适用场景**：
- 已使用 omo 框架
- 需要与 omo 的其他 agent / skill 协作
- 饱和研究（深度调研某个主题直到信息饱和）

**优势**：
- 与 omo 框架原生集成
- 支持 ultrawork（`ulw`）全自动编排
- 跨 harness 共享（OMO 与 Codex 间）

**劣势**：
- 依赖 omo 框架
- 文档较少，主要在 omo 生态内
- "饱和研究"语义偏重，可能不适合轻量场景

**调用方式**：在 omo 环境中通过 `ulw-research` skill 触发。

---

## 重量调研：GitHub 开源生态

**完整列表**：见 [docs/references/github-deep-research-opensource.md](../references/github-deep-research-opensource.md)

以下按使用场景挑选推荐项：

### 推荐 1：dzhng/deep-research（参考实现）

- **GitHub**：https://github.com/dzhng/deep-research
- **规模**：<500 行 TypeScript，19.1k★
- **特点**：原始参考实现，广度/深度参数控制迭代式研究
- **适用**：想理解 deep-research 的核心机制，或基于它二次开发
- **可换**：DeepSeek-R1 / 自定义端点

### 推荐 2：claude-deep-research (arm3n)

- **GitHub**：https://github.com/arm3n/claude-deep-research
- **特点**：6 个搜索引擎并行（Brave/Exa/Tavily/Perplexity/Firecrawl/Context7），100+ 来源
- **适用**：Claude Code 用户，需要生产可用配置
- **含**：install.sh，会话上下文保护

### 推荐 3：Claude Research Orchestrator (sylweriusz)

- **GitHub**：https://github.com/sylweriusz/claude-research-orchestrator
- **特点**：Graph of Thoughts 实现，5 个专门研究 agent
- **适用**：需要多角度三角验证 + 来源评级
- **输出**：25-35 页报告 + HTML 可视化

### 推荐 4：langchain-ai/open_deep_research（通用框架）

- **GitHub**：https://github.com/langchain-ai/open_deep_research
- **特点**：LangGraph 实现，跨多模型/搜索工具/MCP
- **适用**：想用 LangChain 生态，或需要部署到 LangGraph Platform
- **含**：Deep Research Bench 排行榜

### 推荐 5：LearningCircuit/local-deep-research（本地可运行）

- **GitHub**：https://github.com/LearningCircuit/local-deep-research
- **特点**：支持 Ollama 本地模型 + 云端模型
- **适用**：隐私敏感 / 离线场景
- **集成**：arXiv / PubMed / Wikipedia / RAG 私有文档

### 推荐 6：aayii2025/deep-research（中文友好）

- **GitHub**：https://github.com/aayii2025/deep-research
- **特点**：8 步方法论，L1-L4 来源分级，事实卡片 + 显式推导链
- **适用**：中文场景，学术优先
- **MIT**，含中文文档

---

## 选型决策树

```
你的调研需求是什么？
│
├─ 快速了解一个概念 / 技术
│  → Matt Pocock research skill（轻量）
│
├─ 系统性技术调研 / 选型对比
│  ├─ 已用 omo 框架？
│  │  → omo ulw-research（中量）
│  ├─ 否？
│  │  → Anthropic deep-research（中量，官方）
│  │
├─ 学术调研 / 多轮深挖 / 严格溯源
│  ├─ 用 Claude Code？
│  │  → claude-deep-research (arm3n) 或 Claude Research Orchestrator
│  ├─ 用 LangChain 生态？
│  │  → langchain-ai/open_deep_research
│  ├─ 需要本地运行？
│  │  → LearningCircuit/local-deep-research
│  ├─ 中文场景？
│  │  → aayii2025/deep-research
│  └─ 想理解核心机制 / 二次开发？
│     → dzhng/deep-research（参考实现）
│
└─ 需要结构化 claims + 确定性 source verification？
   → 无现成方案（见下"已知缺口"）
```

---

## 已知缺口：结构化 claims + 确定性 source verification

info-collector 退役后，**没有任何替代方案提供**：

1. **结构化 claims schema**（evidence_type / confidence / precision / metric_type / source_metadata）
2. **确定性 source verification**（confirmed / absent / indirect 三级别，由代码计算而非 LLM 自报）
3. **†/‡ 可见标记** 让 fabrication 可见

**这是否是问题？**

按 info-collector ADR 0028 的 "research starting point" 定位——**不是问题**。用户本来就要 verify，prompt 自标的 70-80% 准确率对 starting point 足够。

**如果未来真的需要**：

不要重建 info-collector 规模的 pipeline。更轻的路径：
1. 用上述任一 deep-research 工具产出 markdown 报告
2. 写一个 ~200 行的 Python 后处理脚本：解析 markdown 中的 `[N]` 引用 → fetch 对应 URL → 数字匹配 → 标记 †/‡
3. 牺牲结构化 claims schema，保留确定性验证

这条路径的前提是——**确实有场景需要 100% 准确的数字溯源**。若无此场景，prompt 模板（见 [source-verification-protocol.md](../../skills/info-collector/references/source-verification-protocol.md)）就够。

---

## 从 info-collector 迁移的注意事项

### 保留可用的资产

| 资产 | 位置 | 用途 |
|---|---|---|
| 通用写作指南 | [docs/research/research-writing-guide.md](research-writing-guide.md) | 任何调研 agent 的写作品味指南 |
| source_verification prompt 模板 | [skills/info-collector/references/source-verification-protocol.md](../../skills/info-collector/references/source-verification-protocol.md) | 让任何 research agent 自标 †/‡ |
| 64 个 ADR | skills/info-collector/docs/adr/ | 设计决策历史，可回溯 |
| config.json 的 4-tier source 列表 | skills/info-collector/config.json | 手动调研时的来源参考 |

### 放弃的资产

| 资产 | 原因 |
|---|---|
| fetcher / batch_fetch / fetch_router / fetch_strategies | 重造 webfetch + exa 的轮子 |
| search_gate / 7 个 check | gate 拉低 throughput，LLM 自判 + grill-me 引导更有效 |
| claim_validator 11 个 check | 大部分是 AI-verifying-AI 反模式 |
| trust_boundary / repair_loop / deep_dive | 同上 |
| report_checks | markdownlint 的活 |
| proceed.py 的 gate dispatch | 整个 pipeline 编排，替代方案自带 |

### 迁移路径

1. **新调研**：直接用上述选型矩阵选工具
2. **存量 info-collector 产物**（.workdir/ 下的 analysis.json / collected.json）：可手动转为 markdown 报告，或保留作历史参考
3. **引用 info-collector 报告的下游文档**：原报告仍可读，†/‡ 标记仍有效（标记是文本，不依赖代码）

---

## 后续维护

本文档和 [docs/research/research-writing-guide.md](research-writing-guide.md) 是 info-collector 退役后保留的活文档。GitHub 开源生态列表（[docs/references/github-deep-research-opensource.md](../references/github-deep-research-opensource.md)）随时间变化，建议每 6 个月或需要选型时更新一次。

若发现新的优秀 research skill / 工具，append 到对应表格即可。
