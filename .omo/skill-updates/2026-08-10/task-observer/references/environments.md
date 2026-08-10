# Environments, Activation Setup, and Known Limitations

Adapted from rebelytics/one-skill-to-rule-them-all (CC BY 4.0).

Load this for setup questions or compaction/resume behavior.

## Recommended activation setup

Description-level matching alone can miss invocation when the agent is focused
on the task. Pair the skill with a configuration-level instruction in AGENTS.md:

```
At the start of any task-oriented session — any interaction where you will
use tools and produce deliverables — invoke the task-observer skill before
beginning work. This ensures skill improvement opportunities are captured
throughout the session.

When loading any skill, check the observation log for OPEN observations
tagged to that skill. Apply their insights to the current work, even if
the skill file hasn't been updated yet.
```

**Config detection (once per session):** check the project's AGENTS.md for a
task-observer activation instruction — suggest adding it if absent. Keep the
suggestion to a sentence or two.

**Anti-pattern:** don't chain activation through another skill — load
task-observer independently from AGENTS.md; a broken chain silences all
observation activity.

**Activation tiers (weakest → strongest):**

1. **Description matching** — the skill's `description` in the system prompt.
   Weakest: the agent may skip invocation on short or simple-looking requests
   even when tools are involved.

2. **AGENTS.md instruction** — a structural trigger read at session start.
   Better than description alone, but still probabilistic: the agent can
   read the instruction and still choose not to invoke the skill on requests
   it classifies as non-task-oriented.

3. **opencode hook** (`hooks.yaml`, session.created event) — injects a
   reminder prompt at session start. The only tier with structural
   enforcement, but still a model decision: the prompt increases the
   probability of activation, it does not guarantee it.

No tier is a guarantee — choosing to invoke a skill remains a model
decision. Users should pick a tier knowingly rather than assuming the
middle one is sufficient.

## Compaction behavior

When context compacts mid-task, the AGENTS.md structural trigger re-invokes
this skill on the resumed session automatically. Observations before and after
compaction append to the same log with continuous numbering.

## Known limitations (opencode)

- **Activation is probabilistic:** AGENTS.md instructions and description
  matching are both probabilistic — the agent may skip loading task-observer
  on short or simple-looking requests. This is a platform limitation, not a
  skill defect. If consistent activation is critical, consider adding an
  opencode hook (see below).

- **No scheduled review:** opencode does not have a built-in task scheduler.
  Weekly review must be triggered manually via `/task-observer:review`. A
  calendar reminder is the recommended workaround.

- **No read-only mount for skills:** Unlike Cowork, opencode skill files are
  writable. The "never edit in place" rule is enforced by staging discipline
  and the Python script's `stage` command (cp + diff), not by filesystem
  protection. See `references/skill-authoring.md` for the staging protocol.

- **No presentation tool:** There is no `present_files` equivalent. Updated
  skills are delivered by reporting the staged path and a change summary in
  chat. The user reviews and installs manually.

## Optional: opencode hooks for activation

If you find AGENTS.md instructions are frequently skipped, you can add an
opencode hook as a second layer. Create `.opencode/hooks.yaml` (or
`~/.config/opencode/hooks.yaml` for global) with:

```yaml
hooks:
  - id: task-observer-reminder
    event: session.created
    actions:
      - bash: "echo '[task-observer] Remember to load task-observer skill for this session.'"
```

This outputs a reminder when a new session starts. It does not force the
agent to load the skill — that remains a model decision — but it increases
the likelihood of activation. This is optional; the AGENTS.md instruction
is sufficient for most users.

## User-facing documentation

- Project repo: the skill's own directory `skills/task-observer/`
- Original upstream: https://github.com/rebelytics/one-skill-to-rule-them-all
- Upstream USER-GUIDE: https://github.com/rebelytics/one-skill-to-rule-them-all/blob/main/USER-GUIDE.md
