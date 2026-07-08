---
name: info-collector
description: >
  Structured research pipeline that produces a panoramic map with traceable sources —
  a starting point for deep research, not a citable authority.
  Invoked via /info-collector only.
---

# Info-Collector Skill

Structured research pipeline that produces a panoramic map with traceable sources — a starting point for deep research, not a citable authority.

## Usage

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

## Phase 0: Pre-check

1. Check whether `<project_root>/.workdir/` exists.
2. If it exists → ask the user: "A previous research `.workdir/` directory was detected. Delete it?"
   - User chooses delete → remove `.workdir/` → proceed to Phase 1
   - User chooses keep → **abort the pipeline** (user may manually inspect and re-run)
3. If it does not exist → proceed to Phase 1

**Rationale**: Residual files from a previous run (scope.json, collected.json) can silently pollute a new research session, causing gate misjudgments. This check ensures every info-collector session starts clean.

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

**You MUST execute searches by following `search_plan.json`**: Read it before searching. For each task in the plan, execute the corresponding search using that task's `site_queries` and `query_language`. After each search round, update task statuses to `completed` / `skipped` / `pending` in `search_plan.json`. When marking a task as `skipped`, you MUST provide a `skip_reason` field (e.g., `"cnki.net requires institutional login"`). Tasks skipped without `skip_reason` are treated as pending and will block the gate. Do NOT proceed to Step 2.3 until every direction has at least one `completed` task or is fully skipped with reasons.

**Search language rule**: Search English-language sources using English queries even if the topic is in Chinese. Use Chinese queries only for Chinese domains (cnki.net, zhihu.com, baidu.com, etc.).

**Tier 4 search strategy**: Tier 4 sources are not pre-configured in config.json. When deep research requires Tier 4 coverage, search broadly on Reddit, Hacker News, Dev.to, and personal blogs. All Tier 4 findings must use strong qualifier language in the report.

**Tier 1-2 fallback strategy**: When `site:` queries on Tier 1-2 domains (arxiv.org, huggingface.co, pypi.org, etc.) return few or no results, do NOT skip silently. Instead:
1. Broaden the query — remove restrictive terms, use synonyms or broader categories (e.g., "AI agent framework" instead of "agentic coding tool 2026")
2. Use platform-native search — fetch arXiv listing pages, Hugging Face model/dataset search, PyPI package search directly via URL
3. Accept partial matches — a Tier 2 source that covers a sub-topic is still valuable
4. If all Tier 1-2 searches for a direction fail, note this as a coverage gap when writing analysis

**Search strategy**: Follow the tier-based search order in `references/search-strategy.md`.

### Step 2.3: Full-content fetch (MANDATORY — do NOT skip)

For EVERY entry you plan to add to `collected.json`, you MUST fetch its full content using one of two paths:

**Path A — CLI autonomous fetch** (try first for all sources):
```bash
.venv\Scripts\python.exe -m scripts.cli fetch <url> [--tier <N>] [--no-playwright]
```
CLI will: rewrite URL → try tools in strategy order (skip exa, use requests+markdownify → Playwright) → clean → write source file → output JSON metadata. If `content_insufficient: true` in the result, try Path B. `--tier` is optional — CLI auto-infers from URL domain.

**Path B — Agent exa fetch + CLI post-processing** (for Tier 1-2 or when Path A returns insufficient content):
1. Call `exa_web_fetch_exa(url, maxCharacters=50000)` — **MUST set maxCharacters=50000 for Tier 1-2 sources**
2. Pipe the result to CLI:
```bash
echo '<json_or_text>' | .venv\Scripts\python.exe -m scripts.cli fetch <url> --from-stdin [--tier <N>]
```
Or pass plain text via stdin:
```bash
.venv\Scripts\python.exe -m scripts.cli fetch <url> --from-stdin [--tier <N>] < content.txt
```

**Decision rule**: Try Path A first. If output shows `content_insufficient: true`, switch to Path B.

**CLI JSON output** — use these fields to populate collected.json entry:
- `source_file` ← result.source_file
- `fetched_content` ← result.fetched_content
- `url_hash` ← result.url_hash (for reference)
- `source_tier` ← result.source_tier (auto-inferred, or override with --tier)
- Add `snippet`, `covered_directions` yourself (CLI cannot infer these)

**If fetch fails completely** (all tools exhausted, `fetch_failed: true`):
- Set `fetched_content` to `""`, `source_file` to `null`, add `"fetch_failed": true`
- Entries with `fetch_failed: true` are exempt from source fidelity checks but CANNOT be used as the sole source for claims with `precision: "exact"` or `evidence_type: "official_data"`

**Source fidelity gate** (replaces fetched_content_depth):

| Condition | Result |
|-----------|--------|
| >30% entries missing source files (not `fetch_failed`) | BLOCKER |
| >30% entries have source files < 2000 chars | BLOCKER (summary-only, not full article) |
| >50% entries are `fetch_failed` | WARN |
| Any entries with source files < 5000 chars | WARN (thin content) |

