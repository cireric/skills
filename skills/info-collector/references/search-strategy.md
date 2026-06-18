# Search Strategy Template

## Tier-Based Search Order

Execute searches by tier, starting from the broadest community sources and narrowing to authoritative ones:

1. **Tier 4 — Community breadth scan**: Search Reddit, Hacker News, Stack Overflow for current discussions, pain points, and emerging themes. Use broad queries to map the topic landscape.

2. **Tier 3 — Industry depth articles**: Search Medium, IEEE Spectrum, MIT Technology Review, and vendor blogs for structured analysis, case studies, and expert opinions. Use targeted queries from Tier 4 findings.

3. **Tier 1 — Academic validation**: Search arXiv, Google Scholar for peer-reviewed evidence, benchmarks, and formal frameworks. Use precise technical terms from Tier 3 findings.

## Per-Round Strategy

| Round | Focus | Target | Query Style |
|-------|-------|--------|-------------|
| 1 | Breadth | Tier 4 + Tier 3 | Broad English queries; scan for key themes |
| 2 | Depth | Tier 3 + Tier 1 | Targeted queries based on Round 1 findings; fetch full content |
| 3 | Gap-fill | Any tier | Follow up on uncovered directions; verify specific claims |

## Search Plan Compliance

After each search round, review `search_plan.json` and update task statuses:
- `status: "completed"` — direction covered with >= min_sources
- `status: "skipped"` — direction not applicable (explain why in collected.json notes)
- `status: "pending"` — still needs coverage

Before running `proceed --from search --to analysis`, verify all directions have at least one completed task.
