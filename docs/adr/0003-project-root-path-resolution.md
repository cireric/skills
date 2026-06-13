# ADR 0003: CLI 路径解析基于 project root 自动检测

- **Status**: Accepted
- **Date**: 2026-06-13
- **Context**: info-collector skill

## Context

CLI 的 `WORKDIR = Path(".workdir")` 和 `output_dir`（config.json 中默认 `./reports/`）都相对于 CWD。但 SKILL.md 约定所有路径相对于 project root（where `.git` is），AGENTS.md 第4条也如此描述。

实际运行时 CLI 必须从 skill 目录运行（因为模块导入路径），导致报告保存到 `skills/info-collector/reports/` 而非 project root 下的 `reports/`。

## Decision

CLI 启动时自动向上查找 `.git` 目录确定 project root。`output_dir` 和 `WORKDIR` 都相对于此解析。

实现：从 CWD 向上遍历父目录，找到第一个包含 `.git` 的目录作为 project root。如果找不到，fallback 到 CWD。

## Alternatives Considered

1. **文档对齐现状**：修改 AGENTS.md/SKILL.md，说明路径相对于 CWD。但这违反直觉——用户期望报告保存在项目根目录。
2. **环境变量指定**：通过 `PROJECT_ROOT` 环境变量。增加使用复杂度。
3. **CLI 参数指定**：通过 `--project-root` 参数。同上，增加复杂度。

## Consequences

- 报告和中间文件的位置符合用户直觉（project root 下）
- 无需修改 config.json 或用户习惯
- 在非 git 仓库中运行时 fallback 到 CWD（行为不变）
