---
name: learnings
description: Use when starting non-trivial implementation work, hitting a blocker or pitfall, or when the user asks to consolidate recurring engineering lessons. Loads prior experience from .omo/notepads and captures new pitfalls so the same mistake is not repeated across sessions or agents.
---

# Learnings — cross-session engineering experience memory

> **Convention:** `venv-python` means the venv Python interpreter for the current platform:
> Windows: `.venv\Scripts\python.exe` · Linux/macOS: `.venv/bin/python`

A lightweight, Atlas-independent port of oh-my-openagent's `.omo/notepads/` pattern:
experience lives in append-only markdown under `.omo/notepads/{scope}/`, survives across
sessions, and is injected into new work as "Inherited Wisdom". Any agent can use it — no omo plugin required.

## When to use

- **Before starting a non-trivial task** — retrieve prior experience (avoid repeating pitfalls).
- **When you hit a blocker / pitfall / gotcha**, or discover a working pattern — capture it.
- **When the USER explicitly asks** to consolidate recurring lessons into rules — run `debrief`.
- **Never** auto-edit `AGENTS.md`. Upcycle only on explicit user request, and only after a pitfall recurs across tasks.

## Core loop (3 phases)

### 1. Retrieve (BEFORE work)

```bash
venv-python skills/learnings/scripts/learnings.py retrieve --scope <scope> [--category issues] [--topic <kw>]
```

Read the output and fold relevant entries into your plan as "Inherited Wisdom".
Run this at task start, not after you've already repeated a mistake.

### 2. Capture (on pitfall / on success pattern)

```bash
venv-python skills/learnings/scripts/learnings.py capture \
  --scope <scope> --category <learnings|decisions|issues|problems|verification> \
  --task-id <id> --content "<what happened and what to do differently>"
```

`init` once per scope to create the category files:

```bash
venv-python skills/learnings/scripts/learnings.py init --scope <scope>
```

### 3. Upcycle (USER-requested ONLY, gated on repetition)

```bash
venv-python skills/learnings/scripts/learnings.py debrief --scope <scope>
```

Prints a PROPOSAL (recurring keywords + suggested next step). **It never writes `AGENTS.md`.**
Promote a pitfall to a rule only when: (a) the user asks, and (b) it has recurred across >=2 tasks.

## Quick reference

| Phase | Command | Note |
|---|---|---|
| init | `init --scope X` | create `learnings/decisions/issues/problems/verification.md` |
| retrieve | `retrieve --scope X [--topic kw]` | read before work |
| capture | `capture --scope X --category Y --task-id Z --content "..."` | append-only |
| debrief | `debrief --scope X` | proposal only, never edits AGENTS.md |

## Common mistakes / red flags

- **Using `Write` on a notepad file** — destroys history. Always go through `capture` (append-only).
- **Retrieving AFTER the mistake** — must run at task start.
- **Agent auto-writing `AGENTS.md`** — forbidden. Debrief only proposes; the user promotes.
- **Single pitfall -> rule** — too noisy. Wait for recurrence across tasks.
- **Wrong scope** — pick a stable scope (project or subsystem), not a throwaway task id.

## Why this exists

Without it, agents reinvent the same fixes every session: pitfalls vanish into chat history,
new tasks don't see old lessons, and experience never becomes permanent. This skill closes that loop
without the heavy prometheus/atlas orchestration.
