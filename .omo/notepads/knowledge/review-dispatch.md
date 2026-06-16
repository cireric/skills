# 审查派遣

从 info-collector-improvement 项目中提炼的审查知识。

## 派遣审查任务时必须传入 guardrail 清单

审查子代理不知道项目的设计决策和 guardrail，会把"计划内设计"误判为"意外质量问题"。

**反面案例**：F2（Code Quality Review）将 6 个 `except Exception` 块标记为违规，但其中部分是 Guardrail 保护的合理设计（如 `_count_sources()` 和 `_read_topic()` 的 `except Exception` 是设计如此）。

**规则**：派遣审查任务时，prompt 中必须包含：
1. 项目的 guardrail 清单（哪些行为是设计如此）
2. 相关的设计决策（ADR 摘要或关键决策上下文）

否则审查者无法区分"有意的例外"和"意外的质量问题"。
