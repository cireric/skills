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

**You MUST execute searches by following `search_plan.json`**: Read it before searching. For each task in the plan, execute the corresponding search using that task's `site_queries` and `query_language`. After each search round, update task statuses to `completed` / `skipped` / `pending` in `search_plan.json`. Do NOT proceed to Step 2.3 until every direction has at least one `completed` task.

**Search language rule**: Search English-language sources using English queries even if the topic is in Chinese. Use Chinese queries only for Chinese domains (cnki.net, zhihu.com, baidu.com, etc.).

**Tier 4 search strategy**: Tier 4 sources are not pre-configured in config.json. When deep research requires Tier 4 coverage, search broadly on Reddit, Hacker News, Dev.to, and personal blogs. All Tier 4 findings must use strong qualifier language in the report.

**Tier 1-2 fallback strategy**: When `site:` queries on Tier 1-2 domains (arxiv.org, huggingface.co, pypi.org, etc.) return few or no results, do NOT skip silently. Instead:
1. Broaden the query — remove restrictive terms, use synonyms or broader categories (e.g., "AI agent framework" instead of "agentic coding tool 2026")
2. Use platform-native search — fetch arXiv listing pages, Hugging Face model/dataset search, PyPI package search directly via URL
3. Accept partial matches — a Tier 2 source that covers a sub-topic is still valuable
4. If all Tier 1-2 searches for a direction fail, note this as a coverage gap when writing analysis

**Search strategy**: Follow the tier-based search order in `references/search-strategy.md`.

### Step 2.3: Full-content fetch (MANDATORY — do NOT skip)

For EVERY entry you plan to add to `collected.json`, you MUST fetch its full content using the fetch strategy system. Search-result highlights are NOT sufficient — they are summaries, not source material.

**Fetch strategy resolution** (priority: code strategy > config url_rewrite > DefaultStrategy):

1. If the source has a `fetch_strategy` field in config.json (e.g., `"arxiv"`, `"github"`), the fetch router loads the corresponding `fetch_strategies/<name>.py` strategy
2. If the source has `url_rewrite` rules in config.json, the generic regex rewrite engine applies them
3. Otherwise, DefaultStrategy is used (no URL rewrite, tools=`["webfetch"]`)

Each strategy provides: `rewrite_url(url) → str` and `get_tools() → list[str]` (ordered tool fallback chain).

**Adaptive retry by Tier**:
- Tier 1-2: retry each tool 2 times before falling back to next tool
- Tier 3-4: retry each tool 1 time before falling back to next tool
- Global timeout: 60 seconds per URL across all tools

**Source file storage**:

After fetching, save the original text to `.workdir/sources/{url_hash}.md` where `url_hash` is the first 12 characters of SHA-256 of the normalized URL. Set the `source_file` field in the collected.json entry to `"sources/{url_hash}.md"`.

The `fetched_content` field is reduced to a 200-character index (first 200 chars of the fetched text). It is no longer a gate check target.

**Source fidelity gate** (replaces fetched_content_depth):

| Condition | Result |
|-----------|--------|
| >30% entries missing source files (not `fetch_failed`) | BLOCKER |
| >50% entries are `fetch_failed` | WARN |

If a URL cannot be fetched (paywall, 403, timeout), you MAY still add the entry but MUST set `fetched_content` to `""`, `source_file` to `null`, and add `"fetch_failed": true`. Entries with `fetch_failed: true` are exempt from source fidelity checks but CANNOT be used as the sole source for claims with `precision: "exact"` or `evidence_type: "official_data"`.

### Step 2.4: Collect

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
- search_plan_compliance (WARN) — plan tasks were executed and updated

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

#### Step 3: Assemble analysis.json

Merge all sections into a single analysis.json. JSON merge only — never rewrite section content.

#### Step 3.5: Run concreteness check

`python -m scripts.cli gateway`

- If BLOCKER → fix analysis.json and re-run gateway
- If clean → proceed to 3b

### Gate: proceed --from analysis --to review

Run: `python -m scripts.cli proceed --from analysis --to review`

- Runs all gateway checks but filters to **analysis-phase only** (excludes `claim_verified` and `claim_source_relevance`). Checks schema validation + 14 analysis-phase BLOCKERs including url_traceability, section_coverage, content_concreteness, claim_metadata, precision_inflation, source_metadata, metric_type_homogeneity, claim_dedup, etc. (ADR 0025). Also runs `source_verification_check` (WARN only, never BLOCKER) which computes the three-level source_verification classification and writes `verified` on each claim deterministically.
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
   c. **Skip review** — use `--review-status unreviewed`

`degraded` means review independence was lost (same LLM wrote and reviewed).
`unreviewed` means no review was performed at all.

The review subagent performs semantic checks only — context twist, cross-section inconsistency,
vendor bias undisclosed, and tier misattribution. The `verified` field on claims is set
deterministically by `source_verification_check()` code, not by the review subagent.

For each issue found, the subagent writes findings in review_report.md following
the format in `references/REVIEW_PROMPT.md`.

If user says **no** → review_status will be set to `unreviewed` at finalization.

### 3c: User confirmation + Final report

Show the review report (or degradation notice) to user and ask:

- User confirms approval (adapt language to user) → Run: `python -m scripts.cli proceed --from review --to final`

  The review gate is advisory-only. It runs `run_all()` but never blocks — `claim_verified`
  is now WARN level and `claim_source_relevance` has been replaced by `source_verification_check`
  in the analysis phase. The `verified` field is set deterministically by
  `source_verification_check()` code, not by the review subagent.

  Then generate final report:

  ```
  python -m scripts.cli report --review-status <passed|degraded|unreviewed> --search-rounds N --source-count N [--output DIR]
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
