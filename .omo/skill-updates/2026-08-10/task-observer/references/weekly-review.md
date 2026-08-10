# Comprehensive Review — manual trigger

Adapted from rebelytics/one-skill-to-rule-them-all (CC BY 4.0).

Cross-checks all OPEN observations against all skills, propagates
cross-cutting principles, and applies improvements that don't need user
input. Triggered by the user via `/task-observer:review`.

## Approval policy

**Interactive (user present):** always present observations grouped by skill
(number, title, one-sentence summary), flag judgment calls as "needs your
input", and wait for blanket or selective approval before applying.

**Escalate without applying** when: (1) the observation proposes a NEW skill
(naming/scope/type/licence need the user); (2) it removes or substantially
restructures existing content; (3) it self-flags uncertainty; (4) two
observations conflict.

## Steps

**Step 1 — archive and load.** Run archive first to move previously-resolved
entries out:
```bash
venv-python skills/task-observer/scripts/task_observer.py archive
```
Then read the observation log. Build the work queue from the structural
identifiers: enumerate all `### Observation N:` headers, classify each
entry's status. Treat a missing, blank, or non-ACTIONED/DECLINED status as
OPEN. **Reconciliation guard:** assert that header count equals classified
entry count. Also read all active cross-cutting principles. If no OPEN
observations and no outstanding principles: report "no open observations",
update the timestamp, and stop.

**Step 2 — inventory skills.** List all skills (system prompt
`<available_skills>` or the skills directory). Only user-owned custom skills
can be updated. Observations targeting a system skill (read-only) are routed
to a complementary user-owned `{system-skill}-extras` skill containing only
the delta.

**Step 3 — cross-check observations.** Evaluate every OPEN observation
against every skill — not just the skill named in its header; Principles
often generalise. Build skill → [relevant observations]. Present all and
await approval.

**Step 4 — cross-check principles.** Flag every skill that doesn't yet
comply with each active cross-cutting principle.

**Step 5 — apply.** For each skill with approved items, produce an updated
SKILL.md: integrate insights into the sections where they belong (never
append an observations list at the bottom); preserve structure, voice, and
attribution; place new rules where they logically live. Follow the editing
rules in `references/skill-authoring.md` (live file as base, staging, diff).

**Step 6 — mark ACTIONED.** For each applied observation:
```bash
venv-python skills/task-observer/scripts/task_observer.py mark \
  --number N --new-status ACTIONED --reason "Applied to [skill-name] (weekly review)"
```
The date is auto-filled by the script.

**Step 7 — timestamp.**
```bash
venv-python skills/task-observer/scripts/task_observer.py next-review
```

**Step 8 — deliver and summarise.** Stage updated skills (see Delivery
below), then present:

```
## Weekly Skill Review Complete — [date]

Updated skills ([N] observations, [N] principles applied):

**[skill-name]** — [1-sentence change summary]; observations #[N], #[N]

### Observations Actioned
[numbers and titles]

### Skipped (needs manual review)
[items with reasons]
```

## Constraints

- Don't modify observation entries beyond their status field.
- Don't create new skills in a review — note candidates for the user to
  action.
- Unsure how to integrate an observation → skip it and say so in the summary.
- Treat internal observations with the same rigour as open-source.

## Delivering updated skills

Stage each updated skill to `.omo/skill-updates/{date}/{skill-name}/` — the
FULL skill directory (SKILL.md plus references/, scripts/, assets/ where
present), never SKILL.md alone. Use the stage command:
```bash
venv-python skills/task-observer/scripts/task_observer.py stage <skill-path>
```

In opencode: report the staged path and a change summary in chat. Never write
to the live skill directly — staging-only is a deliberate safety property
(nothing goes live without the user's sign-off). For any skill with supporting
files, zip the staged directory into a `.skill` bundle and present the bundle.

**Pre-delivery gate** (run as the last step before presenting): (1) grep the
staged SKILL.md body for `references/`, `scripts/`, `assets/` paths and fail
if any referenced file is missing from the staged set; (2) for multi-file
skills, fail if the artefact is bare file links rather than the `.skill`
bundle. Sweep build artefacts before zipping.

**Keep-two rule:** for any skill, keep only the two most recent date
directories under `skill-updates/`; delete older ones.
