# Source Verification Protocol (Prompt Template)

> **来源**：从 info-collector 的 `apply_source_verification()` 确定性代码（ADR 0028）提炼为 prompt 模板。
> **状态**：归档模板。任何 research skill 的 agent 读到即可使用。牺牲 100% 确定性，换零维护成本。
> **对应代码**：原 `skills/info-collector/scripts/claim_validator.py` 的 `_compute_source_verification()` + `_number_found_in_source()` + `_is_indirect_source()`。

## 使用方式

将以下内容作为 system prompt 前置，或粘贴到任何 research / 报告生成 agent 的指令中。agent 产出报告时按本协议自标来源验证状态。

---

## Protocol

对报告中**每个含数字 / 基准 / 量化声明**的引用，执行以下验证并标记：

### 三级状态

| 标记 | 状态 | 含义 |
|---|---|---|
| （无标记）| `source_confirmed` | 声明中的数字在引用来源原文中找到 |
| `†` | `source_absent` | 声明中的数字在引用来源原文中**未找到** |
| `‡` | `source_indirect` | 来源本身是间接的（见下规则），数字是否找到不影响此判定 |

**优先级**：`source_indirect` > `source_absent` > `source_confirmed`。一个 claim 只能有一个状态。

### 验证流程

对每个含数字的 claim：

1. **打开引用来源**（Read tool / webfetch）——不要只看 snippet，要看原文
2. **在原文中搜索 claim 中的具体数字**（精确匹配，含单位、百分比、范围）
3. **判定状态**：
   - 数字找到 + 来源直接 → 无标记（`source_confirmed`）
   - 数字未找到 + 来源直接 → `†`（`source_absent`）
   - 来源是间接的（见下） → `‡`（`source_indirect`），无论数字是否找到

### Indirect 判定规则

满足以下**任一**条件，来源标记为 `‡`（indirect）：

1. **Tier 3+ 来源 + 官方数据声明**：来源是博客 / 社区帖 / 行业媒体（非官方、非学术），但 claim 声明 `evidence_type` 为 `official_data` 或 `independent_benchmark`。低权威来源声称官方数据，本身就可疑。
2. **Vendor benchmark + exact/range precision**：来源是厂商自己的 benchmark（`source_type: vendor_benchmark`），且 claim 精度为 `exact` 或 `range`。厂商自测自报的数据天然有偏向。
   - **例外**：若来源 venue 本身是权威的（如 arXiv 论文，即使被误标为 `vendor_benchmark`），不判定为 indirect。权威 venue 的同行评审抵消 vendor 标签的可疑性。
3. **间接引用模式**：claim 文本中出现"X 据称"、"Y 公司报告称"等间接引用模式，且被引用实体不是来源 host 本身。

### 数字匹配规则

- **精确数字**：`80.9%`、`4,683 lines`、`23%` —— 原文中必须出现完全相同的数字（单位可不同，但数值要匹配）
- **范围数字**：`45-48%` —— 原文中必须出现该范围，或两个端点都出现
- **货币**：`$2.5B` = `$2,500,000,000` = `2.5 billion` —— 数值等价即匹配
- **无数字的 claim**：定性声明（如"框架支持并行处理"）默认 `source_confirmed`，无需标记

### 报告末尾的验证摘要

报告必须包含验证摘要表：

```markdown
> **Verification note**: This report is a research starting point, not a citable authority.
> † = data not found in cited source; ‡ = data from indirect source.

| Status | Count | Ratio |
|--------|-------|-------|
| Confirmed | X | X% |
| Indirect ‡ | Y | Y% |
| Absent † | Z | Z% |
```

### Front matter

报告 YAML front matter 必须包含：

```yaml
verification_required: true
```

提示后续使用者：报告中含需要验证的 claim，†/‡ 标记处需人工核查。

---

## 示例

### 示例 1：confirmed（无标记）

Claim: "Claude Opus 4.5 在 SWE-bench Verified 上得分 80.9%[1]"
来源原文: "...Claude Opus 4.5 achieved 80.9% on SWE-bench Verified..."
→ 数字找到，来源是官方/学术 → `[1]`（无标记）

### 示例 2：absent (†)

Claim: "框架吞吐量达 23,000 req/s[2]"
来源原文: "...the framework processes requests efficiently..."（无具体数字）
→ 数字未找到 → `[2†]`

### 示例 3：indirect (‡)

Claim: "GPT-5 在 MMLU 上得分 92%[3]"
来源是 Reddit 帖子（Tier 4）+ claim 声明 official_data
→ Tier 4 + official_data → `[3‡]`（即使原文中出现了 92%）

---

## 局限性（已知）

1. **LLM 自标会失真**：agent 可能不仔细检查、谎报。本协议依赖 agent 的诚实执行，无强制机制。
2. **无结构化校验**：原 info-collector 用确定性代码（数字正则匹配 + URL 归一化）达到 100% 准确；本模板是 prompt 指令，准确率估计 70-80%。
3. **符合 starting point 定位**：用户本来就要 verify，†/‡ 只是"提示哪些更可疑"。对 starting point 来说，70-80% 准确率足够。

若未来需要 100% 确定性验证，需重建结构化 claims pipeline（见 ADR 0065 的 lessons）。

---

## 历史参考

原确定性代码逻辑（Python，~220 行）保留在 `skills/info-collector/scripts/claim_validator.py` 和 `skills/info-collector/scripts/reporter.py`，作为历史归档。关键函数：

- `_normalize_numbers(text)` — 数字提取（含货币、范围、百分比）
- `_number_found_in_source(claim_text, source_text)` — 数字匹配
- `_is_indirect_source(claim, collected_by_url)` — indirect 判定（tier + source_type 规则）
- `_compute_source_verification(claim)` — 主逻辑
- `apply_source_verification(workdir)` — 写回 analysis.json
- `_resolve_ref_markers(content, ref_map, sv_map)` — †/‡ 渲染
- `_render_verification_summary(analysis)` — 验证摘要表
