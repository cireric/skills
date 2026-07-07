# Subagent Delegation Template

When delegating section writing to independent agent calls in Phase 3a, follow these rules:

## Delegation Rules

1. **One section per agent call** — never write all sections in a single call. This prevents token-limit compression and ensures each section gets full output capacity.
2. **Write content FIRST, extract claims AFTER** — within each call, first write the complete Markdown narrative (tables, comparisons, detailed parameters, architecture breakdowns), then extract structured claims from what you wrote.
3. **Embed allowed URL list in every subagent prompt** — extract all URLs from `collected.json` and include them in the prompt as the **only** valid `source_urls`. Any `source_url` not in this list will be caught by the `analysis→review` gate's url_traceability check and block progression. Format:

   ```
   ## Allowed source URLs (use ONLY these in source_urls)
   - https://example.com/article1
   - https://example.com/article2
   ...
   ```

4. **Specify output path with `.workdir/` prefix in every subagent prompt** — subagents must write their output to `<project_root>/.workdir/`, NOT the project root. Include this instruction explicitly:

   ```
   ## Output path
   Write your section JSON to: <project_root>/.workdir/analysis_section_<id>.json
   Do NOT write to the project root.
   ```

5. **Include JSON schema in every subagent prompt** — embed the exact expected structure to minimize schema violations:

   ```
    ## Required JSON structure
    Write a single JSON object with these EXACT fields (no others):
    {
      "id": "<section_id>",
      "title": "<section title>",
      "content": "<full Markdown content, must NOT start with ## >",
      "depth_strategy": "<overview|deep_dive|comparison|methodology>",
      "key_insights": [
        {
          "text": "<insight statement with causal direction or key finding>",
          "source_urls": ["<url from allowed list>"]
        }
      ],
      "tensions": [
        {
          "description": "<description of disagreement or conflict between sources>",
          "sources": ["<url from allowed list>"]
        }
      ],
      "claims": [
        {
          "text": "<claim statement>",
          "source_urls": ["<url from allowed list>"],
          "evidence_type": "official_data|independent_benchmark|third_party_estimate|qualitative_trend|expert_opinion",
          "confidence": "high|medium|low",
          "precision": "exact|range|qualitative",
          "source_metadata": { "test_conditions": "...", "test_date": "...", "source_type": "..." }
        }
      ]
    }
    - Use "id" NOT "section_id"
    - Use "source_urls" NOT "sources"
    - "claims" is REQUIRED, use [] if no claims
    - "key_insights" is REQUIRED for panoramic/exploratory sections (min 2), optional otherwise
    - "tensions" is optional — include only when sources genuinely disagree
    - "depth_strategy" is REQUIRED — must be one of: overview, deep_dive, comparison, methodology
    - Do NOT add fields like "word_count", "language", etc.
   ```

## Source Content Summary Injection

When constructing each subagent prompt, the orchestrator MUST inject source content for URLs relevant to that section:

1. Identify which URLs are relevant to the section (from section plan + source_hints)
2. For each relevant URL, inject:
   - First 500 characters of the original text (from `.workdir/sources/{url_hash}.md`)
   - The `source_file` path so the subagent can read deeper via the Read tool
3. Include in the subagent prompt under a "## Source Content" heading:
   ```
   ## Source Content
   For each source, the first 500 chars are provided below. For deeper detail, use the Read tool on the source_file path.

   ### [URL1](url1)
   - source_file: sources/abc123def456.md
   - Preview: <first 500 chars of original text>

   ### [URL2](url2)
   - source_file: sources/def789ghi012.md
   - Preview: <first 500 chars of original text>
   ```
4. This gives the subagent actual source data to write from, reducing fabrication tendency

## Deep-Dive Topic Injection

When the section plan includes `deep_dive_topics`, the orchestrator MUST inject them into the subagent prompt. This is critical for panoramic/exploratory sections where the orchestrator has selected key findings for deep argumentation.

Inject deep-dive topics under a "## Deep-Dive Topics" heading in the subagent prompt:

```
## Deep-Dive Topics
You MUST write ≥ 2 deep-dive paragraphs in this section. Each deep-dive paragraph
argues one key finding with 3+ sources. The orchestrator has identified these topics
as the most important findings in this direction:

1. **<topic_1>** — Suggested sources: <url1>, <url2>, <url3>
   Selection criterion: <tension|impact|mechanism>

2. **<topic_2>** — Suggested sources: <url4>, <url5>
   Selection criterion: <tension|impact|mechanism>

You may use sources beyond the suggested ones. The suggested sources are advisory,
not exhaustive. If you find a more important finding than the suggested topics while
writing, you may substitute it — but you must still write ≥ 2 deep-dive paragraphs
and each must satisfy at least one selection criterion (tension, impact, or mechanism).
```

