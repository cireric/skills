# Task Planning Workflow

按任务复杂度选择规划方式，避免过度仪式或欠规划。

## 决策树

```
需求/想法
    ↓
是否有多个决策点或歧义？
    ├── 否 → 直接做（简单任务）
    └── 是 → /grill-with-docs（对齐决策，更新 CONTEXT.md + ADR）
                ↓
            /to-prd（产出规格文档）
                ↓
            涉及几个模块？有几个决策点？
                ├── 单模块，≤3 决策点（中等） → /hyperplan → /start-work
                └── 多模块，>3 决策点（复杂） → /to-issues 垂直切片
                                                    → 每片按需: /hyperplan → /start-work
                                                    ↓
                                                验证回路（测试 → 对齐 → commit）
                                                    ↓
                                                实施后 skill（按需）：
                                                ├── /diagnose — 查 bug
                                                ├── /improve-codebase-architecture — 架构深化
                                                ├── /tdd — 补测试
                                                └── /zoom-out — 理解上下文
```

## 复杂度评估

不用"步数"判断——"步"的定义因人而异。用以下两个信号：

| 信号 | 简单 | 中等 | 复杂 |
|------|------|------|------|
| **涉及模块数** | 1 | 1-2 | 3+ |
| **决策点数量** | 0-1 | 2-3 | 4+ |
| **是否需要跨文件协调** | 否 | 有限 | 是 |

- **模块** = 一个有独立接口的代码单元（一个 Python 文件、一个 React 组件、一个 API endpoint）
- **决策点** = 需要人工确认的选择（接口设计、数据结构、依赖取舍、架构方案）

### 典型例子

| 任务 | 模块 | 决策点 | 复杂度 | 流程 |
|------|------|--------|--------|------|
| 修 typo | 1 | 0 | 简单 | 直接做 |
| 加一个 config 字段 | 1 | 1 | 简单 | 直接做 |
| reporter.py 加 test conditions 表格 | 1 | 2 | 中等 | hyperplan → start-work |
| 新增 i18n 标签系统 | 2 | 3 | 中等 | hyperplan → start-work |
| 10 issue 的 PRD 全量实施 | 5+ | 8+ | 复杂 | to-issues → 逐片执行 |

## 各阶段规则

### /grill-with-docs

- **触发条件**：任务有 ≥2 个决策点或存在歧义
- **不触发**：改 typo、加字段、修 lint error 等无需对齐决策的任务
- **副作用**：同步更新 CONTEXT.md（术语）和 ADR（不可逆决策）。后续所有 skill 读到的术语是对齐后的
- **不可跳过的原因**：术语不对齐 = 后续 skill 各说各话，PRD 和 issues 用词不一致，atlas 更容易幻觉

### /to-prd

- **触发条件**：经过 grill 或有足够上下文后，需要把决策固化为规格文档
- **不触发**：简单任务不需要 PRD
- **产出**：user stories + implementation decisions + testing decisions + out of scope
- **关键**：implementation decisions 不写文件路径和行号（会过时），写接口和行为

### /to-issues

- **触发条件**：复杂任务（多模块、多决策点）
- **产出**：垂直切片 issues，每个 issue 有 acceptance criteria 和 blocked-by
- **垂直切片原则**：每个 issue 切穿所有层（schema → API → test），不是按层拆（"先改 schema，再改 API"）
- **HITL vs AFK**：需要人工确认的 issue 标 HITL，agent 可独立完成的标 AFK
- **并行安全**：同文件的 issue 用 blocked-by 串行；不同文件的 issue 可并行 delegate

### /hyperplan + /start-work

- **触发条件**：中等任务，或复杂任务的单个 issue
- **/hyperplan**：5 个 hostile agent 交叉质疑，lead 综合。产出 .omo/plans/ 下的 plan 文件
- **/start-work**：atlas 读取 plan → 自动分解 sub-task → 逐条执行 → boulder.json 追踪进度
- **约束来源**：atlas 的自由度被上一层的产出约束——PRD 约束 issues，issue 的 acceptance criteria 约束 atlas
- **worktree**：需要隔离时用 `--worktree`，在独立分支工作，完成后 merge 回主分支

### 实施中发现的 skill

这些 skill 不在决策树的主路径上，而是在实施过程中按需触发：

