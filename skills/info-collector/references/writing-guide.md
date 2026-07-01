# Writing Guide for analysis.json Content

## Content Quality

**Content quality is the #1 priority.** The `content` field is rendered as-is in the final report by reporter.py. If the content is thin, the final report will be thin. Write as if you are writing the final report section.

### Content must include

- **Structured tables** for any multi-dimensional comparison (framework features, benchmark scores, protocol specs, pricing, etc.). Tables are the primary way engineers extract information — prefer tables over paragraphs for comparisons.
- **Specific numbers with context** — not "scores around 70%" but "Claude Opus 4.5: 80.9% on Verified, ~45-48% on Pro, ~33pt gap"
- **Architecture details** — not "uses AsyncGenerator" but "AsyncGenerator core loop, ~4,683 lines, 43+ built-in tools, 5-layer permission model (from full-auto to per-action approval), DeepImmutable state management"
- **Concrete examples** — not "supports parallel agents" but "git worktrees isolate each agent's working directory, branch, and staging area; `/apply-worktree` rebase/merges changes back"

### Content length guidance

Each section's content should be 500-2000 words of substantive analysis. If a section has less than 300 words, it is almost certainly too thin — check if tables or details are missing.

### Sub-headings

Use sub-headings (`###`) within content to organize complex sections. Example: a "Framework Comparison" section should have `###` sub-headings per framework.

### No top-level headings in content

Content must not start with `# ` or `## `. All headings must be `### ` or below. The section `title` itself serves as the `## ` level — content is nested under it.

### Concreteness self-check

Before finalizing each section's content, verify:
- Every number has context (not "70% accuracy" but "70% on MNIST, 65% on CIFAR-10 under 5-shot conditions")
- Every entity has a specific name (not "a framework" but "LangChain v0.3")
- Comparisons use tables, not paragraphs
- Each claim has its source referenced via `{{ref:URL}}` markers adjacent to the claim in content

## Source Traceability

Content must ensure source traceability:

- **Every quantified claim (benchmark numbers, percentages, etc.) must include a source identifier**: use `{{ref:URL}}` format where URL matches an entry in collected.json. The reporter assigns reference numbers automatically. **DO NOT** use hardcoded reference numbers like `[1]` or `[8]`.
- **Benchmark data must include a test environment summary**: at minimum hardware, OS, runtime version, test date
- **Every source name in the report must have a corresponding full clickable URL**

### Goal-type differentiated traceability

| goal_type                                                                   | Minimum traceability                                          |
| --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `tech_selection`, `competitive_comparison`, `feasibility_assessment`        | Each benchmark datum annotated with source URL + test conditions (CPU/OS/version/date) |
| `academic_research`                                                         | Formal citation format (e.g., `[1]` appendix mapping)         |
| `exploratory`, `market_analysis`, `background_check`, `fact_check`, `other` | Each claim with at least source URL or reference number        |
| `panoramic_understanding`                                                   | Each major conclusion paragraph with at least one source link  |

## Tier-aware Source Citations

Different source tiers require different language in body text to accurately reflect their evidentiary weight:

| Source Tier | Citation Language Rule | Example |
|-------------|----------------------|---------|
| Tier 1 (official docs, standards body) | Cite as authoritative | "According to OpenAI's official documentation..." |
| Tier 2 (industry reports, established media) | Cite with source attribution | "A 2025 Gartner report estimates..." |
| Tier 3 (blogs, tutorials, community posts) | Use qualifier: "according to a blog post", "a community analysis suggests" | "A community benchmark on Reddit suggests..." |
| Tier 4 (forums, personal pages, unverified) | Use strong qualifier: "an unverified source claims", "according to a forum post" | "An unverified forum post claims..." |

Never present Tier 3 or Tier 4 findings with the same authority as Tier 1 or Tier 2. The citations in body text must let readers assess evidentiary weight at a glance.

**Note**: The †/‡ verification markers in the final report are injected automatically by `reporter.py` based on `source_verification_check()` results. You do not need to add them manually in content. Tier-aware citation language (e.g., "according to a blog post") is still your responsibility as the writer.

## Precision Rules for Claims

- `evidence_type: "third_party_estimate"` or `"qualitative_trend"` → MUST NOT use `precision: "exact"` (gate BLOCKER)
- `precision: "exact"` → MUST have `evidence_type` of `"official_data"` or `"independent_benchmark"`
- Benchmark numbers from different test conditions → use `precision: "range"` and annotate in `source_metadata.test_conditions`

## Methodology Section

For quantitative goal_types (`tech_selection`, `competitive_comparison`, `feasibility_assessment`, `market_analysis`, `academic_research`), include a section with `id="methodology"` in analysis.json. This section must describe:

- Data sources and their test conditions
- Limitations of cross-source comparisons
- Date range of data collection

## Recommendation Structure (for `tech_selection` / `competitive_comparison`)

For `tech_selection` and `competitive_comparison` goal types, the report must include a structured recommendation section with three components written in the `content` field of analysis.json (no separate schema fields).

### Recommendation Matrix

A comparison table that scores each option against key criteria:

| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Performance | 30% | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Cost | 25% | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Ecosystem | 25% | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Learning Curve | 20% | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

Scores must be justified with evidence from the report body. Use emoji scales (⭐/★), numeric (1-5), or descriptive (Strong/Moderate/Weak). Include a weight column when criteria have different importance.

### Key Decision Factors

A numbered list of the most important factors users should consider when choosing:

1. **Factor name** — Explanation supported by evidence from comparison sections
2. **Factor name** — Explanation supported by evidence from comparison sections

Each factor must reference specific data rather than general impressions.

### Not-Recommended Scenarios

Explicitly state when each option should NOT be chosen:

- **Option A** — Not recommended for X scenario because...
- **Option B** — Not recommended for Y scenario because...
- **Option C** — Not recommended for Z scenario because...

This section must use explicit "not recommended" language so readers can quickly identify unsuitable options. Place it under a section with `id: "recommendation"` (or as part of `id: "comparison"` if space is tight).

## Anti-patterns (DO NOT)

- ❌ Writing all sections in a single agent call → token-limit compression makes content thin
- ❌ Writing claims before content → constraints thinking, produces checklist not narrative
- ❌ Using paragraphs where a table would be clearer → engineers scan tables, not walls of text
- ❌ Vague qualifiers without numbers → "significantly higher" is useless; "23% vs 80.9%, ~33pt gap" is useful
- ❌ Omitting architecture details because "the reader can look it up" → the report IS the lookup
- ❌ Content starting with `## Section Title` — top-level headings create structural conflicts with the report template
- ❌ Pronouns without antecedents — "它支持并行处理" → what is "它"? Name it explicitly every time
- ❌ Separating sources from claims — source URLs must be adjacent to their claims, not collected at the end
