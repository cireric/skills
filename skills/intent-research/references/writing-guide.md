# Research Writing Guide

> **定位**：品味指南，不强制遵守。取舍由 writer 决定。

## Content Quality

**内容质量是第一优先级。** 如果内容稀薄，最终报告就会稀薄。写每个章节时，当作在写最终报告的该章节。

### 内容必须包含

- **结构化表格**用于任何多维比较（框架特性、基准分数、协议规范、定价等）。工程师扫表格提取信息——比较场景优先用表格而非段落
- **带上下文的具体数字**——不是"分数约 70%"，而是"Claude Opus 4.5: Verified 80.9%, Pro ~45-48%, ~33pt 差距"
- **架构细节**——不是"用 AsyncGenerator"，而是"AsyncGenerator 核心循环，~4,683 行，43+ 内置工具，5 层权限模型"
- **具体例子**——不是"支持并行 agent"，而是"git worktree 隔离每个 agent 的工作目录、分支和暂存区；`/apply-worktree` rebase/merge 回主分支"

### 内容长度

每节 500-2000 字实质性分析。若不足 300 字，几乎肯定太薄——检查是否缺表格或细节。

### 子标题

复杂章节内用 `###` 组织。例如"框架对比"节应有每个框架的 `###` 子标题。

### 不要顶级标题

内容不要以 `# ` 或 `## ` 开头。所有标题必须是 `### ` 或更低。节标题本身是 `## ` 级——内容嵌套其下。

### 具体性自检

定稿前验证：
- 每个数字都有上下文（不是"70% 准确率"，而是"MNIST 70%，5-shot 下 CIFAR-10 65%"）
- 每个实体都有具体名字（不是"一个框架"，而是"LangChain v0.3"）
- 比较用表格，不是段落
- 每个 claim 在内容中紧邻其 `{{ref:URL}}` 来源引用

## Source Traceability

- **每个量化声明（基准数字、百分比等）必须带 `{{ref:URL}}` 来源标识**——URL 必须匹配 collected.json 中的条目
- **基准数据必须包含 `source_metadata`**：至少 test_conditions（硬件、OS、运行时版本）、test_date、source_type
- **报告中每个来源名都要有对应的完整可点击 URL**——reference numbering 由 reporter.py 自动分配，禁止硬编码引用编号

### source_tier-aware 引用语言

不同 source_tier 需要不同的正文措辞，准确反映证据权重：

| source_tier | 引用语言规则 | 示例 |
|---|---|---|
| Tier 1（Academic / Standards） | 权威引用 | "根据 OpenAI 官方文档..." |
| Tier 2（Documentation / Open Source） | 带来源归属 | "2025 年 Gartner 报告估计..." |
| Tier 3（Industry / Expert Blogs） | 用限定词 | "一篇博客指出"、"社区分析表明" |
| Tier 4（Community / UGC） | 用强限定词 | "一个未验证来源声称"、"一篇论坛帖提到" |

**绝不要**把 Tier 3/4 的发现用与 Tier 1/2 相同的权威性呈现。正文引用语言要让读者一眼判断证据权重。

## Precision Rules for Claims

- `evidence_type: third_party_estimate` 或 `qualitative_trend` → **不应**用 `precision: exact`
- `precision: exact` → **必须**有 `evidence_type` 为 `official_data` 或 `independent_benchmark`
- 不同 test_conditions 下的基准数字 → 用 `precision: range`，在 `source_metadata.test_conditions` 注明

## Anti-patterns (DO NOT)

- ❌ **单 agent 写所有章节** → token 限制导致内容压缩变薄
- ❌ **先写 claims 再写内容** → 限制思考，产出清单不是叙事
- ❌ **该用表格处用段落** → 工程师扫表格，不扫长文
- ❌ **模糊限定词无数字** → "显著更高"无用；"23% vs 80.9%, ~33pt 差距"有用
- ❌ **省略架构细节因为"读者可自查"** → 报告就是查阅点
- ❌ **内容以 `## 标题` 开头** — 顶级标题与报告模板结构冲突
- ❌ **无先行词的代词** — "它支持并行处理" → "它"是谁？每次都明确命名
- ❌ **来源与 claim 分离** — `{{ref:URL}}` 必须紧邻其 claim，不要堆在末尾
- ❌ **pseudo-synthesis（伪综合）** — 用因果/矛盾语言（"核心矛盾是"、"综合来看"、"本质上"）但无因果证据。若 A 和 B 共现但无法用来源建立 A→B，写"A 和 B 共现；是否有因果关系，现有来源未建立"
- ❌ **name-as-analysis（名字当分析）** — 提及实体 + 一句话描述，但不评估其意义或与替代方案对比。每节至少有 ≥2 个分析性条目（带评估、对比或影响判断，不只是存在性陈述）
- ❌ **action-platitude（行动陈词滥调）** — "读者需要理解 X"或"工程师应该意识到 Y"但无具体、来源支持的指引。要么给具体行动项（"优先 X 因为 Y，来源支持 [src]"），要么删掉这段

## Synthesis Guard

所有综合段落必须满足 synthesis guard：**因果方向必须明确（A→B），且因果链每步至少有一个来源支持**。

**合格综合**（通过）：
> 工具趋同 → 协议碎片化 → 互操作性缺口 → 攻击面扩大。每步有据：趋同 [3]，碎片化 [15]，缺口 [16]，攻击面 [9]。

**不合格综合**（不通过）：
> "核心矛盾是能力增长远超治理成熟度。"——这陈述了矛盾，但未提供因果链，也无来源支持的推理说明为何这两趋势矛盾而非仅共现。

**当 synthesis guard 无法满足时**：诚实呈现为共现现象：
> "能力指标（基准分数、采用率）快速上升，而治理指标（成熟度分数、合规率）持平 [8]。这两趋势是否因果相关或独立，现有来源未建立。"

## Panoramic Overview Section

全景/探索性报告的 overview 节有特殊规则：

1. **优先因果链组织**——若跨节因果链接可建立（如工具趋同 → 协议碎片化 → 安全缺口），围绕因果链组织 overview。每个链接必须通过 synthesis guard。
2. **回退到带注解的共现**——若因果链接无法建立，列出每个方向的关键发现，在有证据处标注关系（"A 与 B 相关因为 [src]"）。不要无证据强行连接。
3. **不要逐节总结**——overview 不是带摘录的目录。它应揭示单节内看不见的方向间关系。
