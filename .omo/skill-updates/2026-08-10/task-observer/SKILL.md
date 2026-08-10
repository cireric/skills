---
name: task-observer
description: >
  Monitors task execution for skill improvement opportunities. Use this skill
  during ANY multi-step task, agentic workflow, or substantive work session where
  the agent is using tools and producing deliverables. It captures patterns, user
  corrections, workflow insights, and methodology worth preserving as reusable
  skills. Also triggers during post-task feedback discussions and when the user
  explicitly mentions skill observations, improvements, the observation log,
  skill taxonomy, or asks the agent to watch for skill opportunities. IMPORTANT:
  this skill should be invoked at the start of every task-oriented session — if
  you are about to use tools to produce deliverables, invoke this skill first.
---

# Task Observer — Continuous Skill Discovery & Improvement

**Adapted from [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all)**
by Eoghan Henn / rebelytics.com. Licensed CC BY 4.0: share and adapt freely
with credit to the original author.

Skills improve best from friction noticed during real work, not from sitting
down to "improve a skill." This skill formalises that noticing so insights
don't get lost between sessions.

**Convention:** `venv-python` means the venv Python interpreter for the current
platform: Windows `.venv\Scripts\python.exe` · Linux/macOS `.venv/bin/python`.

## Scope and division of labor

This skill observes **skill-level improvements** (L1–L3):

- **L1: Skill file defects** — rules are ambiguous, missing, or violated
- **L2: Skill inter-operation** — skills don't hand off cleanly to each other
- **L3: Workflow/methodology gaps** — a workflow step is missing or could be a new skill

The `learnings` skill covers **project-level experience** (L3 auxiliary + L4 agent
behavior + L5 tool/environment quirks). When L3 overlaps, write both: task-observer
writes the normative perspective ("skill X should change"), learnings writes the
experiential perspective ("next time, remember to do Y").

**Do NOT log here:** one-off corrections, agent behavior habits, tool bugs, or
anything already captured in learnings notepads.

## Reference files — load on demand, not up front

- `references/weekly-review.md` — comprehensive review procedure, approval policy,
  delivery/staging of updated skills. Load when a review triggers or the user
  asks for one.
- `references/skill-authoring.md` — taxonomy details, licensing, attribution
  template, lean-content rule, confidentiality layers, editing rules. Load before
  creating or editing any skill.
- `references/environments.md` — activation/config setup, compaction behavior,
  known limitations. Load for setup questions.

These loads are mandatory steps, not suggestions: when an episode fires (review
triggers → weekly-review; creating/editing a skill → skill-authoring;
setup questions → environments), load the file before proceeding — never
improvise the episode from this core file.

## Session Start Protocol

1. If `.omo/skill-observations/log.md` or `.omo/cross-cutting-principles.md`
   don't exist, run `init`:
   ```bash
   venv-python skills/task-observer/scripts/task_observer.py init
   ```
2. Scan OPEN observations and active principles; hold them in awareness, don't
   surface unprompted.