## Depth Strategy Injection

The orchestrator MUST inject the section's depth strategy into the subagent prompt. This determines the content organization rules the subagent must follow.

```
## Depth Strategy: <overview|deep_dive|comparison|methodology>
Follow the content organization rules for this strategy from writing-guide.md.
```

For **overview** strategy sections, the subagent must produce:
- 1-2 paragraphs of breadth-first summary
- ≥ 2 deep-dive anchor paragraphs (each with 3+ sources, satisfying tension/impact/mechanism)
- Optional: 1 tension paragraph, 1 action paragraph (only if source-supported)

For **deep_dive** strategy sections, the subagent must produce:
- Full analysis with structured comparison tables
- Every major claim argued with 2+ sources
- Contradictions surfaced with resolution conditions

For **comparison** strategy sections, the subagent must produce:
- Comparison matrix, key decision factors, not-recommended scenarios
- See writing-guide.md "Recommendation Structure" for full requirements

For **methodology** strategy sections, the subagent must produce:
- Data sources, test conditions, cross-source comparison limitations, date range

## Assembly Step

Merge all sections into a single analysis.json. **This step is JSON merge only — never rewrite or rephrase section content.** Each section's `content` and `claims` fields are taken verbatim from the subagent outputs. If content needs improvement, go back and re-delegate that section.

```json
{
	"topic": "...",
	"goal_type": "tech_selection",
	"audience": "engineer",
	"sections": [
		{
			"id": "comparison",
			"title": "Comparison",
			"content": "Full Markdown narrative with tables, details, and sub-headings...",
			"depth_strategy": "comparison",
			"key_insights": [
				{
					"text": "Key finding with causal direction",
					"source_urls": ["https://..."]
				}
			],
			"tensions": [
				{
					"description": "Source A claims X while Source B claims Y",
					"sources": ["https://...", "https://..."]
				}
			],
			"claims": [
				{
					"text": "Claim statement",
					"source_urls": ["https://..."],
					"evidence_type": "official_data | independent_benchmark | third_party_estimate | qualitative_trend | expert_opinion",
					"confidence": "high | medium | low",
					"precision": "exact | range | qualitative",
					"source_metadata": {
						"test_conditions": "Brief description of test methodology and hardware",
						"test_date": "2026-Q1",
						"source_type": "vendor_benchmark | independent_test | production_case | survey"
					}
				}
			]
		}
	]
}
```

Every claim MUST have at least one source_url linking to a URL in collected.json.

## Numeric Claim Source Rule

Any claim containing a specific number (percentage, dollar amount, benchmark score, etc.) MUST satisfy one of these conditions:

1. **The number appears verbatim in the original source text file** (`.workdir/sources/{url_hash}.md`) — use `precision: "exact"` or `"range"`.
2. **The number does NOT appear in the source text file** — you MUST either:
   - Use `precision: "qualitative"` and rephrase without the exact figure (e.g., "outperformed the baseline by a significant margin" instead of "72.2% vs 64.8%"), OR
   - Use `precision: "range"` with a conservative range (e.g., "~70-75%" instead of "72.2%"), OR
   - Remove the claim entirely.

**Rationale**: The review subagent cross-checks every exact number against the original source text files. Numbers not present in the source file will be flagged as precision inflation and may block the review gate.

**NEVER infer or calculate exact numbers from ratios, percentages, or other derived data.**
If the source says "revenue grew 15%" and you want to state the dollar amount, you MUST find the actual dollar figure in fetched_content. Calculating "$4.2B from 15% growth" is fabrication, not analysis.

**Example violations to avoid**:
- ❌ Claim: "Agyn achieves 72.2% on SWE-bench 500" with `precision: "exact"` when the fetched_content only mentions "multi-agent system" without the 72.2% figure
- ✅ Claim: "Agyn outperforms single-agent baselines on SWE-bench 500" with `precision: "qualitative"`
- ✅ Claim: "Agyn achieves ~70-75% on SWE-bench 500" with `precision: "range"`

## Citation format rule

When referencing sources in section content, use `{{ref:URL}}` format where URL
matches an entry in collected.json. Example: `domain knowledge can be classified{{ref:https://ar5iv.labs.arxiv.org/html/2212.00017}}`.

**DO NOT** use hardcoded reference numbers like `[8]` or `[&#91;8&#93;](#refs)`.
The reporter assigns reference numbers automatically based on first-appearance order.

Every URL in a claim's `source_urls` MUST also appear as `{{ref:URL}}` in the same
section's content. The gate will block if any claim source URL is not referenced in content.
