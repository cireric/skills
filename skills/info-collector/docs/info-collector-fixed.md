# Info-Collector 代码审查报告

审查范围：`skills/info-collector/scripts/` 全部源码（含 `lib/` 子模块）。
审查日期：2026-06-26（原 2026-06-23，更新修复状态）

---

## 1. 死代码

严格意义上的死代码为零。初判中以下两项经验证排除：

| 初判 | 验证结论 |
|------|----------|
| `artifact_checks.py:65-68` 有 `CheckResult` 残留 | **误判** — L62 起是 `check_artifact_exists` 函数体，非残留代码 |
| `proceed.py:7` `import sys` 未使用 | **误判** — L107/L180/L403 均使用了 `sys.stderr` |

---

## 2. 重复定义的常量 / 逻辑

### R1: `covered_directions` 最大长度硬编码 ✅ DONE

| 位置 | 代码 |
|------|------|
| `schemas.py:222` | `if len(cd) > 3:` |
| `search_gate.py` | `if len(cd) > 3:`（原 `proceed.py:205`，已拆至 search_gate.py） |

同一业务规则在两处硬编码。已提取为 `constants.py:97` 中的 `_MAX_COVERED_DIRECTIONS = 3`，替换了 `schemas.py` 和 `search_gate.py` 中的硬编码。

### R2: fallback route 字典硬编码 ✅ DONE

| 位置 | 代码 |
|------|------|
| `source_router.py:30` | `routes.get("other", {"entry_tier": 3, "path": [3, 2, 1]})` |
| `source_router.py:42` | `routes.get("other", {"entry_tier": 3, "path": [3, 2, 1]})` |

已提取为模块级常量 `_DEFAULT_ROUTE = {"entry_tier": 3, "path": [3, 2, 1]}`，替换了两处硬编码 fallback。

### R3: `defined_nums | visible_nums` 合并逻辑 ✅ DONE

| 位置 | 代码 |
|------|------|
| `report_checks.py:46-48` | `defined_nums = ...; visible_nums = ...; all_defined = defined_nums \| visible_nums` |
| `report_checks.py:76-78` | 完全相同的代码 |

### R4: body 内引用编号提取逻辑 ✅ DONE

| 位置 | 代码 |
|------|------|
| `report_checks.py:49-56` | `_INLINE_CITATION.finditer(body)` + `re.finditer(r'\[(\d{1,2})\]\[\]', body)` |
| `report_checks.py:80-86` | 完全相同的代码 |

R3+R4 已提取为两个辅助函数：`_extract_defined_nums(ref_section)` 和 `_extract_cited_nums(body)`，替换了 F1/F2 中的重复逻辑。

### R5: `_source_text()` 内联重复 ✅ DONE

| 位置 | 代码 |
|------|------|
| `artifact_checks.py:44-45` | `def _source_text(item): return (item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()` |
| ~~`artifact_checks.py:770-772`~~ → `claim_validator.py` | `(item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()` |

`check_claim_source_relevance` 原在 `artifact_checks.py:770-772` 内联了与 `_source_text()` 完全相同的拼接逻辑。该函数已随 ADR 0024 拆分至 `claim_validator.py`，内联拼接已替换为 `_source_text(item)` 调用。

### R6: collected URL 集合构建 ✅ DONE

| 位置 | 代码 |
|------|------|
| `proceed.py:417-419` | `{normalize_url(e.get("url", "")) for e in collected if isinstance(e, dict)}` |
| `artifact_checks.py:88` | `{normalize_url(item["url"]) for item in collected if "url" in item}` |

两者均从 collected.json 构建 `normalize_url` 集合，逻辑重复。已提取 `build_collected_url_set(collected)` 到 `utils.py`，统一两处集合构建。

### Extra: 重复 `_VERSION_PATTERN` 定义 ✅ DONE

`artifact_checks.py` 中原有重复的 `_VERSION_PATTERN` 定义，已删除。

---

## 3. 代码异味

### S1: God Module

