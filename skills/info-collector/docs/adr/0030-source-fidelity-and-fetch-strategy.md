# ADR 0030: Source Fidelity — Original Text Storage and Fetch Strategy

## Context

A production run (2026 Agentic Coding trends, 40 sources) revealed that ALL `fetched_content` entries were LLM-rewritten summaries based on search highlights, not original web page text. The gate passed because it only checked character count, not content authenticity. The resulting report was assembled from fragmented summaries, lacking depth and precision.

The root cause is a structural gap: `fetched_content` is both the storage field (what gets saved) and the quality metric (what the gate checks), but LLM agents naturally write summaries rather than preserving original text. The field cannot serve both roles.

## Decision

Introduce **source fidelity** infrastructure: store original text as local files, let subagents read them on demand, and check file existence (not character count) at the gate.

### 1. Original text storage

- New directory: `.workdir/sources/{url_hash}.md` — markdown format, one file per collected entry
- `url_hash` = short hash of normalized URL (avoids filename conflicts and special characters)
- New field in collected.json: `"source_file": "sources/abc123.md"` — points to the local file
- `fetched_content` field downgraded to a 200-char index: first 200 chars of original text, for gate quick-check and subagent relevance screening. No longer a gate depth-check target.

### 2. Source fidelity gate

- Replaces `fetched_content_depth` check in SearchGate
- Checks `.workdir/sources/` file existence and non-emptiness
- Rule: if >30% of collected entries have no source file (and not `fetch_failed: true`), BLOCKER
- `fetch_failed: true` entries are exempt, but if >50% are exempt, WARN
- `fetched_content_depth` check removed

### 3. FetchStrategy — mixed declarative + code

- **config.json `url_rewrite`**: declarative regex rules per source, covers ~80% of URL rewriting
  ```json
  {
    "name": "arXiv",
    "domain": "arxiv.org",
    "fetch": {
      "url_rewrite": [
        {"match": "arxiv.org/pdf/(.+)", "replace": "ar5iv.labs.arxiv.org/html/$1"},
        {"match": "arxiv.org/abs/(.+)", "replace": "ar5iv.labs.arxiv.org/html/$1"}
      ],
      "tools": ["webfetch", "exa_web_fetch_exa"]
    }
  }
  ```
- **`fetch_strategies/*.py`**: code-based strategies for complex logic (e.g., GitHub default branch detection), covers ~20%
- **Resolution order**: code strategy (by name) → config `url_rewrite` → DefaultStrategy (no rewrite, tools=["webfetch"])
- **Fallback**: tools list tried in order; if first tool fails, try next

### 4. Fetch execution in Phase 2

- Orchestrator performs fetch serially in Phase 2 (Step 2.3), before gate
- Subagents in Phase 3 only READ files, never fetch
- Rationale: separation of concerns (fetch ≠ analysis), gate has meaningful data to check, no duplicate fetch across subagents

### 5. Adaptive retry by tier

| Tier | Retries per tool | Max attempts per URL |
|------|-----------------|---------------------|
| Tier 1 | 2 | tools × 2 |
| Tier 2 | 2 | tools × 2 |
| Tier 3 | 1 | tools × 1 |
| Tier 4 | 1 | tools × 1 |

- Global timeout: 60 seconds per URL
- All tools exhausted → `fetch_failed: true`

### 6. Subagent on-demand reading

- Prompt injection: first 500 chars of each source + file path list
- Subagent reads `.workdir/sources/` files via Read tool when deeper detail is needed
- Replaces current "Source Content Summary" injection (800-char LLM summary per URL)

## Consequences

- Reports will be based on original source text, not LLM summaries — fundamental quality improvement
- Pipeline takes 3-7 minutes longer in Phase 2 (serial fetch), acceptable for a research tool
- `fetched_content` field retains an index role but loses gate significance
- New `source_file` field in collected.json creates a coupling between collected entry and local file — cleanup must remove both
- FetchStrategy plugin system requires a naming convention (file name = strategy name) and an interface protocol
- Supersedes `fetched_content_depth` gate check from SearchGate
- Requires updates to: SKILL.md Phase 2 Step 2.3, SearchGate, subagent-template.md, reporter.py (if it reads fetched_content), config.json schema

## Status: accepted
