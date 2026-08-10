# ADR 0044: table_suggestion WARN check

## Context

T2 report had zero Markdown tables across 5 sections, while the research skill's report on the same topic used 15+ tables for enterprise rosters, product lineages, policy timelines, and market data. The writing-guide requires "Structured tables for any multi-dimensional comparison" but this rule was not enforced or prompted by any gate check.

Root cause: agent in narrative mode defaults to paragraphs; without external prompting, it does not switch to tables even when information structure would benefit. Not an exploratory-specific issue — ecosystem/product sections with multiple entities naturally suit tables.

## Decision

Add `table_suggestion` WARN check to report_checks: if a section has ≥4 claims, emit WARN suggesting the author consider using Markdown tables for structured data presentation.

Threshold rationale: ≥4 claims indicates multiple structured data points (entity names, numbers, comparisons) that are more scannable in table format. This is a simple proxy — not all 4-claim sections need tables, but the false-positive cost is low (just a WARN).

## Consequences

- Lightweight: one threshold check, no entity detection or NLP
- WARN level: does not block pipeline, just prompts reconsideration
- Experimental: threshold may need adjustment after more runs. If false positives are high (many 4-claim narrative sections that genuinely don't need tables), raise threshold or add entity-type filtering
- Combined with ADR 0043 (full source injection), subagents see more information and are more likely to naturally produce tabular content

## Status: accepted
