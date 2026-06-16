# ADR 0012: 具体性检查门和 CJK 分词计数

- **Status**: Accepted
- **Date**: 2026-06-15
- **Context**: info-collector skill

## Context

现有 gate 体系对分析内容的**具体性**缺乏约束。报告可以包含大量模糊表述（"性能良好"、"quite impressive"）而通过所有检查。同时，对需要定量分析的目标类型（如 tech_selection、competitive_comparison），methodology 部分缺乏深度保障。

需要回答两个问题：

1. 如何检测和警告内容中的模糊表述？
2. 如何确保 methodology 部分达到足够的深度？

## Decision

新增两个 gate：`check_content_concreteness` 和 `check_methodology_depth`，并引入 CJK 分段式词数统计作为底层基础设施。

### check_content_concreteness（BLOCKER/WARN）

- 仅对定量目标类型（tech_selection, competitive_comparison, feasibility_assessment, market_analysis, academic_research）生效
- 对每个 section 检查三方面：
  - **模糊短语密度**：预定义的模糊短语列表（中英文各一套，如"比较优秀"、"relatively good"）在 content 中的出现频率。密度超过 10% 则 WARN
  - **数字存在性**：section 是否包含有效数字（排除年份、版本号、列表编号）。对 strict 目标类型（tech_selection, competitive_comparison）为 BLOCKER，其余为 WARN
  - **具体名称存在性**：section 是否包含专有名词（大写英文词、反引号代码引用、非停用词非模糊短语的中文 segment）。同上分级

### check_methodology_depth（WARN）

- 仅对定量目标类型生效
- 检查 methodology section 是否满足：
  - 至少 150 词（用 `_count_words` 计算）
  - 包含至少一个 Markdown 表格（检测 `|` 字符）
- 不满足则 WARN，不阻断流水线

### 词数统计：CJK 分段式计数（Spec Deviation #1）

`_count_words` 实现采用 CJK 分段式计数而非逐字计数：

- **CJK 字符段**（U+4E00–U+9FFF）：连续的汉字序列计为**一个词**。例如"性能良好"计为 1 词，而非 4 词
- **英文/数字 token**：按空白/边界分割，每个非空 token 计为 1 词
- **CJK 标点和全角字符**：跳过不计

**原因**：若逐字计数，纯中文内容的词数会是英文的数倍，分母膨胀使 10% 模糊短语密度阈值对中文内容实际上不可达。CJK 分段式计数让中英文的密度基准可比。

## Alternatives Considered

1. **逐字计数**：实现简单、对称性好；但中文 4 字短语和英文 2 词短语在密度计算中权重差距大，中文内容几乎不可能触发 10% 阈值
2. **外部分词库（jieba）**：分词质量更高；但引入新依赖，且 info-collector 此前已避免添加 jieba（reference: ADR 0001）
3. **仅英文检查**：中文内容跳过具体性检查；但信息收集技能的重要使用场景是中/英文混合报告，跳过中文无法达到质量目标

## Consequences

- 定量分析报告现在强制包含数字和具体名称（BLOCKER），或收到明确 WARN
- 模糊表述密度被量化检测，10% 阈值在中文和英文之间可比
- methodology section 获得最低深度保障（150 词 + 表格）
- CJK 分段式计数是一种折中方案：比逐字计数合理，但不如 jieba 精确
- Spec Deviation #1 已记录：CJK 分段式计数而非逐字计数