### Step 2.4: Collect

**Prerequisite**: The source file must already exist in `.workdir/sources/` before adding an entry to collected.json. Do NOT write collected.json entries first and then retroactively fetch source files.

Add each result to `<project_root>/.workdir/collected.json`:

```json
{
	"url": "...",
	"title": "...",
	"snippet": "...",
	"source_tier": 2,
	"fetched_content": "...",
	"source_file": "sources/abc123def456.md",
	"covered_directions": ["direction 1", "direction 2"],
	"fetch_failed": false,
	"vendor_affiliation": ""
}
```

**`covered_directions`** (optional, ADR 0017): Declares which search_directions this source covers. Use when title/snippet token overlap is below threshold. Constraints: subset of scope.json's search_directions, max 3 per entry, invalid values ignored with WARN.

**`fetch_failed`** (optional, default false): Set to `true` only when the URL could not be fetched after attempting. Exempts the entry from depth checks but imposes claim restrictions.

**`vendor_affiliation`** (optional): When the source belongs to or is published by a company with commercial interest in the topic, record the company name (e.g., `"Anthropic"`, `"Microsoft (GitHub)"`). The reporter will render this as `[vendor: X]` in the References section, providing automatic vendor bias disclosure.

### Step 2.5: Run gate

`python -m scripts.cli proceed --from search --to analysis`

Checks:
- topic_coverage (BLOCKER) — search directions covered
- tier_coverage (WARN) — source tier diversity
- per_direction_min_sources (WARN) — enough sources per direction
- min_sources (WARN) — total source count
- source_fidelity (BLOCKER if >30% entries missing source files) — original text files exist in `.workdir/sources/`
- source_fidelity depth (BLOCKER if >30% entries have source files < 2000 chars; WARN if any entries < 5000 chars) — source files must contain full article content, not search-result highlights/summaries
- search_plan_compliance (BLOCKER) — every search_direction must have at least one task with genuine collected results (verified by gate reverse-computation from collected.json). Tasks may be marked `skipped` with a mandatory `skip_reason` field; skipped tasks without `skip_reason` are treated as pending and block the gate. Tier-level coverage remains WARN.

If BLOCKER → fix the issue (fetch missing content, search more) before proceeding.

## Phase 3: Report

### 3a: Build analysis.json

Synthesize findings from `<project_root>/.workdir/collected.json` into `<project_root>/.workdir/analysis.json`.

**Writing guide**: See `references/writing-guide.md` for content quality requirements, source traceability rules, tier-aware citations, precision rules, methodology section requirements, recommendation structure, anti-patterns, depth strategy rules, deep-dive anchor requirements, synthesis guard, and false depth prohibition.

**Subagent delegation**: See `references/subagent-template.md` for the exact prompt template, JSON schema, and assembly instructions.

#### Step 1: Plan sections

Read collected.json and scope.json. Decide the sections (id, title) based on goal_type requirements (see section_coverage check in gateway.py). For each section, determine the **depth strategy** from the implicit mapping table (see writing-guide.md "Depth Strategy" section). For overview/deep_dive strategy sections in panoramic/exploratory goal_types, identify **≥ 2 deep-dive topics** per section — key findings worth arguing with 3+ sources, selected by tension/impact/mechanism criteria. For each deep-dive topic, list **source_hints** (URLs from collected.json likely relevant to that topic). Write the section plan as `{id, title, deep_dive_topics: [{topic, source_hints}], depth_strategy}` but do NOT write content yet.

#### Step 2: Write each section's content independently (parallel)

Delegate an independent agent call per section. Follow the template in `references/subagent-template.md`.

**Subagent delegation is mandatory** when analysis.json has ≥ 2 sections. The `analysis→review` gate will BLOCK if no `analysis_section_*.json` files exist in `.workdir/`. Each subagent must write its output to `.workdir/analysis_section_{id}.json`. This prevents the orchestrator from writing all sections itself, which degrades quality via token compression and loss of context isolation.

#### Step 2.5: Gate pre-check

Before running `proceed --from analysis --to review`, verify analysis.json against
the gate rules checklist below. Fix any violations, then run the gate.
Do NOT use the gate as a spell-checker — get it right the first time.

The checklist is the AI-readable version of gate rules. Gate code is the single source of truth;
the checklist ensures you know the rules before the gate enforces them.

