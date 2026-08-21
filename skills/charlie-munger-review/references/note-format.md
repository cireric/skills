# 复盘笔记格式

复盘 Phase 4 结束后写到 `${notes_dir}/<决策简称>-YYYY-MM-DD.md`（`notes_dir` 来自 `../config.json`，默认 `.omo/munger-notes`）。

## 文件名清洗

`<决策简称>-YYYY-MM-DD.md`。简称由芒格从决策提炼（≤20 字）。替换 `/ \ : * ? " < > | +` 为 `-`，合并连续 `-`，截断 100 字符。日期用复盘当天。

## 笔记格式

```markdown
---
date: YYYY-MM-DD
decision: <一句话决策>
outcome: <结果，已显现>
paths_not_taken: [<决策树岔口：没选的路 + 为什么没选>]          # Phase 1 穷尽未走路径
bias_circle_of_competence: <越界/未越界>      # 能力圈必检结论
bias_inversion: <想过反例/没想过>             # inversion 必检结论
biases_hit: [<命中的偏误英文 slug，来自 cognitive-biases.md>]
biases_screened_out: [<扫过但判定未命中的偏误 slug>]          # Phase 2a 穷尽扫描的"排除"记录
lollapalooza: <是/否>                          # 多偏误同向叠加
opposing_biases: [<对冲偏误 slug 对，如 ["envy","deprival-superreaction"]>]  # 异向内耗，可为空
severity: <轻/中/重>                           # 芒格判断（定义见下）
unresolved_disagreements: [<X vs Y + 双方简述理由>]          # Phase 3 收手的未决归因分歧，可为空
lessons: [<当 X 信号时做 Y 而非 Z 格式的教训>]
---

## 决策与结果
<决策是什么、当时怎么推理的、结果如何>

## 未走路径（Phase 1 岔口）
<当时的岔口、没选的路、为什么没选>

## 能力圈（必检）
<这次是否越界？在不懂的领域做了判断？>

## 反向思考 inversion（必检）
<当时想过会死在哪吗？想过但没重视？为什么？>

## 命中的偏误
### <偏误英文 slug>
<为什么中了、证据、Phase 3 复盘对话摘录>

### <偏误英文 slug>
...

## 扫过但排除（biases_screened_out）
<Phase 2a 判定未命中的项，一行一条，证明穷尽扫描——没漏检>

## Lollapalooza / 对冲偏误分析
<同向叠加 → lollapalooza；异向 → 对冲偏误 opposing_biases>

## 芒格的话（毒舌总结）
<第一人称芒格的收尾>

## 教训
<当 X 信号时做 Y 而非 Z 格式，最重的一两条，可执行>

## 未决分歧（若有）
<Phase 3 收手的 X vs Y + 双方理由>

## 上次教训落实（若非首次复盘）
<读取上一份笔记的 lessons 字段，对照本次决策问用户落实情况，记录于此>
```

## severity 三档定义

| 档 | 定义 | 判定标准 |
|---|---|---|
| 轻 | 偏误对决策方向影响小，即使没有此偏误决策也大概率不变 | 偏误是陪因，去掉后决策仍成立 |
| 中 | 偏误显著影响决策，但没有它决策可能反转 | 偏误是主因之一，去掉后决策需重新评估 |
| 重 | 偏误是决策反转的关键，没有它决策会朝相反方向 | 偏误是决定性主因，去掉后决策明显反转 |

## 教训格式

教训必须采用 **"当 X 信号时做 Y 而非 Z"** 格式，X 是可观测的触发信号，Y 是替代行为，Z 是原本错误行为。

- 合格：当"身边所有人都在买某标的"信号出现时，做"独立查基础概率与买卖逻辑"而非"跟风下单"
- 不合格：下次要更谨慎 / 要避免冲动 / 多想想——无可观测触发信号，无具体替代行为

## 累积查询

`/charlie-munger-review:history` 读 notes/ 下所有文件的 frontmatter：
1. 统计 `biases_hit` 频次，按 severity 加权（权重见 `../config.json` 的 `severity_weights`），输出"你历史上反复中的偏误"加权排行（如"社会认同 加权 15 分、剥夺反应 加权 9 分…"）。加权排行优先于纯频次——"轻 × 5"不应压过"重 × 1"
2. 汇总所有 `unresolved_disagreements`，输出"仍未决的归因分歧"清单

复盘 Phase 0 自动读同一目录：
1. **提取偏误频次**：用于 Phase 2b 标注"你历史上第 N 次中 X 偏误"和 Phase 3 选历史反复命中的偏误深挖（频次仅作权重不作 ground truth，权重 ≤ 50%）
2. **读取上一份笔记的 lessons 字段**：Phase 1 开始前先问用户"上次复盘的教训是 X，这次决策有没有遇到同类信号？落实了吗？"——教训追踪闭环
3. **读取上一份笔记的 unresolved_disagreements 字段**：Phase 1 开始前先问"上次没定的归因分歧是 X vs Y，这次有没有新证据倾向哪边？"——未决分歧待验闭环

无历史档案时（首次复盘），Phase 0 跳过，Phase 3 改选"最致命的"2-3 个深挖。