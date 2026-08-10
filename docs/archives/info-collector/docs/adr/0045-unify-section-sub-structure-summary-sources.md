# ADR 0045: Unify section sub-structure to {summary, sources} base pattern

Subagent schema compliance was the #1 cause of gate failures (3/3 fails in T2 run): key_insights output as string instead of dict, tensions used `title` instead of `description`. Root cause is not "subagent doesn't follow schema" but schema heterogeneity — three sub-structures (key_insights, tensions, claims) use different field names for the same concept (text/description, source_urls/sources), forcing subagent to switch between three naming modes in one JSON.

Unify all three to a shared base pattern `{summary, sources}`:
- key_insights: `[{text, source_urls}]` → `[{summary, sources}]`
- tensions: `[{description, sources}]` → `[{summary, sources}]`
- claims: `[{text, source_urls, ...}]` → `[{summary, sources, evidence_type, confidence, precision, ...}]`

`summary` is more neutral than `text`/`description` — a key insight is a summary, a tension is a summary, a claim is a summary. `sources` eliminates the `source_urls` vs `sources` naming split. Subagent learns one base pattern; claims extend it.

Supersedes: ADR 0017 Decision 2 (subagent output schema dual safeguard — `_sanitize_sections` field mapping `sources → source_urls` is reversed; new mapping is `text → summary`, `description → summary`, `source_urls → sources`).

Status: accepted
