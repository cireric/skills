# Info-Collector 优化备忘

> 基于 code-level 验证的改进方向备忘。原始提案见 `docs/info-collector-improvement-proposal.md`。
> 验证时间: 2026-06-26 | 代码版本: v2 (26 ADRs)

---

## 已实施

### Batch 1 重构

- R1: `_MAX_COVERED_DIRECTIONS` 常量提取
- R2: `_DEFAULT_ROUTE` 默认路由常量
- R3+R4: `report_checks.py` 中提取 helper 函数
- R5: `claim_validator.py` 中 `_source_text` 去重
- R6: `utils.py` 中 `build_collected_url_set` 提取
- S3: 移除 `import re as _re`
- S6: `_PHASE_ARTIFACTS` 增加 final/cleanup 阶段
- S7: `read_error_level` 重命名
- 移除重复 `_VERSION_PATTERN`

### Batch 2 逻辑修复

- L1: `search_gate.py` 中 per-direction CJK 分词（`_tokenize_direction`）
- L2: `_gate_analysis` 检查全部 14 项 analysis-phase BLOCKER（见 ADR 0025）
- L3: `_gate_review` 仅检查 `claim_verified` + `claim_source_relevance`（见 ADR 0025）
- L4: F1/F2/9 从 WARN 升级为 BLOCKER（见 ADR 0026）

### ADRs

- 0022: `search_gate.py` 提取（从 `artifact_checks.py` 拆分）
- 0024: `claim_validator.py` 提取（从 `artifact_checks.py` 拆分）
- 0025: Gate phase 职责划分（`_gate_analysis` 检 14 项 BLOCKER，`_gate_review` 仅检 2 项）
- 0026: F1/F2/9 升级为 BLOCKER（`_gate_final` WARN 不再误阻塞）

---

## 一、原始提案事实性错误修正

| # | 原提案表述 | 代码验证结果 | 证据位置 |
|---|-----------|-------------|---------|
| 1 | `fact_check` 路由 `entry_tier: 0` 是 bug | **已修复**。当前 `config.json:47` 为 `entry_tier: 1, path: [1, 2, 4]`，正是提案建议的修复方案。测试 `test_source_router.py:169-181` 已覆盖 | `config.json:47` |
| 2 | `source_tier` 和 `fetched_content` 是"文档化但未实现的死字段" | **错误**。`source_tier` 在 5 处被实际读取：`proceed.py:170`(tier_coverage)、`artifact_checks.py:613`(source_tier_balance)、`artifact_checks.py:673`(fetched_content_depth 分层阈值)、`reporter.py:41`(渲染 tier 标签)、`schemas.py:215-216`(schema 校验)。`fetched_content` 在 `artifact_checks.py:48,680` 和 `proceed.py:229` 中被使用 | 见 grep 结果 |
| 3 | `check_precision_inflation` 和 `check_claim_metadata` 零测试覆盖 | **错误**。`test_gateway.py` 中 `TestCheckPrecisionInflation` 有 13 个测试方法，`TestCheckClaimMetadata` 有 4 个测试方法 | `test_gateway.py:717-1104` |
| 4 | `run_all()` 返回 7 checks | **错误**。`artifact_checks.py:803-827` 的 `run_all()` 返回 16 个检查。`GATES.md:31` 记载 15 个（不含 `check_claim_source_relevance` 和 `check_search_plan_compliance`） | `artifact_checks.py:803` |
| 5 | SKILL.md 声称 "5 hard checks" | **未找到**。当前 SKILL.md 和 GATES.md 均无此表述。GATES.md 记载 Gate 4 有 15 checks | `GATES.md:29-31` |

### 代码质量问题（验证中发现，原始提案未提及）

- **`artifact_checks.py:65-68`**：`_read_artifact` 函数 `return` 语句后有 4 行死代码（`CheckResult` 字段定义的残余），虽不影响运行但应清理

---

## 二、原始提案遗漏确认