`artifact_checks.py`（原 818 行，现 385 行）承载 17 个 check 函数 + 辅助函数。已拆出 `report_checks.py`、`claim_validator.py`（ADR 0024）、`search_gate.py`（ADR 0022），artifact 侧已大幅瘦身。

### S2: 延迟导入泛滥

大量函数体内 `from .xxx import yyy`，暗示循环依赖：

- `proceed.py`: L150, L272, L291, L310, L416, L424
- `cli.py`: L29, L44, L55, L68-69, L97, L125-126, L174-176

### S3: 局部重复导入 ✅ DONE

`cli.py:191` 在 `_build_report_filename` 内 `import re as _re`，顶层已有 `import re`。已删除 `import re as _re`，直接使用顶层 `re`。

### S4: `_find_report_path` 重复读 config

`proceed.py:377-390` 重新打开并解析 config.json，而调用链上层 `proceeds()` 已有 config 参数，但未透传至 `_gate_final` → `_find_report_path`。

### S5: 常量下划线前缀与公开使用矛盾

`constants.py` 中所有 `_VALID_*`、`_PREFIX_*` 用下划线表示模块私有，但被 `schemas.py`、`artifact_checks.py`、`proceed.py`、`reporter.py` 大量跨模块导入。下划线前缀语义与实际使用不一致。

### S6: `_PHASE_ARTIFACTS` 不完整 ✅ DONE

`constants.py:149-154` 原仅含 scope/search/analysis/review 四个 key，pipeline 实际还有 final 和 cleanup 阶段。已补充 `final` 和 `cleanup` key，`cmd_reset` 现可重置到 final 阶段。

### S7: `_read_artifact` level 参数语义不清 ✅ DONE

`artifact_checks.py:391-413`：`check_metric_type_homogeneity` 调用 `_read_artifact(..., level="WARN")`，读取失败返回 `WARN+passed=True`，但检查失败返回 `BLOCKER+passed=False`。

`level` 参数控制"读不到时的宽容度"，返回值 level 是"检查结果严重度"——两者语义不同但共用 `level` 命名。已重命名参数为 `read_error_level`，消除语义混淆。

### S8: `_gate_analysis` 只检查 `url_traceability` ✅ DONE（见 L2）

`proceed.py:428-432`（原行号）：调用 `run_all`（17 个 check）但仅用 `next()` 提取 `url_traceability` 一个结果。已修复，见 L2。

### S9: `_VALID_TRANSITIONS_SET` 可读性差

`constants.py:140-147`：用 `set[tuple[str,str]]` 定义合法转换，查找需遍历。若改用 dict 可同时存储转换与对应 gate 函数，消除 `proceeds()` 中的 `gate_fn` 字典。

### S10: `_detect_quality` 分支冗余

`cli.py:139-170`：精确 regex 与 fallback regex 各有三路分支（`pass`/`pass_with_issues`/`fail`），逻辑重复。可用 dict mapping 简化。

---

## 4. 逻辑谬误

### L1: CJK 降级过度降级 ✅ DONE

**文件**: `search_gate.py:196`（原 `proceed.py:248-258`，已拆至 search_gate.py）

**原状**:

```python
cjk_heavy = _has_cjk_tokens(list(needed))  # 检查的是 needed（全部方向），不是 missing
if cjk_heavy:
    warnings.append(...)  # 全部 missing 方向降级为 WARN
else:
    blockers.append(...)  # 全部 missing 方向升级为 BLOCKER
```

只要 `needed` 中**任一**方向含 CJK 字符，就**全部**未覆盖方向降级为 WARN。

**影响**: 若 5 个方向中仅 1 个是 CJK 且未覆盖，其余 4 个英文方向未覆盖也被降级，本应是 BLOCKER 的问题被弱化。

**已修复**: 按方向单独判断 CJK，只对含 CJK 字符的未覆盖方向降级（`search_gate.py:196`）：