3. Check review status:
   ```bash
   venv-python skills/task-observer/scripts/task_observer.py status
   ```
   If review is due (interval exceeded AND there are OPEN observations): offer
   the review in one line ("the observation backlog hasn't been reviewed in N
   days — run `/task-observer:review` now, or carry on?") and proceed with the
   user's task unless they opt in. Never gate the user's work on the review.
4. Once per session: if no AGENTS.md activation instruction for this skill
   exists, briefly suggest adding one (see `references/environments.md`).
5. Load before planning, not just before execution. If the session will
   produce a plan for user approval, relevant skills must be loaded *before
   the plan is written* — a plan is a user-approved artefact whose decisions
   are locked in at approval time; loading the skill at execution cannot
   recover decisions the plan already made.

## When to Observe

Active for the entire task session: execution, post-task feedback and review
discussion, meta-discussion about skills or methodology, and reflective/strategy
conversations about how work should be done. **The observation mindset does not
deactivate when the conversation shifts from doing the work to discussing it** —
user feedback in review phases is often the highest-signal input. Inactive only
for casual conversation and quick factual questions with no tools or deliverables
involved.

## What to Watch For

**Signals for a NEW skill:** a reusable multi-step workflow; a methodology the
user explains that no existing skill captures; a recurring task type with similar
structure; a process with clear inputs, phases, outputs; a structured approach
emerging naturally during work.

**Signals for IMPROVING an existing skill:** the agent violates a documented rule
(the skill needs enforcement, not louder rules); a user correction reveals a
missing rule or edge case; a better workflow emerges than the skill recommends; a
technique works well enough to promote from incidental to recommended; an
undocumented use case; feedback that generalises; a wrong assumption; new tooling
obsoletes a step; corrections forming a pattern; a principle that applies to other
skills too.

**Signals for SIMPLIFYING a skill:** a section never relevant across many sessions;
a rule from a single unvalidated observation; workflows users consistently shortcut;
sections loaded but never acted on; contradictory rules; "just in case" complexity
that never triggered; a rule the agent consistently fails to follow.

**Do NOT log:** one-off corrections that don't generalise; preferences already
captured in a skill; tool bugs unrelated to methodology; observations that would
need proprietary client information to be useful in an open-source skill.

## How to Log

Append to the log **silently, within the same turn or the next** — never batch
mentally for later; the act of writing is the enforcement mechanism. All log
mutations go through the Python script for concurrency safety (filelock,
collision detection, header-count verification).

**Mandatory observation checkpoint after every 3rd TodoWrite completion:** After
marking the 3rd, 6th, 9th (etc.) todo item as completed, you must **write to the
log** — either append any pending observations, or append an explicit
acknowledgement marker (`no observations`). The write itself is the enforcement
mechanism.

**Deliverable-event flush:** Whenever you present a major deliverable or complete a
task/todo batch, flush any pending observations to the log at that moment, before
moving on.

### Appending an observation

```bash
venv-python skills/task-observer/scripts/task_observer.py append \
  --session-context "what task was being worked on" \
  --skill "skill name | New skill candidate: [name]" \
  --type internal \
  --phase "which part of the skill or workflow" \
  --issue "What happened — specific enough to understand weeks later" \
  --improvement "Concrete change — name the section or rule" \
  --principle "The generalisable takeaway — the most important field" \
  [--reference-file "path/to/saved/context"]
```

The script handles: file locking, number assignment, collision detection, status
(`OPEN`) and date auto-fill, header-count verification. You provide the content;
the script handles the mechanics.

### Observation format

```markdown
### Observation [N]: [Short descriptive title]

**Status:** OPEN
**Date:** [date]
**Session context:** [what task was being worked on]
**Skill:** [existing skill name, or "New skill candidate: [working name]"]
**Type:** [open-source | internal]
**Phase/Area:** [which part of the skill or workflow]

**Issue:** [What happened]

**Suggested improvement:** [Concrete change]

**Principle:** [The generalisable takeaway]

**Reference file:** [path] (optional — include if observation depends on session-local data)
```

**Context preservation:** if an observation depends on session-local data, save
that context into the workspace first and pass `--reference-file` with the path.

**Confidentiality:** for `type: open-source` observations, the Principle must be
fully generalised — no client names, domains, or details traceable to a real
project. Full confidentiality layers: `references/skill-authoring.md`.

## Referencing Observations

When citing an observation by number — in conversation, in a review report, or
from within another observation — the number must come from the entry's literal
`### Observation N:` header line. Never cite a number from a search-tool line
number; those are positional metadata, not IDs. Sanity-check any cited number
against the known counter range (the highest `### Observation N:` header in the log).

## Surfacing Protocol

Default: at end of session, as a grouped summary — improvements grouped by skill,
new-skill candidates listed separately; for each, one sentence plus suggested type;
ask which to act on. Surface earlier when an observation needs user input to be
complete, when a skill is actively producing wrong output, or when observations
cluster on one skill.

**Default to log-and-defer.** Surfacing is not an invitation to act. The default
is log-and-defer: state that the observation is logged for the next review, and
stop. Reserve in-session application strictly for: (1) an explicit user request
that names the action; (2) correcting a skill that is producing wrong output in
the current session.

Do NOT routinely offer a binary "apply now vs leave for next review" choice.

**Self-check before surfacing:** observations were logged throughout the whole
session (including discussion phases); logged silently; each follows Issue →
Improvement → Principle; each is typed; existing-skill items name the section; no
open-source Principle contains client-identifying info; every observation carries
a Status line.

## Acting on Observations

Act only in three contexts: (1) the comprehensive review (load
`references/weekly-review.md`); (2) an explicit user request ("update X skill",
"act on observation #N"); (3) in-session correction when a skill is producing
wrong output. Otherwise: log, don't act.

When acting: small, clearly-additive, low-risk changes may be applied directly.
Substantial changes and all new-skill creation: load `references/skill-authoring.md`
first. If an observation reveals a principle that applies to skills generally,
propose it for the cross-cutting principles file.

## Commands

| Command | Purpose |
|---------|---------|
| `/task-observer:init` | Initialize `.omo/skill-observations/` directory, log.md, last-review-date.txt, config.json |
| `/task-observer:review` | Run weekly review (load `references/weekly-review.md`) |
| `/task-observer:status` | Show OPEN/ACTIONED/DECLINED counts + review due check |

Observation appending and archive are handled by the Python script, called by
the agent during work and review respectively — no slash command needed.

## Quick Reference

| Question | Answer |
|----------|--------|
| When do I observe? | The whole session, including feedback and reflection phases |
| How do I log? | Silently, immediately, via `task_observer.py append` |
| When do I surface? | End of session, or earlier if needed |
| Status line? | Mandatory `**Status:** OPEN` — auto-filled by the script |
| Citing an observation number? | Only from its literal `### Observation N:` header |
| Open-source or internal? | Default internal; use open-source when generalisable |
| Small fix or substantial? | Additive → apply directly; restructuring/new skill → `references/skill-authoring.md` |
| Weekly review? | `/task-observer:review`; procedure in `references/weekly-review.md` |
| Division with learnings? | Skill improvement → here; project experience → learnings |
