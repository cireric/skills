# Info-Collector 测试提示词

用于端到端测试 info-collector skill 的标准化提示词。每个提示词设计为触发不同的 goal_type 和代码路径，覆盖 gate 边界条件。

## 使用方式

1. 在目标项目目录中启动 opencode
2. 输入 `/info-collector`
3. 当 skill 询问时，按提示词中的回答逐项回复
4. 验证最终报告是否满足"预期检查点"

---

## T1: tech_selection — 标准量化路径

> 研究 2025-2026 年主流 AI coding agent 框架的技术选型，包括 Claude Code、Cursor、Windsurf、Cline、Aider 等。重点关注 SWE-bench 成绩、架构差异、生产环境适配性。

**回答指引：**
- topic: `2025-2026 AI coding agent 框架技术选型`
- english_title: `ai-coding-agent-framework-selection-2025-2026`
- goal_type: `tech_selection`
- depth: `standard`
- audience: `engineer`
- scope_description: `评估主流 AI coding agent 框架的技术特征、性能指标和生产就绪度，为团队选型提供依据`
- search_directions: `["SWE-bench benchmark scores", "architecture comparison agentic coding", "production deployment experience"]`
- report_language: `zh`

**预期检查点：**
- [ ] scope→search gate 通过
- [ ] search→analysis gate 通过（source_fidelity BLOCKER 若 >30% 浅内容）
- [ ] analysis.json 包含 `overview` + `comparison` + `recommendation` + `methodology` 四个 section
- [ ] recommendation section 含 `不推荐` 或 `not recommended`
- [ ] methodology section 含 Markdown 表格
- [ ] 每个 claim 有 evidence_type/confidence/precision
- [ ] 最终报告引用格式为 `[&#91;N&#93;](#refs)` 可点击链接
- [ ] Front matter 含 `review_status` + `verification_required: true`

---

## T2: exploratory — 非量化中文主题

> 探索 RISC-V 在中国半导体产业中的发展现状和未来趋势

**回答指引：**
- topic: `RISC-V 在中国半导体产业的发展现状与趋势`
- english_title: `risc-v-china-semiconductor-trends`
- goal_type: `exploratory`
- depth: `deep`
- audience: `CTO`
- scope_description: `全景式了解 RISC-V 在中国的产业生态、政策支持、技术路线和商业化进展`
- search_directions: `["RISC-V ecosystem China", "RISC-V chip design adoption", "policy support open-source ISA"]`
- report_language: `zh`

**预期检查点：**
- [ ] 非量化 goal_type → 无 methodology section
- [ ] 至少 2 个 section（overview 必需）
- [ ] 每个 section 有 key_insights（≥2 个）
- [ ] CJK search direction 触发 topic_coverage WARN 而非 BLOCKER（如果未覆盖）
- [ ] depth=deep → 每方向至少 5 个 source
- [ ] 英文搜索词为主，中文域名用中文搜索

---

## T3: fact_check — 最小化路径

> 验证 "Rust 语言在 2025 年内存安全漏洞率比 C/C++ 低 70%" 这一说法

**回答指引：**
- topic: `Verify: Rust memory safety vulnerability rate 70% lower than C/C++ in 2025`
- goal_type: `fact_check`
- depth: `quick`
- audience: `researcher`
- scope_description: `Fact-check the claim that Rust has 70% fewer memory safety vulnerabilities than C/C++`
- search_directions: `["Rust memory safety statistics", "C C++ vulnerability CVE comparison"]`
- report_language: `en`

**预期检查点：**
- [ ] fact_check 路由：entry_tier=1, path=[1,2,4]
- [ ] depth=quick → 每方向至少 1 个 source
- [ ] analysis.json 包含 `claims` + `evidence` + `conclusion` 三个 section
- [ ] claim 的 precision 应为 `qualitative` 或 `range`（非 `exact`，除非有官方数据）
- [ ] source_verification 应标注 source_confirmed/source_absent/source_indirect

---

## T4: academic_research — arXiv 重写路径

> 调研大语言模型在代码生成任务上的最新评估方法，重点关注 SWE-bench 和 HumanEval 之外的新基准

**回答指引：**
- topic: `LLM code generation evaluation benchmarks beyond SWE-bench and HumanEval`
- goal_type: `academic_research`
- depth: `standard`
- audience: `researcher`
- scope_description: `Survey new evaluation benchmarks for LLM code generation since 2024`
- search_directions: `["LLM code generation benchmark 2024 2025", "beyond SWE-bench evaluation", "code generation assessment methodology"]`
- report_language: `en`

**预期检查点：**
- [ ] arxiv.org URL 触发 ArxivStrategy 重写为 ar5iv.labs.arxiv.org
- [ ] academic_research 路由：path=[1], optional_tiers=[2]
- [ ] analysis.json 含 `abstract` + `findings` + `references` + `methodology` 四个 section
- [ ] Tier 1 source 占比较高（source_tier_balance 检查）
- [ ] fetch 路径：Path A 先尝试 webfetch，content_insufficient 则 Path B (exa)

---

## T5: market_analysis — Tier 4 覆盖

> 分析 2025-2026 年全球 AI 编程助手市场规模、竞争格局和增长预测

**回答指引：**
- topic: `2025-2026 global AI coding assistant market analysis`
- goal_type: `market_analysis`
- depth: `standard`
- audience: `CTO`
- scope_description: `Analyze the global AI coding assistant market size, competitive landscape, and growth forecasts for 2025-2026`
- search_directions: `["AI coding assistant market size forecast", "coding tool market share 2025", "developer tool adoption rate"]`
- report_language: `zh`