| # | Rule | Check method | On failure |
|---|------|-------------|------------|
| 1 | `evidence_type` ∈ {`independent_benchmark`, `official_data`} → must have `source_metadata` with non-empty `test_conditions` string | iterate claims | fix and re-check |
| 2 | `precision: exact` → `evidence_type` must be `official_data` or `independent_benchmark` | iterate claims | fix and re-check |
| 3 | Every claim's `source_urls` URLs (normalized) must exist in collected.json | URL set comparison | fix and re-check |
| 4 | Every section must have `id` and `title` | iterate sections | fix and re-check |
| 5 | `panoramic_understanding` / `exploratory` must have `overview` section | section id check | fix and re-check |
| 6 | `{{ref:URL}}` markers' URLs (normalized) must exist in collected.json | iterate ref markers | fix and re-check |
| 7 | Quantitative `goal_type` must have `methodology` section | section id check | fix and re-check |
| 8 | Every claim's `source_urls` URLs must appear as `{{ref:URL}}` in the same section's content | iterate claims + content | fix and re-check |
| 9 | If analysis.json has ≥ 2 sections, `.workdir/analysis_section_*.json` files must exist | glob `.workdir/analysis_section_*.json` | delegate sections to subagents and re-check |

#### Step 3: Assemble analysis.json

Merge all sections into a single analysis.json. JSON merge only — never rewrite section content.

#### Step 3.5: Run concreteness check

`python -m scripts.cli gateway`

- If BLOCKER → fix analysis.json and re-run gateway
- If clean → proceed to 3b

### Gate: proceed --from analysis --to review

Run: `python -m scripts.cli proceed --from analysis --to review`

- Runs all gateway checks but filters to **analysis-phase only** (excludes `claim_verified` and `claim_source_relevance`). Checks schema validation + analysis-phase BLOCKERs including url_traceability, section_coverage, content_concreteness, claim_metadata, precision_inflation, source_metadata, metric_type_homogeneity, claim_dedup, subagent_delegation, etc. (ADR 0025). Also runs `source_verification_check` (WARN only, never BLOCKER) which computes the three-level source_verification classification and writes `verified` on each claim deterministically.
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

If the subagent fails to produce review_report.md (file missing or empty):
1. Ask the user to choose one of:
   a. **Retry subagent review** (max 2 retries; each failure re-asks the user)
   b. **Degrade to inline review** — perform review yourself (same workload as subagent:
      read scope.json, collected.json, analysis.json; run semantic checks for
      context_twist, cross_section_inconsistency, vendor_bias_undisclosed, tier_misattribution;
      write findings). Create `.workdir/review_fallback.log` with:
      `<timestamp> | subagent failed (attempt N/2) | error: <error detail> | user chose: inline review`
      Use `--review-status degraded` when generating the report.

`degraded` means review independence was lost (same LLM wrote and reviewed).
There is no `unreviewed` option — review is mandatory, minimum level is degraded.

The review subagent performs semantic checks only — context twist, cross-section inconsistency,
vendor bias undisclosed, and tier misattribution. The `verified` field on claims is set
deterministically by `source_verification_check()` code, not by the review subagent.

For each issue found, the subagent writes findings in review_report.md following
the format in `references/REVIEW_PROMPT.md`.

If user says **no** to independent review → degrade to inline review (same agent performs review itself, same workload as subagent). Use `--review-status degraded`.

### 3c: User confirmation + Final report

Show the review report (or degradation notice) to user and ask:

- User confirms approval (adapt language to user) → Run: `python -m scripts.cli proceed --from review --to final`

  The review gate is advisory-only. It runs `run_all()` but never blocks — `claim_verified`
  is now WARN level and `claim_source_relevance` has been replaced by `source_verification_check`
  in the analysis phase. The `verified` field is set deterministically by
  `source_verification_check()` code, not by the review subagent.

  Then generate final report:

  ```
  python -m scripts.cli report --review-status <passed|degraded> --search-rounds N --source-count N [--output DIR]
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

Run report checks on the generated `.md` file. Only BLOCKER-level failures need fixing; WARN-level failures are advisory and do not block. (ADR 0026)

**BLOCKER** (must fix):

| ID | Check | Description |
|----|-------|-------------|
| F1 | Dangling references | In-text `[N]` has no matching definition in References section |
| F2 | Orphaned definitions | References section has `[N]` not cited in body text |
| 9 | Front matter format | YAML front matter is malformed or missing required fields |

**WARN** (advisory, does not block):

| ID | Check | Description |
|----|-------|-------------|
| A | References visibility | References section consists only of `[N]: URL` hidden definitions with no visible list |
| D | Table delimiter alignment | Table delimiter row `|` count differs from header row |
| 10 | Heading level skip | Heading level jumps (e.g., `##` directly to `####`) |
| 12 | Duplicate headings | Same-level headings with identical text appear more than once |
| 13 | Unclosed code block | Fenced code block markers (` ``` `) appear an odd number of times |
| 15 | Empty section | Section heading exists but has no content |
| 16 | Overlong line | Single line exceeds 500 characters |

If any check fails → fix the `.md` file → re-run `proceed --from review --to final`.

Pipeline terminates at `post_final`. To clean up intermediate files manually, run `python -m scripts.cli clean`.

## CLI Commands Reference

See `references/cli-reference.md` for full command details and quality values.

## Important Rules

1. Always run `proceed` commands. Never skip a gate.
2. You MUST ask the user about review. Do not assume.
3. Do not reuse old scope.json for a different topic.
