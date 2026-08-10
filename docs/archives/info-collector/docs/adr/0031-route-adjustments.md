# ADR 0031: Route Adjustments — Source Tier Path Revisions and Chinese Academic Sources

## Context

After implementing source fidelity (ADR 0030), a grilling session reviewed all 10 goal_type routes in config.json. Several routes had suboptimal tier ordering that didn't match the information-seeking behavior of each goal type. Additionally, Tier 1 lacked Chinese academic database coverage beyond CNKI.

## Decision

### 1. Route path revisions

| route | original path | revised path | rationale |
|---|---|---|---|
| exploratory | [4,2] | [4,3,2] | +Tier 3 for industry trend perspective alongside community signals |
| tech_selection | [2,1] | [2,3,4,1] | docs→industry→community→academic; industry shows adoption trends, community reveals real-world pain points before academic validation |
| feasibility_assessment | [2,1] | [2,1,3] | docs→academic feasibility→industry cases; industry cases validate practical viability |
| competitive_comparison | [2,3,4,1] | [2,1,3,4] | academic benchmark data before community opinions; benchmarks are objective ground truth |
| background_check | [3,4,2,1] | [3,2,1,4] | official docs before community; background research needs authoritative sources first |
| market_analysis | [3,1,2] | [3,4,1,2] | +Tier 4 for early trend signals; community behavior (Reddit/HN/Zhihu) is the earliest market indicator |
| academic_research | [1] | [1], optional_tiers=[2] | main line stays Tier 1; optional Tier 2 for tech docs when reproducing experiments |

Unchanged routes: panoramic_understanding [4,3,1] optional_tiers=[2], fact_check [1,2,4], other [3,2,1].

### 2. New Tier 1 sources

- **Wanfang** (wanfangdata.com.cn): Chinese academic database, `language: "zh"`, same Tier 1 as CNKI
- **CQVIP** (cqvip.com): Chinese academic database (维普), `language: "zh"`, same Tier 1 as CNKI
- 国标 (gb688.cn) was considered but excluded due to persistent connection timeout issues
- Both Wanfang and CQVIP share CNKI's abstract-only access limitation; the existing source_verification + precision mechanism handles "abstract has it, full text doesn't" naturally

## Consequences

- Tier 1 now has 11 sources (was 9), with 3 Chinese-language sources (CNKI, Wanfang, CQVIP)
- tech_selection and competitive_comparison now search 4 tiers instead of 2, increasing search time but improving coverage
- academic_research gains optional Tier 2 without forcing it — gate won't block on missing Tier 2
- Test assertions for route paths updated to match new config
- CONTEXT.md updated with Route Decisions section referencing this ADR

## Status: Superseded by ADR 0049 (partial: panoramic_understanding route row — panoramic now `[2,1,3,4]`, see ADR 0049)
