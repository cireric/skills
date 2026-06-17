# ADR 0015: 集中 schema 校验（TypedDict + validate 函数）

- **Status**: Accepted
- **Date**: 2026-06-17
- **Context**: info-collector skill

## Context

info-collector 的 JSON schema 校验散落在三个位置：

1. `proceed._check_scope_schema()` — scope.json 字段存在性 + 枚举值
2. `gateway.check_analysis_schema()` — analysis.json 结构（topic/goal_type/sections/claims）
3. `gateway.check_claim_metadata()` — claim 字段完整性（evidence_type/confidence/precision）

每次 schema 变更（如 ADR 0004 加 metric_type、ADR 0005 加 verified、ADR 0008 加 source_metadata）都需要逐处修改校验代码，容易遗漏。且当前校验只检查"值是否在枚举中"，不检查"字段类型是否正确"——AI 写出 `"depth": 3` 时错误消息不够精确。

## Decision

### 1. 新增 `lib/schemas.py`，集中 per-artifact 校验函数

| 函数 | 校验对象 | 调用方 |
|------|----------|--------|
| `validate_scope(data) -> list[ValidationError]` | scope.json | Gate 1（替代 `_check_scope_schema`） |
| `validate_analysis(data) -> list[ValidationError]` | analysis.json | Gate 3 + Gate 4（替代 `check_analysis_schema`） |
| `validate_collected(data) -> list[ValidationError]` | collected.json | Gate 2 开头（新增） |

不校验 config.json（预配置文件，AGENTS.md 约束不可改）和 search_plan.json（代码生成，不需要校验）。

### 2. TypedDict 定义 artifact 结构

为每个 artifact 定义 `TypedDict`，供类型检查器使用。校验函数接受 `dict` 输入（因为 `read_json()` 返回 `dict`），TypedDict 仅作类型注解。

### 3. `ValidationError` 纯 dataclass

```python
@dataclass
class ValidationError:
    field: str
    message: str
```

定义在 `lib/exceptions.py`，和 `InfoCollectorError`/`ArtifactError` 同层。**不继承 Exception**——info-collector 的校验模式是"批量收集错误再决定"，不是"遇错即停"。调用方拿到 `list[ValidationError]` 后自行决定如何处理（转为 `CheckResult`、blocker/warning、或 `sys.exit`）。

### 4. 校验深度原则

- **schema 只管结构，gate 管质量**：`validate_analysis()` 校验 section/claim 结构是否存在，但**不**校验 claim metadata 完整性（evidence_type/confidence/precision 缺失是质量问题，不是结构问题）
- **类型校验**：确保 str 字段是 str、list 字段是 list、枚举值在范围内。比当前"只查枚举值"更精确
- **不加语义校验**：topic 为空、scope_description 过短等是 AI 写作问题，不是 schema 问题

### 5. Gate 2 增加 collected.json 结构校验

当前 Gate 2 不校验 collected.json 结构。如果 entry 缺 url 或 source_tier 类型错误，后续 topic_coverage/tier_coverage/url_traceability 会产生误导性结果。`validate_collected()` 在 Gate 2 开头调用，结构错误算 BLOCKER。

## Alternatives Considered

1. **Pydantic**：强校验、自动序列化。但引入 pip 依赖，违反 stdlib-only 约束（jieba 的先例证明例外会累积技术债——ADR 0001 引入，ADR 0012 又移除）。且 info-collector 的 schema 变更频率高（14 个 ADR），Pydantic 的严格性反而是负担。
2. **stdlib dataclass + `__post_init__` 校验**：不引入依赖，但校验逻辑仍散落在各 dataclass 中，且需要将 `read_json()` 返回的 dict 转为 dataclass 实例，增加转换层。
3. **per-gate 组织**：`validate_scope_search_gate()`、`validate_analysis_review_gate()`。但同一 artifact 的校验在多个 gate 中需要（scope 在 Gate 1 和 Gate 3，analysis 在 Gate 3 和 Gate 4），per-gate 会导致校验逻辑分散。
4. **ValidationError 继承 Exception**：可抛出也可返回。但调用方需同时处理返回值和异常两条路径，心智负担加倍。info-collector 的模式是批量收集错误再决定，不是遇错即停。

## Consequences

- schema 校验逻辑集中在一处，变更时只改 `lib/schemas.py`
- 错误消息更精确：从"Invalid depth: 3"变为"field 'depth': expected str, got int"
- collected.json 结构错误在 Gate 2 即被拦截，不再误导后续检查
- TypedDict 为类型检查器提供信息，但不改变运行时数据流（仍是 `read_json() -> dict`）
- gate 函数需适配：从 `field not in dict` 改为调用 `validate_*()` 并转换 `ValidationError` → `CheckResult`/blocker
