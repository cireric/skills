# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

This repo uses a multi-context structure. Start by checking for `CONTEXT-MAP.md` at the repo root:

1. **If `CONTEXT-MAP.md` exists** — read it to find which contexts exist and where their `CONTEXT.md` files live. Then read the `CONTEXT.md` relevant to the topic you're working on.
2. **If only a root `CONTEXT.md` exists** — single context, read it directly.
3. **If neither exists** — proceed silently. Don't flag their absence; don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

For ADRs: first determine which skill/context you're working in, then look for `docs/adr/` or `skills/<skill>/docs/adr/` in that context. In multi-context repos, check the root `docs/adr/` for system-wide decisions and the context-specific `docs/adr/` for context-scoped decisions.

## File structure

Multi-context repo (this repo):

```
/
├── CONTEXT-MAP.md                       ← points to each context's CONTEXT.md
├── docs/
│   └── adr/                             ← system-wide decisions (if any)
│   └── agents/                          ← cross-skill configuration
└── skills/
    ├── info-collector/
    │   ├── CONTEXT.md                   ← info-collector domain glossary
    │   └── docs/adr/                    ← info-collector decisions
    ├── reading-grill/
    │   └── (no CONTEXT.md — pure prompt skill)
    └── book-grill/
        └── (no CONTEXT.md — pure prompt skill)
```

Single-context repo (for reference):

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
