# GitHub 上开源实现的「Deep Research」（含 Claude /deep-research 对标项目）

> 搜集时间：2026-07-30
> 说明：Deep Research 最初由 OpenAI 于 2025 年初推出，随后 Gemini、Claude（Anthropic Research）、Perplexity、Grok 等纷纷跟进。开源社区围绕这一范式涌现出大量实现，既有直接对标 **Claude Code /deep-research** 的插件/Skill，也有基于 **Claude API** 的独立应用，以及支持多模型的通用框架。以下按类别整理。

---

## 一、Claude Code 专属插件 / Skill（直接对标 /deep-research）

这些项目把 Claude Code 包装成多源研究智能体，通常通过 `SKILL.md` / `commands` / `agents` 与 MCP 搜索服务配合。

| 项目 | 链接 | 亮点 | 备注 |
|---|---|---|---|
| claude-deep-research (arm3n) | https://github.com/arm3n/claude-deep-research | 6 个搜索引擎并行（Brave/Exa/Tavily/Perplexity/Firecrawl/Context7），100+ 来源，置信度评分，会话上下文保护（handover + hooks） | 生产可用配置，含 install.sh |
| Deep Research Agent (SwaroopMeher) | https://github.com/SwaroopMeher/deep-research-agent | 并行子代理 + 递归规划，灵感来自 Gemini；20+ 来源类型、查询变体、验证阶段、持久化记忆 | 5 层来源覆盖 |
| Claude Research Orchestrator (sylweriusz) | https://github.com/sylweriusz/claude-research-orchestrator | Graph of Thoughts 实现，5 个专门研究 agent（多角度/三角验证/CoD 合成/安全校验/定稿），A-E 来源评级 | 输出 25-35 页报告 + HTML 可视化 |
| claude-deep-research-skill (abossenbroek) | https://github.com/abossenbroek/claude-deep-research-skill | 8.5 阶段研究流水线，Graph-of-Thoughts，自动续写（50K-100K+ 字），CiteGuard 引文校验，支持 MD/HTML/PDF | 约 789★；含 CLI |
| claude-deep-reasearch (SipengXie2024) | https://github.com/SipengXie2024/claude-deep-reasearch | 官方插件系统（`/plugin install`），GoT 框架 + 7 阶段 + 多 agent 团队，学术优先（arXiv/Google Scholar/PubMed MCP） | 命令空间 `/deep-research:*` |
| simple_claude_deep_research_agent (liangdabiao) | https://github.com/liangdabiao/simple_claude_deep_research_agent | 简化版 3 类 agent（主导/子代理/引用），仅用 Web 工具，三种查询分类 | 中文文档，教育用途 |
| aiecplugin (LZH736467214) | https://github.com/LZH736467214/aiecplugin | 多跳探索 + 专家框架分析（Christensen/Porter 等），来源可信度分级 | 含 `/research` `/analyze` 命令 |
| oh-rid/deep-research | https://github.com/oh-rid/deep-research | 三方三角验证（Claude + Gemini + GPT），主源核验、防幻觉、沙箱隔离 | 偏安全/事实核查 |
| deep-research (wshuyi / aayii2025) | https://github.com/aayii2025/deep-research | 8 步方法论，L1-L4 来源分级，事实卡片 + 显式推导链，中文友好 | MIT，含中文文档 |

---

## 二、基于 Claude API 的独立应用（dzhng 原始实现的衍生）

| 项目 | 链接 | 亮点 | 备注 |
|---|---|---|---|
| dzhng/deep-research | https://github.com/dzhng/deep-research | **原始参考实现**，<500 行 TypeScript，广度/深度参数控制迭代式研究；递归「搜索→阅读→思考」循环 | 约 19.1k★，MIT；可换 DeepSeek-R1 / 自定义端点 |
| deep-research-with-claude (hakansoren) | https://github.com/hakansoren/deep-research-with-claude | dzhng 项目改用 **Claude API** 的改版，Firecrawl 搜索 + Claude 分析，Docker 化 | MIT |

