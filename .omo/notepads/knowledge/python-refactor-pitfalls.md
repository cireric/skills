# Python 重构踩坑

从 info-collector 代码质量优化实践中提炼的 Python 语言级踩坑记录。

## `Path(__file__)` 层级从函数自身算起

提取共享路径函数时，`Path(__file__)` 的层级取决于**函数所在文件**的深度，不是调用者的深度。

```
# utils.py 位于 scripts/lib/utils.py
# Path(__file__).parent        → scripts/lib/
# Path(__file__).parent.parent → scripts/          ← 差一级！
# Path(__file__).parent.parent.parent → info-collector/  ← 正确
```

**实例**：原代码 `cli.py`（位于 `scripts/`）用 `.parent.parent` 是对的，但提取到 `lib/utils.py`（深了一层）后必须多加一级。必须从函数自己的位置算起。

## 提取共享函数时检查同名局部变量

Python 中局部变量会静默遮蔽同名的模块级导入。提取函数到共享模块后，消费者中若有同名局部变量，必须重命名，否则运行时行为改变且无报错。

```python
# 提取前：局部变量 config_path 遮蔽了即将导入的函数名
config_path = Path(__file__).parent.parent / ARTIFACT_CONFIG  # 局部变量

# 提取后：必须重命名局部变量
from .lib.utils import config_path  # 导入的函数
cfg_path = config_path()            # 重命名局部变量
```

## `except Exception` 的真正问题往往不是太宽，而是太静默

修复宽泛捕获时，更隐蔽的问题是 `pass` 静默吞异常。`except OSError: print(warning)` 比 `except Exception: pass` 好，即使捕获范围一样宽。
