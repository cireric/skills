# ADR 0040: Prohibit Agent-Summarized Source Files

Production run (2026 H2 AI coding agent tech selection, 23 sources) repeated the same failure mode as ADR 0032 despite the earlier fix. The agent correctly called `exa_web_fetch_exa` in batches and received full article text (20K-50K chars per URL), but then delegated to 3 subagents that "extracted key facts" and wrote condensed summaries (1.5K-5K chars) as source files instead of piping raw content to CLI `--from-stdin`. The gate passed because all files exceeded the 2000-char shallow threshold, but no source file contained actual full text. The pattern: agent treats fetched content as input to "process" rather than as payload to "store."

Root cause: SKILL.md Step 2.3 instructed "pipe the result to CLI" but did not mark it MANDATORY or prohibit alternative processing paths. The agent found it more "efficient" to summarize via subagents than to pipe each URL's content individually to CLI. This is the same underlying tendency as ADR 0032 — agents compress by default, and instructions must counteract this explicitly.

Changes:
1. SKILL.md Step 2.3 Path B step 2 now reads "MANDATORY — pipe the FULL result to CLI for post-processing. Do NOT write source files yourself."
2. Added "Anti-pattern: DO NOT summarize fetched content" section with explicit prohibition, common violation patterns (❌), and correct pattern (✅).
3. Source fidelity gate table adds a new row: >30% source files where content overlaps snippet by >80% → BLOCKER (heuristic to catch summary-not-full without requiring a known full-text baseline).

Supersedes: none (complements ADR 0032, which solved the "skip fetch entirely" variant; this ADR solves the "fetch correctly then throw away full text" variant).

Status: accepted
