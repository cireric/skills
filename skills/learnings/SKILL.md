---
name: learnings
description: Post-development summary command. After finishing a task, the user runs /learnings so the agent captures the session's pitfalls, gotchas, and working patterns into append-only .omo/notepads/{scope}/ memory that survives across sessions and agents. Supports an optional [scope] argument; auto-detects the scope when omitted. Never auto-edits AGENTS.md.
disable-model-invocation: true
argument-hint: "[scope]"
---

# Learnings — cross-session engineering experience memory

> **Convention:** `venv-python` means the venv Python interpreter for the current platform:
> Windows: `.venv\Scripts\python.exe` · Linux/macOS: `.venv/bin/python`

A lightweight, Atlas-independent port of oh-my-openagent's `.omo/notepads/` pattern:
experience lives in append-only markdown under `.omo/notepads/{scope}/`, survives across
sessions, and is injected into new work as "Inherited Wisdom". Any agent can use it — no omo plugin required.

## When to use

**Scope:** the `<scope>` argument used below identifies a stable bucket (project or subsystem
name) under `.omo/notepads/{scope}/`. If the user passes an argument to `/learnings`
(e.g. `/learnings myproject`), use it as the scope. If omitted, auto-detect from the repo /
project name or current working directory. Never use a throwaway task id as scope.

Two modes, lightest first:

- **Post-dev summary (recommended, user-triggered)** — after finishing a task, the user runs
  `/learnings`. Reflect on the session and `capture` the pitfalls + experience. This is the
  primary, low-overhead way to build the cross-session memory; the user trigger guarantees it runs.
- **Consult before a task (optional)** — before a non-trivial task, `retrieve` prior experience
  to avoid repeating pitfalls. Optional in the lightweight mode; the persistent log is the value.
- **When the USER explicitly asks** to consolidate recurring lessons into rules — run `debrief`.
- **Never** auto-edit `AGENTS.md`. Upcycle only on explicit user request, and only after a pitfall recurs across tasks.

## What to capture (triage rubric)

Before `capture`, decide if it is worth surviving across sessions. Use the rubric below so every
`/learnings` run applies the same standard — neither over-capturing noise nor missing real lessons.

**The five buckets**

| Category | Capture | Skip |
|---|---|---|
| `learnings` | reusable working patterns ("do this next time") | one-off slips / typos |
| `decisions` | key choices **+ why** (stops mindless reverts) | anything already in AGENTS.md |
| `issues` | pitfalls / blockers / gotchas — the trap **and** the fix | raw task-progress chatter |
| `problems` | unsolved items / tech debt | throwaway state that dies at the next refactor |
| `verification` | "X works / X doesn't" conclusions | secrets / customer data |

**Capture only if ≥2 of these hold:**

1. **Reusable** — a future similar task will hit it again (not one-task progress).
2. **Non-obvious** — not visible from code / docs / error text alone; it is tacit "you had to learn it".
3. **Costly or valuable** — it burned debugging time, or will save someone else's.

**Skip (noise):** one-off typos · pure task-progress logs · anything already in AGENTS.md ·
throwaway state that dies at the next refactor · secrets / customer data.

## Core loop (3 phases)

### 1. Retrieve (optional, before a future task)

```bash
venv-python skills/learnings/scripts/learnings.py retrieve --scope <scope> [--category issues] [--topic <kw>]
```

Read the output and fold relevant entries into your plan as "Inherited Wisdom".
Recommended before a non-trivial task to avoid repeating pitfalls. In the lightweight
post-dev mode this is optional — the persistent log is the main value.

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
| retrieve | `retrieve --scope X [--topic kw]` | optional: read before a future task |
| capture | `capture --scope X --category Y --task-id Z --content "..."` | append-only |
| debrief | `debrief --scope X` | proposal only, never edits AGENTS.md |

## Common mistakes / red flags

- **Using `Write` on a notepad file** — destroys history. Always go through `capture` (append-only).
- **Forgetting to capture after dev** — the user runs `/learnings` post-dev to guarantee it; don't skip it.
- **Agent auto-writing `AGENTS.md`** — forbidden. Debrief only proposes; the user promotes.
- **Single pitfall -> rule** — too noisy. Wait for recurrence across tasks.
- **Wrong scope** — pick a stable scope (project or subsystem), not a throwaway task id.

## Why this exists

Without it, agents reinvent the same fixes every session: pitfalls vanish into chat history,
new tasks don't see old lessons, and experience never becomes permanent. This skill closes that loop
without the heavy prometheus/atlas orchestration.
