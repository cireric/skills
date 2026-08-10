# ADR 0021: 3d 报告终稿校验步骤

- **Status**: Accepted
- **Date**: 2026-06-19
- **Context**: info-collector skill

## Context

reporter.py 生成的 Markdown 报告在 2026-06-19 的"人与LLM协作原则"调研中，输出后经历了 4 轮手动修复才可读：字面量 `\n` 未换行、裸 URL 溢出行宽、参考文献不可见、引用不可点击。所有问题都是"源码看起来对，渲染出来不对"，且 reporter.py 输出后无任何校验环节。

现有流程中，3a/3b/3c 校验的都是 `.workdir/` 下的 JSON 文件（analysis.json、collected.json），最终报告文件 `reports/xxx.md` 从未被检查。

## Decisions

### 1. 新增 Phase 3d，位于 3c 之后、Phase 4 之前

3c 生成报告文件后，3d 对报告文件做终稿校验，通过后才进入 cleanup。

### 2. 3d 分两层：AI 终检 + Gateway check

- **AI 终检**：agent 读 `.md` 源码，按 SKILL.md 列出的允许语法格式做规则推理。覆盖需要判断力的检查项。
- **Gateway check**：在 `proceed --from final --to cleanup` 时自动运行。覆盖可确定编码的检查项。

### 3. 执行顺序：AI 终检 → proceed（含 gateway check）→ cleanup

AI 终检在 proceed 之前执行。理由：gateway check 通过的文件不一定 AI 终检通过，但 gateway check 不通过的文件 AI 终检也无意义。先过自动化关，再做人工判断。

### 4. 3d 只做 3c 无法预知的检查

reporter.py 的确定性 bug（`\n` 未换行、裸 URL、参考文献不可见、`preview-` 前缀）在 reporter.py 内部修复。3d 只负责 reporter.py 无法预知的渲染行为问题。

### 5. 渲染器基准：CommonMark + GFM

3d 以 CommonMark + GFM 为渲染正确性基准。不保证所有渲染器（Typora、pandoc 等）兼容。用户反馈特定渲染器问题后，agent 针对性修复。

### 6. 修复路径

- AI 终检不通过 → 直接编辑 `.md` → 重跑 AI 终检
- Gateway check 不通过 → 修 `.md` → 重跑 proceed

### 7. 不引入 pandoc

所有检查项要么 gateway 自动化，要么 AI 读源码推理。pandoc 的 HTML 输出与目标渲染器（VS Code、GitHub）行为不一致，引入依赖但不提供不可替代的价值。

## Gateway check 清单（10 项，全部 WARN）

| ID | 检查项 | 说明 |
|----|--------|------|
| F1 | 悬空引用 | 正文中 `[N]` 无底部定义 |
| F2 | 孤立定义 | 底部 `[N]` 无正文引用 |
| A | 参考文献可见性 | 参考文献区全是 `[N]: URL` 隐藏定义行，无可见列表 |
| D | 表格分隔行闭合 | 分隔行 `|` 数量与表头不一致 |
| 9 | Front matter 格式 | YAML front matter 解析失败或关键字段缺失 |
| 10 | 标题层级错乱 | 跳级（如 `##` 后直接 `####`）|
| 12 | 重复标题 | 同级别同文本标题出现多次 |
| 13 | 代码块未闭合 | ` ``` ` 出现奇数次 |
| 15 | 空章节 | 有标题但无内容 |
| 16 | 超长行 | 单行超过 500 字符 |

## AI 终检清单（4 项）

| ID | 检查项 | 通过标准 |
|----|--------|---------|
| B | 正文引用可点击 | 符合 SKILL.md 列出的允许语法格式 |
| C | 参考文献 URL 可点击 | URL 以 Markdown 链接语法包裹 |
| G | 无尾部 artifact | 文件末尾干净，无多余文本 |
| 11 | 内部锚点可跳转 | 正文 `(#anchor)` 与参考文献区锚点名称匹配 |

## Alternatives Considered

1. **3d 包含 reporter.py 的全部后处理**：意味着 reporter.py 永远输出脏数据，3d 是它的必要后处理。这等于把 bug 正式化成流程。拒绝。
2. **pandoc 转 HTML → AI/脚本检查 HTML**：pandoc 的渲染行为与 VS Code/GitHub 不一致，且引入外部依赖。所有检查项可不用 pandoc 实现。拒绝。
3. **3d 作为独立 CLI 命令**：3d 天然是 `final→cleanup` 转换的 gate，不需要新命令。拒绝。

## Consequences

- 报告出厂前必须经过渲染校验，不再出现"生成后不可读"的情况
- reporter.py 的确定性 bug 在产出端修复，3d 只兜底无法预知的问题
- `proceed --from final --to cleanup` 不再是空壳，包含 10 项自动检查
- AI 终检需要 agent 执行，增加约 2-3 分钟交互时间
