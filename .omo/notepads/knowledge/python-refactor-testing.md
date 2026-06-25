# Python 重构测试策略

从 info-collector 代码质量优化实践中提炼的测试策略经验。

## 每步跑全量测试，不要攒

每完成一个重构步骤就跑全量测试。出问题时必定是最近一步引入，bisect 成本为零。攒多步再跑，排查范围成倍增长。

## 子进程隔离测试验证 facade 无副作用

`test_gateway_import.py` 在子进程中 `import scripts.gateway` 并验证没有加载 forbidden 模块。重构后 gateway 变成 re-export facade，测试仍通过——说明 facade 模式没有引入意外的模块加载副作用。

**规则**：这类隔离测试对重构安全网很有价值。当模块角色从"实现"变为"re-export facade"时，用子进程隔离测试验证无意外副作用。
