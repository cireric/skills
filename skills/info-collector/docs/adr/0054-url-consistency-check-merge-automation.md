# URL consistency check after merge + merge automation

v3 运行中子代理生成的 `{{ref:URL}}` 和 `sources` 中的 URL 与 collected.json 不精确匹配（`gpt-4` vs `gpt-4-6`），经历 4 轮手动修复，占总 Phase 3 时间 40%+。根因有二：(1) 子代理不知道完整 URL，prompt 中虽有 source_file + snippet 注入但无 URL 精确匹配约束；(2) 合并脚本被重复执行 5+ 次，每次修改 section 后手动重跑合并，修复被覆盖（修了 analysis.json 后下次合并又从未修的 section 文件读入旧 URL）。

## Decision

### 1. Allowed URL list 约束声明

子代理 prompt 的 Source Content 部分末尾增加约束声明："所有 `{{ref:URL}}` 和 `sources` 中的 URL 必须精确匹配以下 URL 之一"。URL 列表取自 collected.json 全量 URL（不分子集），因为 URL 已在 prompt 的 Source Content 注入中存在，额外 token 成本几乎为零。

### 2. 合并后 URL 一致性自检

合并脚本执行后自动扫描 analysis.json 中所有 `{{ref:URL}}` 和 `sources` 中的 URL，与 collected.json 的 URL 列表比对。不匹配的 URL 列表输出为 WARN，并提供 "did you mean?" 建议（复用 `artifact_checks._suggest_similar_urls()` 逻辑）。

此检查与 `ref_marker_validity`/`claim_source_ref_coverage` 的关系：本检查是**前置检测**（合并后立即暴露），`ref_marker_validity`/`claim_source_ref_coverage` 是**最终保证**（gate 层防御纵深）。两者保留，不移除 gate 检查。

### 3. 合并自动化：gate 自动触发合并

`proceed --from analysis --to review` 执行前自动从 section 文件合并为 analysis.json，无需手动跑合并脚本。合并只执行一次：section 文件修改后触发一次合并 → gate → 结束。不再重复合并。

此决策合并了原复盘文档的 2b（合并只执行一次）和 4b（gate 自动触发合并），因为"合并只执行一次"的保证需要"合并是自动触发的"来实现——手动合并天然会重复。

## Consequences

URL 不匹配在合并后立即暴露（而非在 gate 阶段），修复路径更短。子代理 prompt 的 allowed URL list 约束减少初始不匹配概率。合并自动化消除手动重复合并的问题。与 ADR 0053 可并行实施。不取代任何旧 ADR。

Status: accepted
