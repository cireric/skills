# discovery-based facet_coverage safety net (WARN)

SKILL.md 把"覆盖度"定义为"该看的都看了吗"，但 `SearchGate` 只操作化为源数量 + 层级存在性，而非话题维度覆盖。ADR 0042 为不窄化视野、且因 Phase-1 方向无法预判搜索中发现的新主题，删除了 `topic_coverage`/`covered_directions`/`search_plan`。结果：报告可过所有门却缺整面（市场冲击、基准、模型谱系、已声明局限）——正是 v2 的情况。matt /research 的广度来自维度覆盖，而非源数量。

## Decision

在 `artifact_checks.run_all` 新增 `check_facet_coverage`（**WARN，安全网**，不阻塞）：

- **goal_type 感知的固定核心 facet 集**（派生式，非预设用户方向，保留 ADR 0042 取向）：
  - panoramic_understanding / exploratory：全集 `{technical_architecture, model_product_family, cost_economics, market_industry_impact, community_ecosystem, reported_limitations}`
  - fact_check / feasibility_assessment 等：窄集（不含 model_product_family 等不适用维度）
  - agent 可声明额外 facet（扩展点）。
- 每个 facet 须有 ≥1 条 `source_confirmed` 来源；缺失则 WARN + repair_hint 指向对应 tier 的 config 源。
- **`reported_limitations`**：WARN 级（与 B 其他 facet 一致），但附加**质量护栏**——若该 facet 存在，其来源须 Tier 1/2（违反则 WARN，防二手夸大短板）。Phase 1 访谈默认提示用户把"局限"声明为 `search_directions` 方向 → 进入 ADR 0052 的硬契约。
- **community_ecosystem 拓宽 + 多平台要求**：定义为 HF + Reddit/HN + Zhihu/Weibo + 市场新闻(Tier3)；其满足条件要求来源跨 ≥2 个平台（仅 HF 则 WARN），闭合 v2"中文社区 + 市场反应"双缺口。

## Consequences

在话题维度层面操作化"该看的都看了吗"，且不预设静态用户方向（与 ADR 0042 不窄化视野取向兼容）。加的是软（WARN）广度地板；agent 仍自由发现新实体。不取代 ADR 0042（机制不同：搜索后派生 vs 搜索前计划）。facet 集按 goal_type 作用域 + WARN 级别化解 ADR 0042 对"预设方向"的批评。需改动：`scripts/artifact_checks.py`（新增 `check_facet_coverage` + 社区多平台 + limitations 护栏，注册进 `run_all`）。

社区多平台保持 **WARN 而非 BLOCKER**：host 级检测过粗（同 host 不同 subreddit 计为单平台），且部分题目本就只有单一社区平台合理。根因修复靠 Phase 2 搜索指引强制多平台覆盖，本检查仅作兜底报警。

Status: accepted
