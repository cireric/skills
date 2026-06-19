# Search Strategy Template

## Tier-Based Search Order

Execute searches by tier, starting from the broadest community sources and narrowing to authoritative ones:

1. **Tier 4 — Community breadth scan**: Search Reddit, Hacker News, Stack Overflow for current discussions, pain points, and emerging themes. Use broad queries to map the topic landscape.

2. **Tier 3 — Industry depth articles**: Search Medium, IEEE Spectrum, MIT Technology Review, and vendor blogs for structured analysis, case studies, and expert opinions. Use targeted queries from Tier 4 findings.

3. **Tier 1 — Academic validation**: Search arXiv, Google Scholar for peer-reviewed evidence, benchmarks, and formal frameworks. Use precise technical terms from Tier 3 findings.

## Per-Round Strategy

| Round | Focus | Target | Query Style | MUST DO |
|-------|-------|--------|-------------|---------|
| 1 | Breadth | Tier 4 + Tier 3 | Broad English queries; scan for key themes | Update search_plan.json task statuses after round |
| 2 | Depth | Tier 3 + Tier 1 | Targeted queries based on Round 1 findings | **MUST fetch full content** for Tier 1 sources using `webfetch` |
| 3 | Gap-fill | Any tier | Follow up on uncovered directions; verify specific claims | Update search_plan.json; fetch any remaining full content |

## Search Plan Compliance (MANDATORY)

`search_plan.json` is generated automatically by `proceed --from scope --to search`. It contains one task per (direction × tier) combination. You MUST follow it:

### Before searching
1. Read `search_plan.json`
2. Identify tasks with `status: "pending"` for the current round's tier

### During searching
3. For each pending task, execute a search using that task's `site_queries` and `query_language`
4. Use `site:` queries (e.g., `site:arxiv.org human-AI delegation`) rather than generic queries

### After each search round
5. For each task that now has ≥ `min_sources` matching results: set `status: "completed"` and update `collected_count`
6. For tasks that are not applicable to this research: set `status: "skipped"` (add a note explaining why)
7. Write the updated `search_plan.json` back to disk

### Before running `proceed --from search --to analysis`
8. Verify every direction has at least one `completed` task
9. If any direction has zero completed tasks → search more before proceeding

## Full Content Fetch (MANDATORY)

Search-result highlights are NOT sufficient as `fetched_content`. They are summaries, not source material.

### After each search round
For every URL you plan to add to `collected.json`, call `webfetch` (or `exa_web_fetch_exa`) to retrieve the full page content. Store the fetched text in `fetched_content`.

### Per-tier minimum fetched_content lengths
| Tier | Minimum | Why |
|------|---------|-----|
| 1 | 1000 chars | Papers have methodology, results, limitations |
| 2 | 800 chars | Docs have API details, configuration |
| 3 | 600 chars | Blogs have context, nuance, caveats |
| 4 | 400 chars | Forum posts are shorter but must be fetched |

### If a URL cannot be fetched
Set `fetched_content: ""` and `fetch_failed: true`. This exempts the entry from depth checks but prevents it from being the sole source for `precision: "exact"` claims.
