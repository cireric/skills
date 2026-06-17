# 依赖清理检查清单

当从代码库移除一个 pip 依赖时，必须检查以下三项，否则会留下不一致：

1. **venv 残留**：`pip list | grep <package>` 确认已卸载。代码中无 import 不等于 venv 中无安装
2. **ADR Status**：如果该依赖有对应 ADR，Status 必须改为 Superseded，加 `Superseded-by:` 指向替代 ADR
3. **文档引用**：CONTEXT.md、architecture.md、SKILL.md 中对该依赖的描述需同步修正

实例：jieba 在代码中已无 import（ADR 0012 改用内联 CJK 分段），但 venv 中仍残留 jieba 0.42.1，ADR 0001 Status 仍为 Accepted，CONTEXT.md 仍写"Uses jieba tokenization"。三处不一致在审计时才发现。