> 其他 dzhng 衍生：社区 Python 移植 `Finance-LLMs/deep-research-python`；`mbrukman/dzhng-deep-research` 等镜像。

---

## 三、通用开源 Deep Research 框架（支持 Claude / 多模型）

| 项目 | 链接 | 亮点 | 备注 |
|---|---|---|---|
| langchain-ai/open_deep_research | https://github.com/langchain-ai/open_deep_research | LangGraph 实现，跨多模型/搜索工具/MCP；Deep Research Bench 排行榜前列 | 配置化、可部署到 LangGraph Platform |
| assafelovic/gpt-researcher | https://github.com/assafelovic/gpt-researcher | 老牌自治研究 agent，自动生成带引用的报告 | 生态成熟 |
| mshumer/OpenDeepResearcher | https://github.com/mshumer/OpenDeepResearcher | Matt Shumer 的极简开源实现 | |
| LearningCircuit/local-deep-research | https://github.com/LearningCircuit/local-deep-research | **本地可运行**，支持 Ollama 本地模型 + 云端模型，集成 arXiv/PubMed/Wikipedia/RAG 私有文档 | 约 1.4k★，含 Web UI |
| jina-ai/node-DeepResearch | https://github.com/jina-ai/node-DeepResearch | Jina 出品，Web 搜索找答案 | |
| HKUDS/Auto-Deep-Research | https://github.com/HKUDS/Auto-Deep-Research | 港大出品，自动化深度研究 agent | |
| google-gemini/gemini-fullstack-langgraph-quickstart | https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart | Gemini + LangGraph 全栈示例 | |
| zilliztech/deep-searcher | https://github.com/zilliztech/deep-searcher | 基于 Milvus，面向**私有数据**的深度研究 | Python |
| nickscamara/open-deep-research | https://github.com/nickscamara/open-deep-research | Python 实现 | |
| btahir/open-deep-research | https://github.com/btahir/open-deep-research | 早期开源实现之一 | |

---

## 四、资源汇总 / Awesome 列表（持续更新，适合作为索引）

| 项目 | 链接 | 内容 |
|---|---|---|
| hanjanghoon/Awesome-Deep-Research | https://github.com/hanjanghoon/Awesome-Deep-Research | Agentic Deep Research 资源汇总（产品/开源实现/论文/基准）+ 立场论文 |
| Necolizer/awesome-deep-research-agent | https://github.com/Necolizer/awesome-deep-research-agent | 学术论文导向，附「Deep Research Agents: A Systematic Examination And Roadmap」综述 |
| Stars1233/Awesome-Deep-Research | https://github.com/Stars1233/Awesome-Deep-Research | 按时间线更新的论文/基准表格（含模型、优化方法、数据集） |
| DavidZWZ/Awesome-Deep-Research | https://github.com/DavidZWZ/Awesome-Deep-Research | 12 家机构联名论文配套的项目主页/汇总 |

---

## 五、选型建议

- **只想在 Claude Code 里用 `/deep-research`**：优先看 `arm3n/claude-deep-research`（功能全、生产可用）或 `abossenbroek/claude-deep-research-skill`（报告质量高、中文友好选 `aayii2025/deep-research`）。
- **想要独立可部署的研究服务**：`langchain-ai/open_deep_research` 或 `assafelovic/gpt-researcher`。
- **隐私/本地优先**：`LearningCircuit/local-deep-research`（支持本地模型 + 私有文档 RAG）。
- **理解原理 / 自己改**：`dzhng/deep-research`（<500 行，最佳教学参考）。
- **找更多项目 / 追踪前沿**：直接逛四类 Awesome 列表。

> 提示：多数项目需要自备 API Key（Claude / OpenAI / Firecrawl / Tavily / Exa 等），且多为社区维护，星星数与功能会随时间变化，使用前请以仓库最新 README 为准。
