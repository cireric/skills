# ADR 0035: Remove Unreviewed Option — Minimum Review is Degraded (Inline)

Production run skipped review entirely (review_status=unreviewed), and the resulting report contained internal contradictions, inconsistent benchmark comparisons, and pseudo-synthesis — none of which were caught. The unreviewed option removes the only pipeline stage capable of detecting cross-section inconsistency, context twist, and vendor bias. Removing unreviewed: the minimum review level is now "degraded" (inline review by the same agent), ensuring semantic checks always run. If a subagent review fails twice, the agent performs the same workload itself (read scope/collected/analysis, run semantic checks, write findings). The front matter `review_status` field now has only two valid values: `passed` and `degraded`.

Status: accepted
