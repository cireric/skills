# ADR 0028: Reposition info-collector as Research Starting Point

## Context

Two production runs showed that the quality-gated report positioning is unsustainable:
1. The Harness Engineering report had 6 fabricated numbers pass through all gates into the final report
2. Gates verified structure, not semantic truth — review fixed claims[] but not content field
3. AI-verifying-AI is unreliable: the review subagent can be as wrong as the writing subagent

## Decision

Reposition info-collector from "quality-gated report" to "research starting point — panoramic map with traceable sources". Core shift: from "eliminate fabrication" to "make fabrication visible".

Key changes:
1. Three-level source_verification (confirmed/absent/indirect) computed by deterministic code, not LLM
2. †/‡ markers in report body for absent/indirect sources
3. Review subagent does semantic checks only, not claim verification
4. claim_verified downgraded to WARN — no longer blocks pipeline
5. claim_source_relevance removed, replaced by source_verification_check
6. quality → review_status rename; verification_required: true in front matter
7. /info-collector explicit invocation only (no auto-trigger words)

Design decisions:
- **Indirect takes priority over confirmed/absent**: Even if a number IS found in source, an indirect source classification means the source itself is not primary. The ‡ marker warns readers.
- **Write-back happens in _gate_analysis(), not inside ClaimValidator**: Avoids stale-data overwrite from ClaimValidator's pre-loaded data.
- **Review gate is advisory-only**: No checks block the review→final transition.

## Consequences

- Users can no longer trust the report as citable authority — they must verify †-marked claims themselves
- Pipeline no longer blocks on unverified claims — faster completion, more honest output
- Deterministic source_verification is reproducible and testable, unlike LLM verification
- Supersedes aspects of ADR 0005 (verified field) and ADR 0025 (gate phase responsibility) — they remain valid for their original context but the repositioning changes how these mechanisms are used

## Status: accepted