**预期检查点：**
- [ ] market_analysis 路由：path=[3,4,1,2] — Tier 4 (community) 排第二
- [ ] 市场数据 claim 应标 evidence_type 为 `third_party_estimate`（非 `official_data`）
- [ ] vendor_affiliation 字段标注数据来源方（如 "Gartner", "Statista"）
- [ ] precision 应为 `range` 或 `qualitative`（非 `exact`，因为是市场预测）
- [ ] 最终报告含 `overview` + `data` + `trends` + `conclusion` + `methodology`

---

## T6: competitive_comparison — 比较表格

> 对比 Claude Code、GitHub Copilot、Cursor 在企业级开发场景下的能力差异

**回答指引：**
- topic: `Claude Code vs GitHub Copilot vs Cursor enterprise comparison`
- goal_type: `competitive_comparison`
- depth: `deep`
- audience: `CTO`
- scope_description: `Compare Claude Code, GitHub Copilot, and Cursor for enterprise development scenarios`
- search_directions: `["Claude Code enterprise features", "GitHub Copilot enterprise deployment", "Cursor IDE team collaboration"]`
- report_language: `en`

**预期检查点：**
- [ ] competitive_comparison 路由：path=[2,1,3,4]
- [ ] comparison section 必须含 Markdown 表格
- [ ] recommendation section 含 `not recommended`
- [ ] 每个 claim 的 source_urls 必须在 collected.json 中
- [ ] 每个 claim 的 source_urls 必须作为 `{{ref:URL}}` 出现在同 section content 中
- [ ] 不同 metric_type 不可混在同一 section（metric_type_homogeneity）

---

## T7: background_check — 中文域名

> 调查 DeepSeek 的技术架构、开源策略和社区评价

**回答指引：**
- topic: `DeepSeek 技术架构与开源策略调查`
- english_title: `deepseek-architecture-open-source-investigation`
- goal_type: `background_check`
- depth: `standard`
- audience: `engineer`
- scope_description: `调查 DeepSeek 的技术架构特征、开源模型策略和社区反馈`
- search_directions: `["DeepSeek V3 architecture", "DeepSeek open source model strategy", "DeepSeek community review"]`
- report_language: `zh`

**预期检查点：**
- [ ] background_check 路由：path=[3,2,1,4]
- [ ] 中文域名（zhihu.com 等）触发中文搜索查询
- [ ] github.com URL 触发 GithubStrategy 重写（指向 README.md）
- [ ] search_plan 中 zh 任务和 en 任务分开生成
- [ ] report_language=zh → 报告标签用中文（"数据来源"、"参考文献"）

---

## T8: CLI fetch 独立测试

不通过 skill 流程，直接测试 CLI fetch 子命令：

```powershell
# 设置环境
$env:PYTHONPATH = "D:\Project\source\__TEST__\cireric-skills\skills\info-collector"

# T8.1: 普通 URL autonomous fetch
.venv\Scripts\python.exe -m scripts.cli fetch https://example.com --tier 3

# T8.2: arXiv PDF URL（触发重写）
.venv\Scripts\python.exe -m scripts.cli fetch https://arxiv.org/abs/2503.15223 --tier 1

# T8.3: GitHub repo URL（触发重写）
.venv\Scripts\python.exe -m scripts.cli fetch https://github.com/anthropics/anthropic-cookbook --tier 2

# T8.4: pipe mode
echo '{"content": "Test content from exa", "tool_used": "exa_web_fetch_exa"}' | .venv\Scripts\python.exe -m scripts.cli fetch https://example.com --from-stdin --tier 3

# T8.5: --no-playwright 标志
.venv\Scripts\python.exe -m scripts.cli fetch https://example.com --tier 3 --no-playwright
```

**预期检查点：**
- [ ] T8.1: `content_insufficient: true`（example.com < 2000 chars），`fetch_failed: false`
- [ ] T8.2: `actual_url` 包含 `ar5iv.labs.arxiv.org`，`tool_used` 非 exa
- [ ] T8.3: `actual_url` 包含 `README.md`
- [ ] T8.4: `tool_used` = `exa_web_fetch_exa`，`fetch_failed: false`
- [ ] T8.5: `tool_used` 不含 `playwright`
- [ ] 所有成功 fetch：`source_file` 非空，对应 `.workdir/sources/` 文件存在

---

## 覆盖矩阵

| 测试 | goal_type | 量化 | 中文 | arXiv | GitHub | Tier4 | pipe | 重点 gate |
|------|-----------|------|------|-------|--------|-------|------|-----------|
| T1 | tech_selection | ✓ | | | | | | section_coverage, precision |
| T2 | exploratory | | ✓ | | | | | key_insights, topic_coverage |
| T3 | fact_check | ✓ | | | | | | minimal path, source_verification |
| T4 | academic_research | ✓ | | ✓ | | | | URL rewrite, tier_balance |
| T5 | market_analysis | ✓ | ✓ | | | ✓ | | vendor_affiliation, precision |
| T6 | competitive_comparison | ✓ | | | | | | comparison table, metric_type |
| T7 | background_check | | ✓ | | ✓ | | | zh search, GitHub rewrite |
| T8 | (CLI fetch) | | | ✓ | ✓ | | ✓ | fetch pipeline, content_insufficient |
