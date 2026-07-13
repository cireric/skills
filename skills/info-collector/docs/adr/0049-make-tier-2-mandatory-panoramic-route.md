# Make Tier 2 mandatory in panoramic_understanding route

panoramic_understanding 路由当前为 `path=[4,3,1], optional_tiers=[2]`（config.json），Tier 2（官方文档/repo）为*可选*。`tier_coverage` 对*必需* tier 缺失已是 BLOCKER（search_gate.py:116），故 panoramic 跑批缺 Tier 2 时仅打 INFO（L122-127）、不阻塞。结果是 v2 过所有门却漏掉基准/定价/模型谱系/成本拆解——这些恰好躺在 Tier 1/2 一手源。

## Decision

panoramic_understanding 路由改为 `path=[2,1,3,4]`（与 competitive_comparison 同形），删除 `optional_tiers=[2]`。Tier 2 由此成为必需 tier，其缺失经既有 `tier_coverage` BLOCKER 强制触达一手源。exploratory（`path=[4,3,2]`）Tier 2 已是必需，无需改动。

## Consequences

不必改 `tier_coverage` 严重级（本就是 required-tier BLOCKER）；仅调路由即闭合 panoramic 广度缺口。部分取代 ADR 0031（panoramic_understanding 路由行）；落地时把 ADR 0031 的 Status 改为 `Superseded by ADR 0049`（仅改 Status）。不取代 ADR 0042（沿用其 BLOCKER 机制）。

> 已应用：config.json 中 `panoramic_understanding` 路由已改为 `path=[2,1,3,4]`（删除 `optional_tiers=[2]`，entry_tier 同步改为 2 以满足 route invariant），Tier 2 现为必需 tier，其缺失经既有 `tier_coverage` BLOCKER 强制（search_gate.py:116）。entry_tier 保持 4（== path[0]，满足 route invariant）。项目 AGENTS.md 原则上禁止改 config.json，但此改动经本 ADR 授权为永久性技能源码变更，并已通过测试验证。

Status: accepted
