---
name: info-collector
description: >
  Collect, organize, and summarize structured information from the web and
  local sources. Use when user asks to gather information on a topic, compile
  facts, aggregate references, or build a knowledge base. Triggers: 收集一下,
  帮我查查, 整理资料, 搜集, 汇总, 调研一下, find information, gather data,
  look up, compile, collect facts, research topic, 帮我整理, 查资料.
---

# Info-Collector Workflow

Three-phase pipeline with iterative search, quality filtering, and review loops. Detailed references in [SCOPE.md](./SCOPE.md) and [RESEARCH.md](./RESEARCH.md).

---

## Quick Start

User: "调研一下某个技术主题"
→ Ask 3 quick questions (goal/audience/time). After answers + confirmation → proceed.

---

## Phase 1: Scope

1. **Config** — check `config.json`. First-time setup asks output_dir + lang.
2. **Pre-fill** — list existing reports (silent, format awareness).
3. **Scope interview** — ask 3 questions together (goal, audience, time budget) + branch questions by goal type. See [SCOPE.md](./SCOPE.md).
   - New goal type: `exploratory` — for "just want to understand" motivations.
4. **User confirmation** — show scope summary, ask user to confirm or modify.
5. Save `scope.json`. Validate with `research.py validate-scope scope.json`.

**Scope revision**: during Phase 2/3, if new constraints emerge, update `scope.json` and append to `revisions` array. Notify user of changes.

---

## Phase 2: Research

1. **Search (iterative)** — `exa_web_search_exa` (≥3 queries round 1, then by coverage gaps). Log each round in `scope.json > search_log`. See [RESEARCH.md](./RESEARCH.md).
2. **Collect** — `exa_web_fetch_exa` → save to `collected.json`. Content stored inline. Or use `research.py collect`.
3. **Filter** — run `research.py filter` for URL dedup. Then agent-side: quality rating (high/medium/low/excluded), content dedup, timeliness. Update source fields: `quality`, `duplicate_of`, `filter_note`.
4. **Coverage check** — validate against `scope.json` (only non-excluded, non-duplicate sources). Run supplementary search for gaps.
5. **Analyze (3-step)**:
   - Step 1: Extract claims → `analysis.json > claims` (statement, sources, type, confidence)
   - Step 2: Cross-validate → multi-source = high, single-source = medium, contradictions → `contradictions`
   - Step 3: Synthesize → organize into sections, each section gets min-claim confidence

Full detail in [RESEARCH.md](./RESEARCH.md).

---

## Phase 3: Report

1. **Draft** — run with `--draft`:

   ```bash
   python ~/.agents/skills/tech-research/research.py generate analysis.json --draft
   ```

   Then subagent review (input: report + collected.json + scope.json). Tags: [LOGIC]/[DATA] → block, [MISS]/[CLARITY] → auto-fix with collected.json. Max 10 rounds.

2. **User Review** — show draft summary + key conclusions to user. Max 2 rounds. Feedback paths:
   - Small fix → edit analysis.json → regenerate
   - Need more sources → back to Phase 2
   - Scope change → back to Phase 1 (record revision)

3. **Finalize** — regenerate without `--draft`. Evidence traceability check (each claim → source_url, AI-inferred labeled, gaps acknowledged). If fails → supplementary search (max 1 round).

4. **Cleanup** — ask user: "保留中间文件？". If no → `research.py clean`. If yes → files remain for future reference.

---

## Cardinal Rules

- **Auto-fix must cite `collected.json`** as evidence — never hallucinate
- **1% uncertainty = mark in report** — if unsure, label "needs-confirmation"
- **Never modify `config.json`** during research — it's pre-configured
- **Content stored inline** in `collected.json` — no external `content/` directory
- **Coverage checks use filtered sources only** — exclude quality=excluded and duplicate_of≠null

---

## CLI Reference

| Command                                   | Purpose                                          |
| ----------------------------------------- | ------------------------------------------------ |
| `generate <analysis.json>`                | Generate Markdown report                         |
| `generate <analysis.json> --draft`        | Generate draft report (status: draft in front matter) |
| `validate-scope <scope.json>`             | Validate scope.json schema                       |
| `collect <sources.json> [--topic T]`      | Add sources to collected.json                    |
| `filter`                                  | URL-deduplicate sources in collected.json        |
| `init-config [--output-dir D] [--lang L]` | Initialize config.json                           |
| `show-config`                             | Display current config                           |
| `clean`                                   | Remove workfiles (scope/collected/analysis.json) |
