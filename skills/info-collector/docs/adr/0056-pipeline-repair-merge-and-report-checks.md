# Pipeline repair loop: re-merge after fix + report checks as CLI post-step

ADR 0054 规定"合并只执行一次"（`_MERGE_COMPLETED_KEY` 幂等守卫），ADR 0055 引入 repair loop 允许 review-fix subagent 修改 section 文件。两者存在语义冲突：repair 的本质是"执行第二次"，但幂等守卫阻止重合并。DeepSeek 调查复盘发现 review-fix subagent 正确修改了 `analysis_section_*.json`，但 `analysis.json` 因幂等守卫拒绝重合并，最终报告包含 review 已标记为 BLOCKER 的错误内容。同时，`_gate_final` 实现了 3 项 BLOCKER 级报告检查，但因 `review→final` 走 `_gate_review(from_phase="review")` 而非 `_gate_final(from_phase="final")`，报告检查从未被执行。更深层的时序问题：报告在 `review→final` gate 通过后才由 `report` 命令生成，gate 执行时报告文件尚不存在。

## Decision

### 1. repair loop 后自动重合并

在 `_gate_review(to_phase="final")` 中，`check_fix_report()` 返回 `blocker_fixed > 0` 时，删除 `analysis.json` 并重新调用 `_merge_section_files()` + `_sanitize_sections()`，然后继续后续 gate 检查。重合并后的 analysis.json 才是 repair loop 检查和最终报告的基础。

选择此方案而非 mtime 比较方案，因为：(1) 精确触发——只在修复确实发生时重合并；(2) Windows 文件系统 mtime 精度问题；(3) agent 用 Read 工具读 section 文件可能意外触发 mtime 更新。

此决策取代 ADR 0054 的"合并只执行一次"规则。新规则为：**合并只在显式触发条件下执行**——首次合并由 `_gate_analysis` 触发，修复后重合并由 `_gate_review(to_phase="final")` 触发。`_MERGE_COMPLETED_KEY` 幂等守卫保留用于防止同一 gate 内重复合并，但不再阻止跨 phase 的重合并。

### 2. 报告检查从 pipeline gate 移到 CLI 后置步骤

删除 `_gate_final` 作为 pipeline gate 的角色。在 `cmd_report` 中，报告生成后立即调用 `run_report_checks()`，BLOCKER 级失败则报告不保存 + 报错退出。agent 修复后重新调用 `report` 即可。

此方案而非新增 `final→cleanup` 转换，因为：(1) ADR 0029 已删除 cleanup phase，加回来是倒退；(2) 报告生成是 CLI 命令而非 pipeline phase，检查与生成同属 CLI 职责更自然；(3) 不需要改状态机。

### 3. review self-loop 最小校验

`review→review` 转换增加最小校验：`review_report.md` 必须存在（确认上一轮 review 已执行）。不检查 fix_report（重新 review 时可能尚未进入 repair loop）。

## Consequences

repair loop 修复不再丢失。报告检查在正确时序执行。review self-loop 不再零校验。ADR 0054 的"合并只执行一次"被本 ADR 取代。`_gate_final` 函数可删除或保留为 `cmd_report` 内部复用。

Status: accepted

Supersedes: ADR-0054
