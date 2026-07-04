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
- ❌ Pseudo-synthesis — using causal/contradiction language ("核心矛盾是", "综合来看", "本质上") without causal evidence. If A and B co-occur but you cannot establish A→B with source support, write "A and B co-occur; whether a causal relationship exists is not established by the available sources" instead.
- ❌ Name-as-analysis — mentioning an entity + one-sentence description without evaluating its significance or comparing it to alternatives. Each section must have ≥ 2 analytical entries (entries with evaluation, comparison, or impact judgment, not just existence statements).
- ❌ Action-platitude — "readers need to understand X" or "engineers should be aware of Y" without specific, source-supported guidance. Either provide concrete action items ("prioritize X because Y, supported by [source]") or omit the action paragraph entirely.

## Depth Strategy (Per-Section)

Each section's content organization follows a depth strategy determined by goal_type × section id. The orchestrator specifies the strategy in the section plan; the writer must follow it.

### Strategy: overview (panoramic/exploratory sections, overview sections)

- 1-2 paragraphs of breadth-first summary covering the direction's landscape
- **≥ 2 deep-dive anchors** — each anchor is a paragraph that argues one key finding with 3+ sources
- Deep-dive anchor selection criteria (the finding must satisfy at least one):
  - **Tension**: multiple sources disagree or give different conclusions
  - **Impact**: the finding changes the reader's action or judgment
  - **Mechanism**: explains WHY/HOW, not just WHAT happened
- Optional: 1 tension paragraph noting contradictions or unresolved questions within the direction
- Optional: 1 action/decision paragraph — only if source-supported ("do X because Y [source]")

### Strategy: deep_dive (tech_selection comparison sections, fact_check sections)

- Full analysis with structured comparison tables
- Every major claim argued with 2+ sources
- Contradictions explicitly surfaced and resolution conditions stated
- For tech_selection: must include recommendation matrix + key decision factors + not-recommended scenarios

### Strategy: comparison (tech_selection/competitive_comparison)

- Structured comparison table scoring each option against key criteria
- Key decision factors with evidence references
- Not-recommended scenarios with explicit language
- See "Recommendation Structure" section above for full requirements

### Strategy: methodology (quantitative goal_types)

- Data sources and their test conditions
- Limitations of cross-source comparisons
- Date range of data collection
- Must be detailed enough for a reader to assess validity

### Depth strategy mapping (Phase 1 implicit)

| goal_type | section id | depth strategy |
|-----------|-----------|---------------|
| panoramic_understanding, exploratory, background_check | overview | overview |
| panoramic_understanding, exploratory, background_check | other sections | overview (with ≥ 2 deep-dive anchors) |
| tech_selection, competitive_comparison | overview | overview (brief) |
| tech_selection, competitive_comparison | comparison, recommendation | comparison |
| tech_selection, competitive_comparison | methodology | methodology |
| feasibility_assessment, market_analysis, academic_research | methodology | methodology |
| feasibility_assessment, market_analysis, academic_research | other sections | deep_dive |
| fact_check | * | deep_dive |
| other | * | overview (with ≥ 2 deep-dive anchors) |

## Synthesis Guard

All synthesis paragraphs must satisfy the **synthesis guard**: causal direction must be explicitly stated (A→B), and each step in the causal chain must have at least one source supporting it.

**Allowed synthesis** (passes synthesis guard):
> Tool convergence → protocol fragmentation → interoperability gaps → expanded attack surface. Each step is documented: convergence [3], fragmentation [15], gaps [16], attack surface [9].

**Disallowed synthesis** (fails synthesis guard):
> "The core contradiction is that capability growth far outpaces governance maturity." — This states a contradiction but provides no causal chain and no source-supported reasoning for why these two trends are contradictory rather than merely co-occurring.

**When synthesis guard cannot be satisfied**: Present the observations honestly as co-occurring phenomena:
> "Capability metrics (benchmark scores, adoption rates) are rising rapidly while governance metrics (maturity scores, compliance rates) remain flat [8]. Whether these trends are causally linked or independent is not established by the available sources."

## Panoramic Overview Section

The overview section in panoramic/exploratory reports has special rules:

1. **Prefer causal chain organization** — if cross-section causal links can be established (e.g., tool convergence → protocol fragmentation → security gaps), organize the overview around the causal chain. Each link must pass the synthesis guard.
2. **Fallback to annotated co-occurrence** — if causal links cannot be established, list each direction's key finding and annotate relationships where evidence exists ("A is related to B because [source]"). Do not force connections without evidence.
3. **Do not summarize each section** — the overview is not a table-of-contents with excerpts. It should reveal relationships between directions that are not visible within individual sections.
