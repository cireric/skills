# ADR 0014: 自定义异常类与文件操作重试策略

- **Status**: Accepted
- **Date**: 2026-06-16
- **Context**: info-collector skill

## Context

info-collector 的 gate 检查、工件文件读写等操作需要统一的错误处理机制。之前各模块直接抛出内置 `Exception` 或 `OSError`，调用方无法区分错误来源（gate 失败 vs 文件损坏 vs 临时 I/O 抖动）。

同时，`read_json`/`write_json` 在操作工件文件（scope.json, collected.json, analysis.json）时可能遇到临时 I/O 错误（如 NFS 延迟、磁盘繁忙），需要重试机制。但 `json.JSONDecodeError` 与 `OSError` 的性质截然不同——前者代表文件内容已损坏，重试无意义。

## Decision

### 1. 三级异常层次结构

在 `scripts/lib/exceptions.py` 中定义一个基类和两个子类：

| 异常类 | 父类 | 用途 | 附加字段 |
|--------|------|------|----------|
| `InfoCollectorError` | `Exception` | 所有 info-collector 异常的基类 | 无 |
| `GateFailureError` | `InfoCollectorError` | gate 检查未通过（BLOCKER） | `phase: str`, `blockers: list[str]` |
| `ArtifactError` | `InfoCollectorError` | 工件文件缺失、不可读、或 schema 无效 | `path: str`, `reason: str` |

顶层代码按需捕获 `InfoCollectorError` 即可统一处理所有已知异常，无需依赖内置异常的类型推断。

### 2. 文件操作重试（仅 OSError）

`read_json()` 和 `write_json()` 均采用以下重试策略：

```python
def read_json(path, retries=2, delay=0.5):
    for attempt in range(retries + 1):
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ArtifactError(...) from e   # 立即失败，不重试
        except OSError:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise ArtifactError(...) from None

def write_json(data, path, retries=2, delay=0.5):
    for attempt in range(retries + 1):
        try:
            ...  # mkdir + json.dump
            return
        except OSError:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise ArtifactError(...) from None
```

- 默认值：`retries=2, delay=0.5`（最多 3 次尝试，间隔 0.5s）
- 重试对象：仅 `OSError`（PermissionError, FileNotFoundError 等 I/O 异常）
- 不重试对象：`json.JSONDecodeError`

### 3. Spec Deviation #3：不重试 json.JSONDecodeError

**违反了什么**：最初的 spec 草案要求对所有异常统一重试。实际实现将 `json.JSONDecodeError` 排除在重试之外。

**原因**：`json.JSONDecodeError` 表示文件内容已损坏（非 JSON 格式）。这是一个**持久性**错误——等待 0.5s 不会让损坏的 JSON 变得合法。重试只会浪费 1.5s（3 次 × 0.5s）后仍然失败。

**代价**：如果文件因并发写入处于不一致状态（如另一个进程正在写入），3 次重试均会遇到 `json.JSONDecodeError` 并失败。但这不应发生——`write_json` 本身是同步的，且工件文件不被多进程共享。

## Consequences

- 调用方可按异常类型区分错误来源：gate 失败 → `GateFailureError`，文件问题 → `ArtifactError`
- `ArtifactError` 携带 `path` 和 `reason`，日志可直接定位问题文件
- 临时 I/O 抖动（如 NFS 延迟）通过最多 3 次尝试自动恢复，不影响下游
- `json.JSONDecodeError` 不参与重试，避免浪费 1.5s 等待
- 若将来出现多进程共享工件文件的场景，需重新评估 `JSONDecodeError` 的重试策略