| Skill | 触发时机 | 用途 |
|-------|----------|------|
| `/tdd` | 实现新功能或修 bug 时 | 红绿重构循环，一次一个垂直切片 |
| `/diagnose` | 遇到 bug 或测试失败时 | 结构化排查：复现 → 最小化 → 假设 → 修复 → 回归测试 |
| `/improve-codebase-architecture` | 发现模块过浅或耦合过紧时 | 深化模块，提高可测试性和 AI 可导航性 |
| `/zoom-out` | 不熟悉某段代码的全局角色时 | 跳出细节，看模块在系统中的位置 |
| `/prototype` | 架构决策前需要验证方案时 | 抛弃式原型，验证后删除或吸收 |

#### /tdd 的两种用法

- **实现手法**（默认）：嵌入 atlas 执行过程，每个 sub-task 走 red-green-refactor。PRD 已定义接口时直接用
- **前置探索**（按需）：在 start-work 之前单独跑 tdd，用测试描述期望行为来验证接口设计。只在接口不确定、需要用测试"试错"时使用

### 实施中发现的决策点

实施过程中可能发现 PRD / issue 没覆盖的新决策点。处理规则：

1. **影响范围限于当前 issue** → agent 自行决定，记录在 commit message 里
2. **影响其他 issue 或改变 PRD decision** → 停下来，问人。不擅自修改其他 issue 的 scope
3. **发现新 issue 值得做** → 记录但不立即开做，当前 issue 完成后再评估优先级
4. **原则**：实施中的新发现只能**收缩**当前 issue 的范围（发现不需要做某事），不能**扩展**（发现还想做另一件事）。扩展需要回到规划阶段

## 验证回路

实现完成后的验证流程：

1. **全量测试**：`pytest` 全绿（零失败，pre-existing 失败单独标注）
2. **Acceptance criteria 逐条对照**：每个 issue 的 checklist 项在代码中验证
3. **PRD 对齐检查**：回读 PRD 的 implementation decisions，确认：
   - 每条 decision 在代码中有对应实现
   - 代码中的实际实现没有超出 decision 范围（scope creep）
   - decision 里的细节（如 label 列表、字段名）与代码一致
4. **对齐失败时**：更新 PRD 使其与实际一致（PRD 是历史决策记录，应反映真实决策结果），不回退代码去迎合 PRD 的过时描述

### 谁来判定，判定后干嘛

| 验证项 | 判定者 | 通过后 | 失败时 |
|--------|--------|--------|--------|
| 全量测试 | 自动（CI / agent 运行） | 进入下一步 | 修复代码，重跑 |
| Acceptance criteria | agent 逐条验证 + 人工抽查 | 进入下一步 | 修复代码或更新 criteria |
| PRD 对齐 | 人工审阅 | commit | 更新 PRD（以代码为准） |

全部通过 → commit（需人工确认）。不自动 commit。

## 背景决策记录

### 规则：grill-with-docs 不可跳过

- **问题**：跳过 grill 直接写 PRD，术语不对齐导致 issues 之间用词不一致（同一个概念在两个 issue 里叫不同名字），atlas 执行时产生歧义
- **当时的解法**：grill-with-docs 在对齐决策的同时更新 CONTEXT.md，强制所有后续 skill 使用统一术语
- **结论**：grill 的价值不只是"问清楚"——它还建立术语基础设施，后续 skill 都依赖它

### 规则：每层约束逐级收紧

- **问题**：大功能直接扔给 Prometheus+Atlas，atlas 自由度过大，plan 粒度粗，执行时容易"创造性发挥"
- **当时的解法**：用 to-issues 拆成垂直切片，每个 issue 的 acceptance criteria 约束 atlas 范围
- **结论**：跳层（跳过 to-issues 直接让 atlas 执行 PRD）= 幻觉风险

### 规则：同文件 issue 串行执行

- **问题**：#7（reference numbering）和 #8（test conditions）两个 agent 并行改 reporter.py，合并时 test_proceed.py fixture 缺少 methodology section 导致测试失败
- **当时的解法**：手动修复 test_proceed.py，补上 methodology section
- **结论**：同文件的 issue 用 blocked-by 串行；不同文件的 issue 可以并行

### 规则：PRD 完成后对齐检查

- **问题**：PRD Module 9 的 _LABELS 列表只写了 3 个 label key（sources/references/test_conditions），实际实现需要 7 个（+claim/conditions/date/source_type，来自 Test Conditions 表格的列头）
- **当时的解法**：复盘时发现，更新 PRD Module 9 补全 label 列表
- **结论**：PRD 在实施过程中会被细化，完成后必须回读对齐。以代码为准，PRD 是记录
