# ADR-0001: Daily Focus Skill Enhancements

**Status:** Partially superseded by ADR-0002 (Decision #1 — archive rule)  
**Date:** 2026-07-29  
**Context:** Grill session on daily-focus skill optimization

## Decisions

### 1. Cross-day Carry-over
- Scan **last 7 days** of `YYYY-MM-DD.md` files for unfinished tasks
- Ask user whether to bring each unfinished task into today's pool
- Tasks moved to today: mark in source file as `→ 移入 YYYY-MM-DD`
- Tasks ignored by user: mark in source file as `→ 已忽略`
- Completed tasks stay as `[x]`; source files with no unfinished tasks are archived to `archived/` subdirectory

### 2. Next Action Refinement
- After Top 3 is confirmed, ask for **next concrete action** for each task
- E.g., "下一步具体动作是什么？"  "腾讯云配置 → 登录腾讯云控制台创建 CVM 实例"

### 3. Eat the Frog Sorting
- Top 3 automatically ordered by **estimated difficulty** (hardest first)
- User can manually reorder after seeing the recommendation

### 4. Time Estimation
- After sorting, ask for time estimate per task: `<30min / 30min-2h / 半天以上`
- Warn if total estimated time exceeds reasonable daily capacity

### 5. Next-day Review Reminder
- When running the skill, check yesterday's file
- Prompt user to review yesterday's completion before starting today's planning

### 6. todo.md Positioning
- todo.md is a **long-term inbox** for fuzzy ideas and things worth long-term attention
- Not a structured todo list; ideas are clarified only when they enter daily focus

## Deferred
- Time Blocking integration — revisit when there is demand
- Evening review mode — defer until opencode supports scheduled triggers
- Multi-source data integration (calendar, GitHub Issues, etc.)
