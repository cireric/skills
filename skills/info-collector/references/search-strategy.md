# Search Strategy Guide

> **定位**：建议参考的搜索策略，不强制遵守。

## Free Search Approach

Search freely using the topic and scope_description as guidance. Use a mix of source tiers. There is no search_plan.json to follow — you decide your own search strategy.

### Language-aware search

Match search language to source language:
- **Chinese sources** (CNKI, Wanfang, CQVIP, CBOA, Zhihu): use Chinese keywords. When the topic contains Chinese entity names (e.g., "玄铁", "芯来"), Chinese search yields more precise results.
- **English sources** (arXiv, Google Scholar, Reddit, etc.): use English keywords.
- **Mixed topics**: try both languages for key entities. For example, "玄铁 C930" for Chinese sources and "Xuantie C930" for English sources.

### Entity-driven search

When you discover new entities during search (companies, products, standards), proactively search for them — don't wait for gate repair to prompt you. For example, if a source mentions "Andes Technology", search for it immediately rather than hoping to stumble upon it later.

### Breadth-first strategy

Prioritize breadth in the search phase:
1. Quick search across all tiers to confirm source existence and relevance (snippet is enough to judge)
2. Batch fetch full content for relevant sources
3. Don't fetch full content for every URL — skip clearly irrelevant ones early

### Fallback reference

When free search yields no results or gate BLOCKERs fire:
1. Consult scope.json search_directions as fallback search guidance
2. Use config.json source lists for repair hints (automatically provided by gate)
3. search_directions are not enforced — they suggest dimensions you may have missed

### Exa fallback for fetch failures

When the fetch CLI returns `content_insufficient: true` or `fetch_failed: true`:
1. Use exa (via exa_web_fetch_exa or exa_web_search_exa) to get the content
2. Pipe the content to CLI: `python -m scripts.cli fetch <url> --from-stdin`
3. The CLI will handle post-processing (write source file, return metadata)

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