```python
missing = needed - covered
if missing:
    for d in missing:
        if _has_cjk_tokens([d]):
            warnings.append(
                f"topic_coverage WARN (CJK direction): search direction not covered: {d}"
            )
        else:
            blockers.append(
                f"topic_coverage BLOCKER: search direction not covered: {d}"
            )
```

### L2: `_gate_analysis` 遗漏 BLOCKER ✅ DONE

**文件**: `proceed.py:231-265`（原 `proceed.py:428-432`）

**原状**:

```python
url_result = run_gateway(workdir, _get_goal_type(workdir))
url_check = next((r for r in url_result if r.name == "url_traceability"), None)
if url_check and not url_check.passed:
    errors.append(f"[BLOCKER] url_traceability: {url_check.message}")
```

调用 `run_all` 返回 17 个 check 结果，但只提取 `url_traceability`。其他 BLOCKER（如 `precision_inflation`、`source_metadata`、`claim_verified`）被丢弃。

**影响**: analysis→review 门无法捕获所有应阻断的问题，需等到 review→final 才暴露，阶段归属不清。

**已修复**: 检查全部 14 个 analysis-phase BLOCKER（`proceed.py:231-265`）：

```python
gateway_results = run_gateway(workdir, _get_goal_type(workdir))
analysis_check_names = {
    "url_traceability", "precision_inflation", "source_metadata",
    "claim_verified", "claim_source_relevance", "claim_metadata",
    "claim_dedup", "metric_type_homogeneity", "fetched_content_depth",
    "search_plan_compliance", "topic_coverage", "tier_coverage",
    "collected_schema", "analysis_schema",
}
blockers = [
    r for r in gateway_results
    if r.level == "BLOCKER" and not r.passed and r.name in analysis_check_names
]
errors.extend(f"[BLOCKER] {b.name}: {b.message}" for b in blockers)
```

### L3: `_gate_review` 全量重跑 gateway ✅ DONE

**文件**: `proceed.py:268-275`（原 `proceed.py:436-439`）

**原状**:

```python
def _gate_review(workdir: Path) -> list[str]:
    gateway_results = run_gateway(workdir, _get_goal_type(workdir))
    blockers = [r for r in gateway_results if r.level == "BLOCKER" and not r.passed]
    return [f"[BLOCKER] {b.name}: {b.message}" for b in blockers]
```

review 阶段再次全量运行 17 个 check，但 review 阶段应只关心 review-specific check（如 `claim_verified`）。全量运行浪费性能，且可能被 analysis 阶段就该阻断的问题阻断。

**影响**: review 阶段可能被 analysis 阶段就该阻断的问题阻断，错误消息阶段归属不清。

**已修复**: 缩小检查范围至 review-specific check（`proceed.py:268-275`）：

```python
def _gate_review(workdir: Path) -> list[str]:
    gateway_results = run_gateway(workdir, _get_goal_type(workdir))
    review_check_names = {"claim_verified", "claim_source_relevance"}
    blockers = [
        r for r in gateway_results
        if r.level == "BLOCKER" and not r.passed and r.name in review_check_names
    ]
    return [f"[BLOCKER] {b.name}: {b.message}" for b in blockers]
```

### L4: `_generate_search_plan` 语言判断粒度不足 ❌ NOT DONE

**文件**: `proceed.py:340-354`

**现状**:

```python
is_chinese_tier = any(
    s.get("domain", "").endswith((".cn", ".com.cn")) or "cnki" in s.get("domain", "")
    for s in tier_sources
)
task = {
    ...
    "query_language": "zh" if is_chinese_tier else "en",
}
```

用 `any(...)` 判断**整个 tier** 是否中文，但同一 tier 可能同时包含中英文源。例如 Tier 2 既有 `github.com` 又有 `cnki.net`（如果被添加），则整个 tier 的所有 task 被标记为 `zh`。

**影响**: 中英文混合 tier 的搜索任务可能被标记为错误的语言。

**建议**: 将 `query_language` 判断从 tier 级别下推到 source 级别，每个 task 拆分为中/英文子任务，或使用 source 级别的语言标记。

### L5: F1/F2/9 检查级别过低 ✅ DONE

