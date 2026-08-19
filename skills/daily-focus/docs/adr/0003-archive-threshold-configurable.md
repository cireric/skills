# ADR-0003: Configurable Archive Threshold (archive_days)

**Status:** Accepted  
**Date:** 2026-08-18  
**Supersedes:** ADR-0002, Deferred item ("Configurable archive threshold (7 days as default) — not needed yet")  

## Context

ADR-0002 deferred configurability of the archive threshold. In practice the archive
step has since been expanded with task markers (`[someday:…]`, `[doing]`,
`[delegated:…]`, SKILL.md step 3B) and the threshold is now part of the skill's
config surface: users with weekly vs monthly review rhythms need different
retention, without editing the skill instructions.

## Decision

1. Add `archive_days` (default `7`) to `skills/daily-focus/config.json`.
2. The archive step (SKILL.md step 2 / 3B) reads `archive_days` from config;
   when absent, the default stays `7` (matching ADR-0002's original scope).
3. The carryover window in SKILL.md step 3C ("最近 7 个 `YYYY-MM-DD.md` 文件")
   is **intentionally independent** of `archive_days`: it is a recency window over
   the most recent files, not an age threshold, and remains fixed regardless of
   the configured archive age.

## Rationale

- Configurable retention without changing instructions keeps user-specific
  settings in `config.json` (single source of truth), consistent with how the
  skill already stores `focus_dir`, `todo_filename` and `top_n`.
- Keeping step 3C's window fixed avoids silently changing carryover semantics
  when a user tunes archive age; the two numbers answer different questions
  ("how old before archiving" vs "how many recent files to carry over").

## Supersede notes

- Partially supersedes ADR-0002 (Deferred item only); ADR-0002's remaining
  decisions (trigger before pool building, scope exclusions, per-task four
  options, summary format) remain in force.