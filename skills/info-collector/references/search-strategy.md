# Search Strategy Guide

> **定位**：建议参考的搜索策略，不强制遵守。

## Free Search Approach

Search freely using the topic and scope_description as guidance. Use a mix of source tiers. There is no search_plan.json to follow — you decide your own search strategy.

### Suggested tier mix

1. **Tier 4 — Community breadth scan**: Search Reddit, Hacker News, Stack Overflow for current discussions, pain points, and emerging themes.
2. **Tier 3 — Industry depth articles**: Search Medium, IEEE Spectrum, MIT Technology Review, and vendor blogs for structured analysis, case studies, and expert opinions.
3. **Tier 1 — Academic validation**: Search arXiv, Google Scholar for peer-reviewed evidence, benchmarks, and formal frameworks.

### When search gate BLOCKERs fire

Consult the repair_hints for suggested sources from config.json. repair_hints are generated from config.json's source lists and provide concrete site_query suggestions (e.g., "tier 2 零覆盖 → try site:github.com, site:en.wikipedia.org").

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
