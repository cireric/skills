# 并行编排

## `run_in_background=false` 是串行排队，不是并行

同时发出多个 `task(run_in_background=false)` 调用时，调度器逐一执行。总耗时 = 各任务耗时之和。

**规则**：真正独立的任务用 `run_in_background=true`；共享文件的任务用 `run_in_background=false` 串行。
