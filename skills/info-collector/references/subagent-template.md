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

## Numeric Claim Source Rule

Any claim containing a specific number (percentage, dollar amount, benchmark score, etc.) MUST satisfy one of these conditions:

1. **The number appears verbatim in the `fetched_content` of the cited source** — use `precision: "exact"` or `"range"`.
2. **The number does NOT appear in `fetched_content`** — you MUST either:
   - Use `precision: "qualitative"` and rephrase without the exact figure (e.g., "outperformed the baseline by a significant margin" instead of "72.2% vs 64.8%"), OR
   - Use `precision: "range"` with a conservative range (e.g., "~70-75%" instead of "72.2%"), OR
   - Remove the claim entirely.

**Rationale**: The review subagent cross-checks every exact number against `fetched_content`. Numbers not present in the fetched source will be flagged as precision inflation and may block the review gate.

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
