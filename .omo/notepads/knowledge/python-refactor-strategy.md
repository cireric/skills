# Python 重构策略

从 info-collector 代码质量优化实践中提炼的重构策略经验。

## Facade 先行，消费者零改动

拆分上帝对象时，先建新模块，再让原文件变成 re-export facade：

```python
# gateway.py — 变成 facade
from .artifact_checks import CheckResult, check_analysis_schema, ...  # noqa: F401
from .report_checks import check_report_dangling_refs, ...  # noqa: F401
```

**规则**：所有 `from scripts.gateway import ...` 的消费者和测试零改动，测试立即通过。重构风险窗口从"改 N 个文件"压缩到"改 1 个文件 + 验证 re-export"。

**反例**：先改所有 import 站点再删原文件，改动面大，任何一步出错都会炸。

## 常量迁移用 re-export 过渡

把散落各文件的魔法值迁入 `constants.py` 时，原位置可保留 `= constants.XXX` 别名。测试中直接引用旧名的 import 不会断，过渡更平滑。

## 提取 shared helper 前确认语义一致

两个看似重复的实现可能有细节差异（如 CJK 分词的标点范围、是否 lowercase、是否过滤停用词）。

**规则**：不是"删一个保留另一个"，而是找到最小公共超集作为 core，各消费者在上层做差异化后处理。

## 同域逻辑、不同接口 → 一个实现服务两个接口

同一业务逻辑被两个不同返回类型驱动（如 `list[str]` vs `CheckResult`），解法是让一个 canonical 实现服务两个接口，做类型适配层，而非维护两份逻辑。
