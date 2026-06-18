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
   - Do NOT add fields like "word_count", "language", etc.
   ```

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
