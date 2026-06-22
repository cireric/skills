# Python 重构经验总结

从 info-collector 代码质量优化实践中提炼的通用工程经验。适用于任何 Python 项目的重构工作。

## 拆分策略

### Facade 先行，消费者零改动

拆分上帝对象时，先建新模块，再让原文件变成 re-export facade：

```python
# gateway.py — 变成 facade
from .artifact_checks import CheckResult, check_analysis_schema, ...  # noqa: F401
from .report_checks import check_report_dangling_refs, ...  # noqa: F401
```

好处：所有 `from scripts.gateway import ...` 的消费者和测试零改动，测试立即通过。重构风险窗口从"改 N 个文件"压缩到"改 1 个文件 + 验证 re-export"。

反例：先改所有 import 站点再删原文件，改动面大，任何一步出错都会炸。

### 常量迁移用 re-export 过渡

把散落各文件的魔法值迁入 `constants.py` 时，原位置可保留 `= constants.XXX` 别名。测试中直接引用旧名的 import 不会断，过渡更平滑。

### 同文件串行，跨文件可并行

改动同一文件的两个 issue 必须串行，否则并行写会丢失改动。不同文件的独立改动可以并行。

## 去重模式

### 提取 shared helper 前确认语义一致

两个看似重复的实现可能有细节差异（如 CJK 分词的标点范围、是否 lowercase、是否过滤停用词）。解法不是"删一个保留另一个"，而是找到最小公共超集作为 core，各消费者在上层做差异化后处理。

### 同域逻辑、不同接口 → 一个实现服务两个接口

同一业务逻辑被两个不同返回类型驱动（如 `list[str]` vs `CheckResult`），解法是让一个 canonical 实现服务两个接口，做类型适配层，而非维护两份逻辑。

## 踩坑与修复

### `Path(__file__)` 层级从函数自身算起

提取共享路径函数时，`Path(__file__)` 的层级取决于**函数所在文件**的深度，不是调用者的深度。

```
# utils.py 位于 scripts/lib/utils.py
# Path(__file__).parent        → scripts/lib/
# Path(__file__).parent.parent → scripts/          ← 差一级！
# Path(__file__).parent.parent.parent → info-collector/  ← 正确
```

原代码 `cli.py`（位于 `scripts/`）用 `.parent.parent` 是对的，但提取到 `lib/utils.py`（深了一层）后必须多加一级。必须从函数自己的位置算起。

### 提取共享函数时检查同名局部变量

Python 中局部变量会静默遮蔽同名的模块级导入。提取函数到共享模块后，消费者中若有同名局部变量，必须重命名，否则运行时行为改变且无报错。

```python
# 提取前：局部变量 config_path 遮蔽了即将导入的函数名
config_path = Path(__file__).parent.parent / ARTIFACT_CONFIG  # 局部变量

# 提取后：必须重命名局部变量
from .lib.utils import config_path  # 导入的函数
cfg_path = config_path()            # 重命名局部变量
```

### `except Exception` 的真正问题往往不是太宽，而是太静默

修复宽泛捕获时，更隐蔽的问题是 `pass` 静默吞异常。`except OSError: print(warning)` 比 `except Exception: pass` 好，即使捕获范围一样宽。

## 测试策略

### 每步跑全量测试，不要攒

每完成一个重构步骤就跑全量测试。出问题时必定是最近一步引入，bisect 成本为零。攒多步再跑，排查范围成倍增长。

### 子进程隔离测试验证 facade 无副作用

`test_gateway_import.py` 在子进程中 `import scripts.gateway` 并验证没有加载 forbidden 模块。重构后 gateway 变成 re-export facade，测试仍通过——说明 facade 模式没有引入意外的模块加载副作用。这类隔离测试对重构安全网很有价值。