| # | 遗漏项 | 验证结果 | 证据位置 |
|---|-------|---------|---------|
| 1 | `analysis → review` 门控过弱 | **已修复**。`_gate_analysis`(`proceed.py:231-265`) 现检查全部 14 项 analysis-phase BLOCKER，而非仅 schema + url_traceability 2 项。见 ADR 0025 | `proceed.py:231-265` |
| 2 | `final → cleanup` 无测试 | **确认**。所有测试文件中无任何 `cleanup` 相关测试 | grep 验证 |
| 3 | `search_plan` 可生成空 `site_queries` 任务 | **确认**。`_generate_search_plan` 当 `recommended.get(tier, [])` 为空时，生成空 site_queries 任务，无校验 | `proceed.py` |
| 4 | `_gate_final` 把 WARN 也当阻塞 | **已修复**。F1/F2/9 已从 WARN 升级为 BLOCKER（见 ADR 0026），`_gate_final`(`proceed.py:278-284`) 现仅阻塞 BLOCKER 级别。剩余 7 项 WARN 为建议性检查，不阻塞 `final → cleanup`，此为正确行为 | `proceed.py:278-284` vs `268-275` |

---

## 三、原始提案架构适配性问题

### 3.1 Weighted RRF 与当前架构不兼容

当前搜索流程是 **LLM 驱动的单流串行搜索**：

1. `search_plan.json` 按 `direction × tier` 生成任务
2. AI agent 逐任务执行 Exa/Playwright 搜索
3. 结果追加到 `collected.json`

RRF 的前提条件——多流独立排名（每流有 `native_rank`）——在当前架构中不存在：
- Exa API 不返回排名位置
- 搜索是串行非并行的，无流标识符
- 在单流上做 RRF 等于恒等变换

**结论**：RRF 需先重构搜索层为多流并行架构才有效，当前阶段投入产出比极低。

### 3.2 LLM Rerank 的成本/收益比存疑

- `collected.json` 典型规模 5-20 条，LLM 已在 analysis 阶段做综合排序
- 额外一次 LLM 调用增加延迟和 token 成本，边际排序收益有限
- 本地信号 fallback（tier 权重 + entity match）本质上已被 `check_source_tier_balance` 和 `check_content_concreteness` 门控覆盖
- 若需 rerank，应优先做本地信号版本（无额外 LLM 调用），LLM rerank 可作为可选增强

### 3.3 Untrusted Content 沙箱的注入层问题

提案建议在 `collected.json` 数据层扩展 `trust_level` 字段，Phase 3a 时对 UGC 内容包裹 `<untrusted_content>` 标签。但：

- Phase 3a 由 **subagent** 执行（见 `SKILL.md` Step 2 + `references/subagent-template.md`）
- 沙箱标签必须在 **subagent prompt 模板** 中注入，而非 `collected.json` 数据层
- `trust_level` 映射（source_tier → trust_level）可在 `source_router.py` 中实现，数据层扩展是合理的
- 但 `<untrusted_content>` 包裹逻辑应作用在 prompt 构造层，非数据存储层

---

## 四、优化方向（经代码验证修订）

### P0：立即处理

#### P0-1：Preflight 质量门控

原始提案建议合理，验证后保留。低质量查询（PII、无意义、过宽泛）在 scope → search 转换中短路，避免浪费 API 调用。

**实现要点**：
- 新增 `scripts/lib/preflight.py`
- 在 `proceed.py` 的 `_gate_scope` 中调用
- REJECT（拒绝执行）vs WARN（建议补充）两类行为

#### ~~P0-2：`analysis → review` 门控增强~~ ✅ DONE

`_gate_analysis`(`proceed.py:231-265`) 现已检查全部 14 项 analysis-phase BLOCKER。见 ADR 0025。

### P1：核心改进

#### P1-1：LAW 输出合同形式化

低成本高收益。`reporter.py` 已有隐式 LAW 行为：
- `build_front_matter` → 隐式 LAW 1（Front Matter）
- `sections_to_markdown` 用 `**Sources:**` 粗体标签 → 隐式 LAW 2（Inline Links）
- `_build_reference_map` + `_render_references` → 隐式 LAW 3（Reference 编号）
- `check_url_traceability` → 隐式 LAW 4（No Invention）

**实现要点**：
- 新增 `references/OUTPUT_LAWS.md`，将隐式规则显式化
- 在 `reporter.py` 渲染后增加 `verify_laws()` 自检
- 注意：LAW 2 的表述应匹配 reporter 实际行为（`**Sources:**` 内联，非 `## Sources` 标题块）

