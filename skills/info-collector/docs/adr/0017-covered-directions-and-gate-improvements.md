# ADR 0017: covered_directions 字段与五项 gate 改进

- **Status**: Superseded by ADR-0042
- **Date**: 2026-06-18
- **Context**: info-collector skill

## Context

2026-06-18 的 "Agentic Coding 趋势" deep 调研实战暴露了六个问题（详见 `reports/info-collector-retrospective-2026-06-18.md`），经 grill-with-docs 会议确认后合并为五项改进。

## Decisions

### 1. covered_directions 字段（合并原问题 1+2）

在 collected.json 的每个 entry 中增加可选字段 `covered_directions: list[str]`，由 agent 在收集时声明该来源覆盖了哪些 search_directions。

约束：
- 值必须是 `scope.json` 的 `search_directions` 的子集
- 每个 entry 最多声明 3 个方向（防止偷懒全选）
- `_check_search_gate` 中，当 entry 有 `covered_directions` 时，优先使用该字段而非 token 匹配来确定 direction 覆盖
- 同时服务于 `topic_coverage` 检查和 `per_direction_min_sources` 计数

**为什么不用 embedding 相似度**：违反 stdlib-only 原则（ADR 0001 已否决 jieba，embedding 更重），且对中英混合方向匹配质量不确定。半结构化声明让 agent 用领域知识纠正 token 匹配的误判，零依赖。

### 2. subagent 输出 schema 双层保障（原问题 3）

- **Prompt 层**：SKILL.md Step 2 的 subagent prompt 模板中加入 JSON schema 片段，减少违规概率
- **代码层**：`proceed.py` 在 `_check_analysis_schema` 之前增加 `_sanitize_sections` 函数，做字段映射和裁剪：
  - `section_id` → `id`
  - `sources` → `source_urls`
  - 删除 `word_count`、`language` 等非 schema 字段
  - `claims` 缺失 → 默认空列表 `[]`

### 3. precision_inflation 检查降级（原问题 4）

当 `fetched_content` 为空或长度 < 200 字符时，跳过 `_number_found_in_source` 检查（WARN 级），只保留 BLOCKER 级的 `precision='exact' + evidence_type` 违规检查。

**原因**：Exa 搜索 API 返回 snippet 是截断片段，`exa_web_fetch_exa` 不保证所有 URL 都能抓到全文（付费墙、JS 渲染等）。强制全文抓取成本高且不稳定，不如在数据不充分时降级检查。

### 4. reset --phase review 文档补充（原问题 5）

SKILL.md Phase 3b 中补充：review 后修复 analysis.json 时，若 phase 已推进到 post_review，先运行 `python scripts/cli.py reset --phase review` 回退 phase，再 re-run `proceed --from analysis --to review`。

不改代码 — `reset` 命令（ADR 0016）已能解决问题。

### 5. _detect_quality() 解析 review verdict（原问题 6）

`_detect_quality()` 改为解析 `review_report.md` 的 `## Overall Verdict` 部分（Markdown 加粗格式）：
- `**pass**` → `"passed"`
- `**pass_with_issues**` → `"degraded"`
- `**fail**` → 报错（不应生成报告）
- 解析失败 → fallback `"degraded"`（宁降不升）

## Alternatives Considered

1. **embedding 相似度替代 token 匹配**：准确但引入外部依赖，违反 stdlib-only 原则
2. **降低 per_direction_min_sources 阈值**：治标不治本，阈值本身没问题，是输入数据（匹配结果）有误
3. **强制全文抓取 fetched_content**：理想但 Exa fetch API 不稳定，且 57 个来源全抓 token 消耗巨大
4. **phase_lock.json 显式 phase 管理**：过重，reset 命令已足够
5. **validate_section 函数让 subagent 调用**：subagent 是 AI 不是 Python 进程，无法调用

## Consequences

- token 匹配的语义盲区通过 agent 声明补充，不再需要捏造 Tier 4 来源通过门禁
- subagent schema 违规在组装时自动修正，gate 不再因 schema 问题 BLOCK
- precision_inflation 误报减少（数据不充分时跳过检查）
- review 后修复 analysis.json 的路径文档化
- 报告 quality 标记更准确（自动检测 verdict 而非只检查文件存在）
