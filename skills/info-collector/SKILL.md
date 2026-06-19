---
name: info-collector
description: >
  Structured research pipeline: scope → search → analyze → review → report.
  Triggers on 调研, research, 技术选型, tech selection, 竞品分析, competitive analysis,
  市场分析, market research, 可行性评估, feasibility assessment, 事实核查, fact-check.
---

# Info-Collector Skill

Structured research pipeline that collects, organizes, and synthesizes information from web sources into a quality-gated report.

## Usage

- **Trigger phrases**: 调研, research, 技术选型, tech selection, 竞品分析, competitive analysis, 市场分析, market research, 可行性评估, feasibility assessment, 事实核查, fact-check
- **Slash command**: `/info-collector`
- **Output**: Markdown report in `<project_root>/<config.json:output_dir>` with YAML front matter

## Path Convention

All relative paths are relative to the **project root** (where `scripts/cli.py` is run from):

**CLI invocation**: Set `PYTHONPATH` to the skill directory and run from within it:
```
# From skills/info-collector/
PYTHONPATH=. python -m scripts.cli <command>
# On Windows PowerShell:
$env:PYTHONPATH = "D:\...\skills\info-collector"; python -m scripts.cli <command>
```

| Reference                                 | Actual location                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| `<project_root>/.workdir/`                | `<cwd>/.workdir/` — e.g. `D:\Project\.workdir\`                          |
| `<project_root>/<config.json:output_dir>` | `<cwd>/<output_dir>` — configured in `skills/info-collector/config.json` |

## Setup Wizard

When `skills/info-collector/config.json` does not exist (first run), guide the user through setup:

1. **output_dir**: Where reports should be saved. Default: `./reports/`
2. **default_report_language**: Preferred report language (e.g., zh, en). Default: `zh`
3. **default_depth**: Typical research depth (quick/standard/deep). Default: `standard`
4. **Source customization**: Show the 4-tier source list. Ask if user wants to add/remove sources per tier.

After collecting answers, write `skills/info-collector/config.json` and confirm in the user's language.

**Re-running the wizard**: User can request setup wizard at any time by saying "重新配置" or "run setup wizard". This overwrites the existing `skills/info-collector/config.json`.

## Phase 1: Scope

1. **Interview** the user to determine:
   - Read `config.json` from `skills/info-collector/config.json` and verify `output_dir` is set; if missing, warn the user and ask for an output directory path
   - `topic` — what to research
   - `english_title` — **required when topic contains non-ASCII characters** (e.g., CJK). Used as the report filename base. Optional for pure-ASCII topics.
   - `goal_type` — which of the 10 types (or "other" for custom)
   - `depth` — quick | standard | deep
   - `audience` — CTO | engineer | researcher | general
   - `scope_description` — natural language summary
   - `search_directions` — 1+ specific directions to search. **Prefer English keywords** because CJK tokens match poorly against English source snippets. Chinese directions are allowed but may trigger topic_coverage WARN instead of BLOCKER.
   - `report_language` — (optional) override `default_report_language` from config

2. Write `scope.json` to `<project_root>/.workdir/scope.json`.

3. **Run gate**: `python -m scripts.cli proceed --from scope --to search`
   - If exit code != 0 → show errors, fix scope.json, retry.

## Phase 2: Search-Collect-Filter

### Step 2.1: Get source recommendations

`python -m scripts.cli source <goal_type>`

### Step 2.2: Search (rounds 1-3)

Use `exa_web_search_exa` for discovery. Use `site:` queries from recommended sources. Aim for ~3 search rounds (soft limit).

**You MUST execute searches by following `search_plan.json`**: Read it before searching. For each task in the plan, execute the corresponding search using that task's `site_queries` and `query_language`. After each search round, update task statuses to `completed` / `skipped` / `pending` in `search_plan.json`. Do NOT proceed to Step 2.3 until every direction has at least one `completed` task.

**Search language rule**: Search English-language sources using English queries even if the topic is in Chinese. Use Chinese queries only for Chinese domains (cnki.net, zhihu.com, baidu.com, etc.).

**Tier 4 search strategy**: Tier 4 sources are not pre-configured in config.json. When deep research requires Tier 4 coverage, search broadly on Reddit, Hacker News, Dev.to, and personal blogs. All Tier 4 findings must use strong qualifier language in the report.

**Search strategy**: Follow the tier-based search order in `references/search-strategy.md`.

### Step 2.3: Full-content fetch (MANDATORY — do NOT skip)

For EVERY entry you plan to add to `collected.json`, you MUST fetch its full content using `webfetch` (or `exa_web_fetch_exa` if available). Search-result highlights are NOT sufficient — they are summaries, not source material.

**Minimum fetched_content lengths (BLOCKER if not met)**:

| Source tier | Minimum fetched_content | Rationale |
|-------------|------------------------|-----------|
| Tier 1 (academic) | 1000 chars | Academic papers contain methodology, results, limitations that highlights cannot capture |
| Tier 2 (docs) | 800 chars | Official docs have API details, configuration, examples |
| Tier 3 (industry) | 600 chars | Blog posts and reports have context, nuance, caveats |
| Tier 4 (community) | 400 chars | Forum posts are shorter but must still be fetched, not summarized from highlights |

If a URL cannot be fetched (paywall, 403, timeout), you MAY still add the entry but MUST set `fetched_content` to the empty string `""` and add `"fetch_failed": true` to the entry. Entries with `fetch_failed: true` are exempt from depth checks but CANNOT be used as the sole source for claims with `precision: "exact"` or `evidence_type: "official_data"`.

### Step 2.4: Collect

Add each result to `<project_root>/.workdir/collected.json`:

```json
{
	"url": "...",
	"title": "...",
	"snippet": "...",
	"source_tier": 2,
	"fetched_content": "...",
	"covered_directions": ["direction 1", "direction 2"],
	"fetch_failed": false
}
```

**`covered_directions`** (optional, ADR 0017): Declares which search_directions this source covers. Use when title/snippet token overlap is below threshold. Constraints: subset of scope.json's search_directions, max 3 per entry, invalid values ignored with WARN.

**`fetch_failed`** (optional, default false): Set to `true` only when the URL could not be fetched after attempting. Exempts the entry from depth checks but imposes claim restrictions.

### Step 2.5: Run gate

`python -m scripts.cli proceed --from search --to analysis`

Checks:
- topic_coverage (BLOCKER) — search directions covered
- tier_coverage (WARN) — source tier diversity
- per_direction_min_sources (WARN) — enough sources per direction
- min_sources (WARN) — total source count
- fetched_content_depth (BLOCKER if >30% entries are stubs) — full content was actually fetched
- search_plan_compliance (WARN) — plan tasks were executed and updated

If BLOCKER → fix the issue (fetch missing content, search more) before proceeding.

## Phase 3: Report

### 3a: Build analysis.json

Synthesize findings from `<project_root>/.workdir/collected.json` into `<project_root>/.workdir/analysis.json`.

**Writing guide**: See `references/writing-guide.md` for content quality requirements, source traceability rules, tier-aware citations, precision rules, methodology section requirements, recommendation structure, and anti-patterns.

**Subagent delegation**: See `references/subagent-template.md` for the exact prompt template, JSON schema, and assembly instructions.

#### Step 1: Plan sections

Read collected.json and scope.json. Decide the sections (id, title) based on goal_type requirements (see section_coverage check in gateway.py). Write the section plan but do NOT write content yet.

#### Step 2: Write each section's content independently (parallel)

Delegate an independent agent call per section. Follow the template in `references/subagent-template.md`.

#### Step 3: Assemble analysis.json

Merge all sections into a single analysis.json. JSON merge only — never rewrite section content.

#### Step 3.5: Run concreteness check

`python -m scripts.cli gateway`

- If BLOCKER → fix analysis.json and re-run gateway
- If clean → proceed to 3b

### Gate: proceed --from analysis --to review

Run: `python -m scripts.cli proceed --from analysis --to review`

- Validates analysis.json has topic, goal_type, non-empty sections, and url_traceability.
- **YOU MUST ASK THE USER** whether to launch an independent review (adapt language to user).

### 3b: Review

If user says **yes**:

1. Read `references/REVIEW_PROMPT.md` for the review prompt
2. Launch a subagent with that prompt
3. Subagent reads scope.json, collected.json, analysis.json
4. Subagent writes `<project_root>/.workdir/review_report.md` — **include the explicit `.workdir/` output path in the subagent prompt**
5. Fix any issues found in analysis.json
6. **After fixing analysis.json, re-run the gate**: `python -m scripts.cli proceed --from review --to review`
   - This self-loop re-validates analysis.json without requiring a phase reset.
   - If the gate still refuses, use `python -m scripts.cli reset --phase review` then `python -m scripts.cli proceed --from analysis --to review`.

If user says **no** → quality will be set to `unreviewed` at finalization.

### 3c: User confirmation + Final report

Show the review report (or degradation notice) to user and ask:

- User confirms approval (adapt language to user) → Run: `python -m scripts.cli proceed --from review --to final`

  This runs gateway.py with 15 checks. BLOCKER fails = stop and fix. WARN = noted but does not block.

  Then generate final report:

  ```
  python -m scripts.cli report --quality <passed|degraded|unreviewed> --search-rounds N --source-count N [--output DIR]
  ```

  Report filename: `{english_title_or_topic}.md`. If file already exists, appends date suffix: `{name}_{YYYY-MM-DD}.md`.

- User expresses dissatisfaction → Start a new research from Phase 1 with a new scope.

### 3d: Report rendering verification

After the report file is generated in 3c, verify it renders correctly before cleanup. This step catches problems that are invisible in source code but obvious in rendered output (e.g., references section not showing, citations not clickable).

#### Step 1: AI rendering sanity check

Read the generated `.md` file and verify the following items against CommonMark/GFM standards:

| ID | Check | Pass criteria |
|----|-------|---------------|
| B | In-text citations are clickable | Citation syntax matches an allowed format (see below) |
| C | Reference URLs are clickable | URLs in the References section use Markdown link syntax |
| G | No trailing artifacts | File ends cleanly — no duplicate headings, JSON fragments, or orphaned definition lines |
| 11 | Internal anchors resolve | Any `(#anchor)` in-text links match an actual anchor in the References section |

**Allowed citation syntax** (CommonMark/GFM compatible):
- `[&#91;N&#93;](#refs)` — HTML entity brackets (widest compatibility)
- `[\[N\]](#refs)` — Escaped bracket syntax

**Disallowed citation syntax:**
- `[N]` — Plain text, not a link
- `[N][]` — Relies on hidden definition; most renderers do not render a clickable link or jump target

If any check fails → directly edit the `.md` file to fix → re-run this step.

#### Step 2: Gateway check

Run: `python -m scripts.cli proceed --from final --to cleanup`

This runs 10 automated checks on the report file (all WARN level):

| ID | Check | Description |
|----|-------|-------------|
| F1 | Dangling references | In-text `[N]` has no matching definition in References section |
| F2 | Orphaned definitions | References section has `[N]` not cited in body text |
| A | References visibility | References section consists only of `[N]: URL` hidden definitions with no visible list |
| D | Table delimiter alignment | Table delimiter row `|` count differs from header row |
| 9 | Front matter format | YAML front matter is malformed or missing required fields |
| 10 | Heading level skip | Heading level jumps (e.g., `##` directly to `####`) |
| 12 | Duplicate headings | Same-level headings with identical text appear more than once |
| 13 | Unclosed code block | Fenced code block markers (` ``` `) appear an odd number of times |
| 15 | Empty section | Section heading exists but has no content |
| 16 | Overlong line | Single line exceeds 500 characters |

If any check fails → fix the `.md` file → re-run `proceed --from final --to cleanup`.

## Phase 4: Cleanup

1. Run: `python -m scripts.cli proceed --from final --to cleanup`
2. Ask user whether to clean up intermediate files (adapt language to user).
   - Yes -> `python scripts/cli.py clean`
   - No -> `<project_root>/.workdir/` remains

## CLI Commands Reference

See `references/cli-reference.md` for full command details and quality values.

## Important Rules

1. Always run `proceed` commands. Never skip a gate.
2. You MUST ask the user about review. Do not assume.
3. Do not reuse old scope.json for a different topic.