**文件**: `report_checks.py`

**原状**: F1（dangling refs，悬空引用）、F2（orphaned defs，孤立定义）、9（front matter 缺失）均为 WARN 级别，但这些错误会导致报告不可用（引用断裂、缺少必要章节），应阻断流程。

**已修复**: F1、F2、9 已从 WARN 升级为 BLOCKER，确保 review→final 门可捕获这些问题。

---

## 5. 改进建议

### P0 — 必须修复（逻辑谬误）

| 编号 | 对应问题 | 修复要点 | 状态 |
|------|----------|----------|------|
| P0-1 | L1 | `_check_topic_coverage` 中按方向单独判断 CJK，只对含 CJK 的 missing 方向降级为 WARN | ✅ DONE |
| P0-2 | L2 | `_gate_analysis` 中检查 `run_all` 返回的全部 BLOCKER，而非仅 `url_traceability` | ✅ DONE |

### P1 — 应该修复（重复定义 + 代码异味）

| 编号 | 对应问题 | 修复要点 | 状态 |
|------|----------|----------|------|
| P1-1 | R1 | `constants.py` 添加 `_MAX_COVERED_DIRECTIONS = 3`，替换 `schemas.py` 和 `search_gate.py` 中硬编码 | ✅ DONE |
| P1-2 | R2 | `source_router.py` 提取 `_DEFAULT_ROUTE` 常量，替换两处硬编码 fallback | ✅ DONE |
| P1-3 | R3+R4 | `report_checks.py` 提取 `_extract_defined_nums()` 和 `_extract_cited_nums()` 辅助函数 | ✅ DONE |
| P1-4 | R5 | `claim_validator.py`（原 `artifact_checks.py:770-772`）用 `_source_text(item)` 替换内联拼接 | ✅ DONE |
| P1-5 | R6 | 提取 `build_collected_url_set(collected)` 到 `utils.py`，统一两处集合构建 | ✅ DONE |
| P1-6 | S3 | `cli.py` 删除 `import re as _re`，直接使用顶层 `re` | ✅ DONE |
| P1-7 | S4 | `_find_report_path` 添加 `config` 参数，避免重复读 config.json | ❌ NOT DONE |
| P1-8 | S7 | 重命名 `_read_artifact` 的 `level` 参数为 `read_error_level`，消除与返回值 `level` 的语义混淆 | ✅ DONE |

### P2 — 建议改进（架构 + 可读性）

| 编号 | 对应问题 | 修复要点 | 状态 |
|------|----------|----------|------|
| P2-1 | S1 | 拆分 `artifact_checks.py` 为 `claim_checks.py` / `coverage_checks.py` / `content_checks.py` | ✅ DONE（已拆出 `claim_validator.py` + `search_gate.py`，artifact_checks.py 从 818→385 行） |
| P2-2 | S5 | 去掉 `constants.py` 中被跨模块使用的常量下划线前缀，或提供公开访问函数 | ❌ NOT DONE |
| P2-3 | S2 | 将 gate 逻辑独立为 `gates.py`，`proceed.py` 只负责状态转换和 gate 调度，解除循环依赖 | ❌ NOT DONE |
| P2-4 | S6 | `_PHASE_ARTIFACTS` 补充 `final` 和 `cleanup` key | ✅ DONE |
| P2-5 | S9 | `_VALID_TRANSITIONS_SET` 改用 dict 映射 `(from, to) → gate_fn`，消除 `proceeds()` 中的 `gate_fn` 字典 | ❌ NOT DONE |
| P2-6 | S10 | `_detect_quality` 用 dict mapping 替代多分支 if/elif | ❌ NOT DONE |
| P2-7 | L3 | `_gate_review` 缩小检查范围至 review-specific check | ✅ DONE |
| P2-8 | L4 | `_generate_search_plan` 语言判断从 tier 级下推到 source 级 | ❌ NOT DONE |
| P2-9 | L5 | F1/F2/9 从 WARN 升级为 BLOCKER | ✅ DONE |
