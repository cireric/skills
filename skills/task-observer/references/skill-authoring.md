# Skill Authoring — taxonomy, licensing, confidentiality, editing rules

Adapted from rebelytics/one-skill-to-rule-them-all (CC BY 4.0).

Load this before creating any skill or making substantial changes to one.

## Taxonomy in full

**Open-source skills** are client-agnostic and methodology-driven.
Recognise one: the methodology works across clients and contexts; no
proprietary information is needed; other practitioners would find it
valuable. Required elements: identifies itself as open-source; author
attribution block; a licence statement; tool-agnostic language; built-in
enforcement (see Pre-Flight Principle). Default to open-source when a skill
could go either way — strip specifics and generalise.

**Internal skills** contain user/client/project specifics, personal
preferences, or context only the user has. They identify themselves as
internal, need no attribution or licence, and can be shorter and less
formal.

## The Pre-Flight Principle

Rules documented in a skill are not reliably followed during creative flow.
Every skill with explicit rules needs a verification step where the agent
re-reads the rules and checks its output against them before delivery. When
creating or improving any skill ask: "Does it have rules? Does it have a
mechanism to enforce them?" If not, add one.

**Embedded commands are pre-flight items too — execute before you ship.**
Any command embedded in a skill must be executed once against real data, with
its output inspected for plausibility, before the skill file is saved. An
unverified snippet is among the highest-risk lines in a skill: it ships bugs
that no re-read can catch.

## Lean Content

A skill should contain only content that changes the agent's behaviour at
execution time. Move changelogs, credits beyond the author block, long
backstories, and maintainer notes to supporting docs. Do NOT cut examples,
anti-patterns, or worked scenarios — bare rules get violated more than rules
with context. Test: would removing it change behaviour? Keep per-session
rules in the skill body and episodic material in reference files loaded on
demand — a skill loaded every session is fixed overhead and should be audited
like one.

## Licensing

Include a licence statement in the preamble. Default: **CC BY 4.0**
(prose/methodology skills; share and adapt with credit). For code-heavy
skills, consider MIT or Apache 2.0.

## Author Attribution Template

```markdown
**Created by [Author Name] / [website or contact link]**

[1-2 sentence description of what the skill does and its provenance.]

**Licence:** This skill is released under [LICENCE NAME].

**Feedback & Support:** [contact link or repo URL]
```

## Confidentiality layers

The open-source/internal boundary is a confidentiality boundary; enforce it
in layers so any one catches what others miss:

1. **Observation-level stripping** — open-source observations carry a fully
   generalised Principle.
2. **Pre-creation review** — before drafting an open-source skill, scan all
   source material for client names, URLs, domains, internal terminology;
   replace with generic equivalents.
3. **Post-draft sweep** — a separate re-read focused only on leakage: proper
   nouns besides the author, domains/URLs/project identifiers, vertical
   details that narrow the client.
4. **Structural principle** — when in doubt, remove. Slightly more generic
   beats slightly leaky.
5. **Cross-product re-identifiability sweep** — the final pass before any
   public release. Individually-sanitised examples can combine to identify a
   client. List every example and its fields; ask whether a reader with the
   author's public client list could map them.

## Editing skills — always start from the live file

1. The live file is the authoritative source. Do not edit skill files in
   place, in any environment — staging-only is what keeps the review safe.
2. Always base edits on a fresh read of the live file — never a workspace
   copy, prior draft, or memory.
3. Before overwriting any staged/workspace copy, diff it against the live
   file; if they differ, rebase your edits on the live version.
4. Stage every update to `.omo/skill-updates/{date}/{skill-name}/` — the
   FULL skill directory (SKILL.md plus references/, scripts/, assets/ where
   present), never SKILL.md alone. Use the stage command:
   ```bash
   venv-python skills/task-observer/scripts/task_observer.py stage <skill-path>
   ```
   In opencode: present the staged path and a change summary in chat.
   Staging-only applies in every environment — it's the review loop's safety
   property, not a filesystem constraint.
5. Match process rigour to the change: complex/open-source/uncertain design
   → use a structured skill-creation process; internal skills with
   requirements already established in conversation → write directly,
   flagging substantial changes for review.

## Verifying relocations and restructures

When content is relocated verbatim (splits into core + references, merges,
restructures), verify with a two-tier check:

1. Enumerate every added/moved line via `diff` of the old base vs the new
   base. Exact-match each non-empty line against the restructured file set.
2. For misses, substance-check via a distinctive mid-line substring before
   concluding loss.
3. Inventory the original's enforcement mechanisms as an explicit checklist —
   compression preferentially destroys enforcement machinery because it reads
   as redundancy.

## New skills

Determine type early: open-source → strip and generalise; internal → include
specifics freely; uncertain → default open-source and let the user add
internal detail afterwards.

## Principle Propagation

When an observation's Principle applies to skills in general, log it with
`Skill: All skills` and surface it; if the user approves, add it to
`.omo/cross-cutting-principles.md`. That file is a mandatory checklist
during any skill creation or regeneration.

```markdown
# Cross-Cutting Principles

Principles that apply to all skills. Read as a mandatory checklist during
any skill creation or regeneration.

---

## Active Principles

### 1. [Principle title]
**Added:** [date]
**Applies to:** [all skills | all open-source skills | all skills with rules]
**Requirement:** [what it requires]
**Propagation:** [immediate | opportunistic]
**Status:** [active]
```
