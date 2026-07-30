# ADR-0002: Time-based Archive for Historical Daily Focus Files

**Status:** Accepted  
**Date:** 2026-07-30  
**Supersedes:** ADR-0001, Decision #1 (archive rule)  

## Context

The original archive rule (ADR-0001 #1) archived a file only when all its tasks were completed (`- [x]`). For multi-day tasks that never reach 100% completion, this caused stale files to accumulate indefinitely in `{focus_dir}/`, making the directory increasingly noisy.

## Decision

Replace completion-based archival with time-based archival:

1. **Trigger**: Every `/daily-focus` run, **before** building the task pool.
2. **Scope**: Files older than 7 days (excluding `todo.md`, today's file, already-archived files).
3. **Per-file handling**:
   - No unfinished tasks → silently archive to `archived/`.
   - Has unfinished tasks → prompt user per-unfinished-task with four options:
     - Move to `todo.md`
     - Bring into today's pool (re-evaluate urgency)
     - Mark complete
     - Abandon (no longer track)
   - After handling all tasks, move file to `archived/`.
4. **Summary**: Report "N files archived, M tasks handled" after completion.

## Rationale

- Time-based triggers handle multi-day tasks gracefully compared to completion-based triggers.
- Interactive handling per-unfinished-task prevents silent data loss when archiving.
- Running before task pool building ensures decisions feed into today's focus.

## Deferred

- Configurable archive threshold (7 days as default) — not needed yet.