#### P1-2：内容信任模型（trust_level 映射 + 沙箱 prompt）

`source_tier` 已在代码中广泛使用（5 处读取），在其上构建 `trust_level` 映射是可行的。

**实现要点**：
- `trust_level` 映射在 `source_router.py` 中实现，`source_tier` → `trust_level` 自动映射
- `<untrusted_content>` 沙箱标签在 **subagent prompt 模板**（`references/subagent-template.md`）中注入，非 `collected.json` 数据层
- `gateway.py` 新增 `check_source_diversity`（>70% claims 仅来自 UGC → WARN）
- 不修改 `config.json`（项目规则禁止）

#### P1-3：测试覆盖补全

| 缺口 | 说明 | 优先级 |
|------|------|-------|
| `final → cleanup` 转换 | 零测试覆盖，清理逻辑可能是死代码 | 高 |
| `_gate_final` 行为验证 | F1/F2/9 已升级为 BLOCKER，剩余 7 项 WARN 正确地不阻塞。需测试明确记录此正确行为 | 中 |
| `search_plan` 空任务 | `_generate_search_plan` 可生成空 `site_queries` 任务，无校验 | 中 |

### P2：后续改进

#### P2-1：写入时 URL 去重

比后处理 dedupe 更高效。在 SKILL.md Step 2.4 的写入指引中增加 `normalize_url` 去重要求，AI agent 写入 `collected.json` 时即跳过重复 URL。

**理由**：`collected.json` 典型规模 5-20 条，后处理 dedupe 收益有限。写入时去重零成本。

#### P2-2：近重复检测（dedupe.py）

P2-1 的补充。对标题做 trigram Jaccard 近重复检测，标记 `near_duplicate_of` 字段。仅当 `collected.json` 规模增长到 30+ 条时才有显著价值。

#### P2-3：实体提取（entity_extract.py）

为 `claim_source_relevance` 检查提供更精确的实体匹配信号。当前 `check_content_concreteness` 已做简单实体检测（`_has_concrete_name`），但基于规则，无法提取产品名/技术名等结构化实体。

#### P2-4：Provenance 来源证明链

扩展 `analysis.json` 的 claim schema，增加 `provenance` 子字段。需先解决 P0-2（analysis 门控增强），否则 provenance 字段无法被门控强制执行。

### P3：远期/待定

#### P3-1：Weighted RRF

需先重构搜索层为多流并行架构，否则 RRF 无实际效果。当前架构下不投入。

#### P3-2：LLM Rerank

成本高收益低。若需实现，应先做纯本地信号版本（tier 权重 + entity match + freshness），LLM rerank 作为可选增强。

---

## 五、`config.json` 修改说明

项目规则禁止修改 `config.json`。所有涉及 routes/sources 配置变更的建议（如 fact_check 路由调整），需确认：
1. 当前值是否已正确（fact_check 已修复）
2. 若需修改，通过 setup wizard 或用户手动操作完成，不由代码直接修改

---

## 六、实施路径建议（修订版）

**迭代 1（P0，1-2 天）**：
- ~~新增 `scripts/lib/preflight.py` + 测试~~ 待实施
- ~~增强 `_gate_analysis` 门控（增加 section_coverage 检查）+ 测试~~ ✅ DONE（L2: 检查 14 项 BLOCKER，见 ADR 0025）

**迭代 2（P1，3-5 天）**：
- 新增 `references/OUTPUT_LAWS.md` + `verify_laws()`
- 新增 `trust_level` 映射 + subagent prompt 沙箱改造
- 新增 `check_source_diversity` 门控
- 补全 `final → cleanup` 转换测试 + `_gate_final` 行为测试（F1/F2/9 已为 BLOCKER，WARN 不阻塞为正确行为）

**迭代 3（P2，2-3 天）**：
- SKILL.md 写入时 URL 去重指引
- 新增 `dedupe.py` + `entity_extract.py`（可选）
- 新增 provenance schema 扩展

**迭代 4（P3，视需求）**：
- 搜索层多流并行重构 → RRF 前置条件
- 本地信号 rerank → LLM rerank 可选增强

每个迭代独立可交付，互不阻塞。

---

_验证时间: 2026-06-26_
