# Subagent Delegation Template

When delegating section writing to independent agent calls in Phase 3a, follow these rules.

## JSON Schema

Each subagent must output a JSON object with these EXACT fields (no others):

```json
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
```

- Use "id" NOT "section_id"
- Use "source_urls" NOT "sources"
- "claims" is REQUIRED, use [] if no claims
- "key_insights" is REQUIRED for panoramic/exploratory sections (min 2), optional otherwise
- "tensions" is optional — include only when sources genuinely disagree
- "depth_strategy" is REQUIRED — must be one of: overview, deep_dive, comparison, methodology
- Do NOT add fields like "word_count", "language", etc.

## Source Content Injection

When constructing each subagent prompt, the orchestrator MUST inject ALL source references from collected.json:

1. For each entry in collected.json, inject:
   - The source title
   - The `source_file` path so the subagent can read the full original text via the Read tool
   - The `snippet` (1-2 sentence summary for relevance screening)
2. Include in the subagent prompt under a "## Source Content" heading:

   ```
   ## Source Content
   For each source, the title, snippet, and source_file path are provided below. You MUST use the Read tool on the source_file path to read the original text before writing any claim — titles and snippets are for relevance screening, not for content extraction. Select sources relevant to your section based on the snippet content.

   ### [URL1](url1)
   - Title: <title from collected.json>
   - Snippet: <snippet from collected.json>
   - source_file: sources/abc123def456.md

   ### [URL2](url2)
   - Title: <title from collected.json>
   - Snippet: <snippet from collected.json>
   - source_file: sources/def789ghi012.md
   ```

## Assembly Step 2: Write content FIRST, extract claims AFTER

Within each call, first write the complete Markdown narrative (tables, comparisons, detailed parameters, architecture breakdowns), then extract structured claims from what you wrote.

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
