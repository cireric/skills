# source_type enum unification and validation gap

DeepSeek 调查复盘发现 subagent 输出 `evidence_type: independent_test`，trust boundary 拒收。合法值是 `independent_benchmark`，而 `source_type` 的合法值中却有 `independent_test`。代码验证发现更深层问题：(1) `source_type`（`source_metadata.source_type`）在 `schemas.py` 的 `_validate_claims()` 中**零校验**——subagent 可以写任何字符串，trust boundary 不拦，schema 不拦，gate 不拦；(2) `_VENDOR_SOURCE_TYPES`（`constants.py:81-83`）定义了 `analyst_forecast, vendor_benchmark, vendor_survey, vendor_blog`，但 CONTEXT.md 声明的 `source_type` 合法值为 `official_report, independent_test, production_case, survey, vendor_benchmark`——两套枚举根本对不上。

## Decision

### 1. 统一 source_type 合法值枚举

在 `constants.py` 中新增 `_VALID_SOURCE_TYPES` frozenset，合并 CONTEXT.md 和 `_VENDOR_SOURCE_TYPES` 的值：

```python
_VALID_SOURCE_TYPES = frozenset({
    "official_report", "independent_test", "production_case",
    "survey", "vendor_benchmark", "analyst_forecast",
    "vendor_survey", "vendor_blog",
})
```

`_VENDOR_SOURCE_TYPES` 保留为子集（用于 `claim_validator.py` 的 indirect 判定逻辑），但必须是 `_VALID_SOURCE_TYPES` 的子集。

### 2. trust boundary schema 校验

在 `schemas.py` 的 `_validate_claims()` 中增加 `source_type` 校验：当 `source_metadata` 存在且 `source_type` 字段存在时，检查其值是否在 `_VALID_SOURCE_TYPES` 中。无效值产生 `ValidationError`，trust boundary 拒收。

### 3. `_sanitize_sections` auto-fix 兜底

在 `_sanitize_sections()` 中，对 `source_metadata.source_type` 做 auto-fix：先尝试 `_SOURCE_TYPE_ALIASES` 映射（如 `independent_benchmark` → `independent_test`，`benchmark` → `independent_test`，`official` → `official_report`），无 alias 时降级为 `"survey"`（最通用的默认值，不暗示权威性）。与 `evidence_type` 的 auto-fix 模式一致——先 alias 再降级。alias 映射处理 subagent 混淆 `evidence_type` 和 `source_type` 术语的常见错误。

### 4. evidence_type alias 补充

在 `_EVIDENCE_TYPE_ALIASES` 中增加 `"independent_test": "independent_benchmark"` 映射，消除最常见的混淆路径。注意：`evidence_type` 的 `independent_benchmark` 和 `source_type` 的 `independent_test` 是不同概念的不同枚举值——前者描述证据类型，后者描述数据来源类型。两个 alias 映射方向相反：`evidence_type: independent_test → independent_benchmark`（纠正为正确的证据类型术语），`source_type: independent_benchmark → independent_test`（纠正为正确的来源类型术语）。

## Consequences

`source_type` 不再是校验盲区。subagent 的小错误被 auto-fix 修掉，严重错误被 trust boundary 拦住。`evidence_type: independent_test` 的混淆通过 alias 自动修正。CONTEXT.md 的 `source_type` 术语定义需同步更新。

Status: accepted
