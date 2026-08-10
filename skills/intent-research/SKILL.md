---
name: intent-research
description: >
  Invoke via /intent-research only. Structured research pipeline with source
  authority tiering, deterministic verification, and intent-driven convergence
  (decision_questions). Use when research informs a decision.
---

# Intent-Research Skill

## Goal

Produce research reports aligned to user intent, with source authority discrimination and deterministic verification. The criterion: **every decision_question is answered with traceable, tier-labeled sources.**

## Three Pillars

1. **Source Authority Tiering** — 4 tiers, 10 goal_type routes, CJK sources. Default tier by URL domain matching; agent may override with `tier_override_reason`.
2. **Deterministic Verification** — `source_verification` computed by Python code (number matching + indirect rules), never by LLM. Three levels: `source_confirmed`, `source_absent` (†), `source_indirect` (‡).
3. **Intent-Driven Convergence** — `decision_questions` (3-5) declared in Phase 1. Search stops when DQs have required source coverage. Analysis is complete when every DQ has a directly answering claim.

## Execution Model

- **Main agent** (sync): Phase 0 + Phase 1, then spawns background task
- **Background agent** (async): Phase 2-5, returns structured summary
- Main agent does not participate in Phase 2-5
- Background agent self-resolves gate failures; returns error only if unresolvable
- No cancellation mechanism — user cancels by ending the session

## Workflow

### Phase 0: Environment Check (main agent, sync)

`.workdir/` at project root (where `AGENTS.md` lives).

- `.workdir/` does not exist → create it, proceed to Phase 1
- `.workdir/` exists → ask user:
  1. **Clear and restart** — delete entire `.workdir/`, recreate, proceed to Phase 1
  2. **Cancel** — exit without changes

No "Continue" option — partial `.workdir/` state from crashed/aborted runs is unreliable.

### Phase 1: Scope (main agent, sync)

Structured interview — the only phase requiring user interaction.

**4 core questions** (user must answer):

| # | Question | Field | Notes |
|---|----------|-------|-------|
| 1 | Goal type | `goal_type` | 10 options with descriptions; agent recommends one based on topic |
| 2 | Depth | `depth` | quick / standard / deep |
| 3 | Search directions | `search_directions` | Select from suggestions or custom |
| 4 | Decision questions | `decision_questions` | Free input; 3-5 recommended |

**Goal type options** — agent analyzes the user's topic and recommends one:

| # | goal_type | Description |
|---|-----------|-------------|
| 1 | tech_selection | 帮我选技术方案（A vs B vs C） |
| 2 | competitive_comparison | 帮我对比多个方案的优劣 |
| 3 | feasibility_assessment | 这个方案能不能做 |
| 4 | fact_check | 这个说法对不对 |
| 5 | background_check | 这个人/公司/项目怎么样 |
| 6 | market_analysis | 市场规模/趋势/格局 |
| 7 | academic_research | 学术前沿/研究现状 |
| 8 | panoramic_understanding | 系统性了解一个领域 |
| 9 | exploratory | 快速了解一个领域大概有什么 |
| 10 | other | 以上都不匹配 |

**Auto-inferred** (agent infers and confirms with user):

| Field | Inference rule |
|-------|---------------|
| `audience` | From topic + goal_type (e.g., "tech_selection" → engineer/CTO) |
| `report_language` | CJK topic → `"zh"`, otherwise `"en"`; user may override |
| `english_title` | Required when topic contains non-ASCII characters |
| Search language strategy | CJK topic → bilingual search (match source `language` field in config.json) |

**Decision questions are the quality anchor**:
- Every decision_question must have a directly answering claim in the final report
- Source sufficiency checks against them: does each have Tier 1-2 sources?
- Recommend 3-5, covering the core value of the research
- Prompt: "What decisions will this research help you make?"

Write `.workdir/scope.json`:

```json
{
  "topic": "...",
  "english_title": "...",
  "goal_type": "...",
  "scope_description": "...",
  "depth": "...",
  "audience": "...",
  "report_language": "...",
  "search_directions": ["..."],
  "decision_questions": [
    {"id": "dq1", "question": "...", "context": "..."}
  ]
}
```

Gate: `venv-python -m scripts.cli scope-check`

### Phase 2-5: Background Task

Main agent confirms: *"Research task started. Report will be saved to `reports/<english_title>.md`"*

### Phase 2: Search (background agent, async)

**Breadth first, then depth — converge via decision_questions.**

**Round 1 — Breadth scan**:
- Cover all `search_directions`; each direction ≥1 source
- Follow goal_type route for search order
- Goal: map the information landscape

**Round 2 — Depth driven by decision_questions** (standard/deep only):
- For each decision_question: which sources can answer it? Gaps → targeted search
- Discover new entities → follow-up search
- Converge when: every decision_question has ≥1 Tier 1-2 source that can answer it

**Round 3 (deep only) — Targeted gap fill**:
- Remaining gaps from Round 2
- Use config.json sources as repair toolbook (not pre-search plan)
- Converge when: every decision_question has ≥2 Tier 1-2 sources + tension coverage

**Depth-driven search budget**:

| depth | Max rounds | Expected sources | DQ coverage requirement |
|-------|-----------|-----------------|------------------------|
| quick | 1 | 5-10 | Each DQ ≥1 source |
| standard | 2 | 10-20 | Each DQ ≥1 Tier 1-2 source |
| deep | 3 | 20-40 | Each DQ ≥2 Tier 1-2 sources + tension coverage |

Max rounds are hard limits. Early convergence is allowed.

**Tier availability caveat**: some domains (e.g., fast-moving open-source ecosystems, emerging topics) have no Tier 1 academic/standards sources at all. Tier 2 official documentation/repositories are then the highest reachable authority. Interpret the DQ coverage requirement against the *highest tier that actually exists* for the topic — don't inflate search budget chasing a tier that doesn't exist, and never lower source quality to fill a count. Note the absence of Tier 1 sources in the analysis (a brief statement of why, e.g. "topic is too recent for academic coverage"), so readers can calibrate evidence strength.

**Convergence failure**: After reaching the round limit, mark unanswerable questions. Explain in analysis why evidence is insufficient. Never lower source quality to fill the count.

**Requirements**:
- Every `collected.json` entry must have a `direction` field (one of `scope.search_directions` or `"other"`)
- `source_tier` is auto-assigned by URL domain matching against config.json; if domain not in config, default Tier 3; agent may override with `tier_override_reason`
- Source files must be written through the fetch tool — never write source content directly
- Prefer primary sources; match search language to source language
- Exa is the primary fetch path: `exa_web_fetch_exa` → `venv-python -m scripts.cli fetch --from-stdin`

Gate: `venv-python -m scripts.cli scope-check`

### Phase 3: Analysis (background agent, async)

**Decision_questions as skeleton, tensions as substance.**

Follow `references/writing-guide.md` for writing standards.

**Value extraction — four steps**:

1. **Skeleton**: Each decision_question maps to ≥1 section. Section's job: answer that question. Tightly related questions may share a section. At most 1 background/overview section.

2. **Three-layer filter** — for each candidate piece of information:
   - *Relevance*: related to any decision_question? No → skip
   - *Incrementality*: does the reader already know this, or is it better stated elsewhere? No increment → skip
   - *Actionability*: can it change the reader's judgment or action? No → demote to background, not a core claim

3. **Tension-driven insight**: conflicting findings across sources are where value lives. Source A says "X works", Source B says "X fails for Y" → the insight is not "X sometimes works" (trivial) but "X's effect depends on condition Z" (incremental).

4. **Concrete over abstract**: every number needs context (whose experiment? what conditions?); no vague qualifiers without specifics.

**analysis.json schema**:

```json
{
  "topic": "...",
  "goal_type": "...",
  "sections": [
    {
      "id": "...",
      "title": "...",
      "content": "Body text with {{ref:URL}} source markers",
      "key_insights": [{"summary": "...", "sources": ["url"]}],
      "tensions": [{"summary": "...", "sources": ["url"]}],
      "claims": [
        {
          "summary": "...",
          "sources": ["url"],
          "evidence_type": "official_data|independent_benchmark|third_party_estimate|qualitative_trend|expert_opinion",
          "precision": "exact|range|qualitative"
        }
      ],
      "decision_questions_answered": ["dq1"],
      "order": 0
    }
  ]
}
```

Field notes:
- `decision_questions_answered` per section — explicit traceability from section to DQs it answers
- `tier_override_reason` on claims — required if agent overrides the default tier for a source

Gate: `venv-python -m scripts.cli scope-check`

### Verify (automatic, between Phase 3 and Phase 4)

```bash
venv-python -m scripts.cli verify
```

Reads analysis.json + collected.json + sources/ directory. For each claim:
1. Read source file from `sources/` directory
2. Run number matching
3. Apply indirect source rules
4. Write `source_verification` field back to analysis.json
5. Print verification summary

**Mandatory** — not optional. Results are data annotations, not gate BLOCKERs.

**Indirect source rules** (any one triggers `source_indirect` ‡):

1. **Low-tier authoritative claim**: source_tier ≥ 3 AND evidence_type is `official_data` or `third_party_estimate`
2. **Vendor self-test**: source_type is `vendor_benchmark`/`vendor_survey`/`vendor_blog` AND precision is `exact`/`range` AND source venue is non-authoritative (tier ≥ 3)
3. **Citation entity mismatch**: claim text mentions entity X but source URL hosts entity Y

Priority rule: `indirect` > `confirmed`/`absent`. Even if a number IS found in source text, an indirect classification means the source itself is not primary.

### Phase 4: Self-Edit Checklist (background agent, async)

Prompt-level checklist — not a formal review phase. After writing analysis, check against this list and fix directly:

1. **Context twist** — generalized a narrow finding?
2. **Precision inflation** — presented a secondhand number as exact?
3. **Vendor bias** — presented vendor self-reported data without noting the source?
4. **Tier misattribution** — presented a Tier 3 finding with Tier 1 authority language?
5. **Verification gaps** — verify output shows †/‡ claims; check if any need supplementary sources
6. **Marker-driven source dropping** — dropped a Tier 3/4 source merely to avoid a ‡ marker? ‡ is a data annotation about source provenance, not a defect; keep informative low-tier sources and phrase their claims with the appropriate tier qualifier (per writing-guide source_tier-aware language). Tensions often live in Tier 3/4 sources — dropping them to clean up markers weakens the report.

This is self-edit (author's checklist), not a quality gate.

### Phase 5: Report (background agent, async)

```bash
venv-python -m scripts.cli report
```

Auto-rendered Markdown with:
- Source references with tier labels (★★★☆ Tier 1, etc.)
- †/‡ verification markers from verify step
- Verification summary table (confirmed / indirect / absent counts)
- Decision questions answered summary
- YAML front matter with `verification_required: true`

Output: `reports/<english_title>.md`

`.workdir/` is preserved after report generation for audit trail. User may manually delete it.

### Return Summary (background → main agent)

On completion:

```json
{
  "status": "completed|failed",
  "report_path": "reports/<english_title>.md",
  "summary": {
    "topic": "...",
    "goal_type": "...",
    "source_count": 0,
    "tier1_count": 0,
    "tier2_count": 0,
    "decision_questions": [
      {"id": "dq1", "question": "...", "answered": true, "key_finding": "..."}
    ],
    "key_insights": ["..."],
    "tensions": ["..."],
    "verification": {
      "confirmed": 0,
      "indirect": 0,
      "absent": 0
    }
  },
  "issues": []
}
```

## CLI Commands

All commands use the venv Python interpreter, abbreviated `venv-python` below.

**Convention:** `venv-python` means the venv Python for the current platform — Windows: `.venv\Scripts\python.exe` · Linux/macOS: `.venv/bin/python` (mirrors AGENTS.md). Substitute your platform's path when running commands literally.

**Environment requirement**: the `scripts` package lives under the skill directory (`skills/intent-research/scripts`), not in the project root. Commands must be run with the skill directory on `PYTHONPATH`; otherwise `No module named scripts.cli`:

```powershell
# PowerShell (Windows)
$env:PYTHONPATH = "skills\intent-research"; venv-python -m scripts.cli <command>
```

```bash
# bash (Linux/macOS)
PYTHONPATH=skills/intent-research venv-python -m scripts.cli <command>
```

Run from the project root (where `AGENTS.md` lives) so `.workdir/` and `reports/` resolve correctly.

### `scope-check`

5 checks (3 BLOCKER + 2 WARN):

| Check | Level | Condition |
|-------|-------|-----------|
| scope_schema | BLOCKER | topic non-empty, goal_type valid, CJK topic requires english_title |
| precision_rules | BLOCKER | No `expert_opinion`+`exact` etc. |
| ref_marker_validity | BLOCKER | All `{{ref:URL}}` in collected.json |
| source_sufficiency | WARN | Each DQ has Tier 1-2 sources |
| direction_coverage | WARN | Each search_direction has ≥1 source |

### `fetch --from-stdin` / `fetch --from-file`

Reads a JSON array, writes source files and updates collected.json.

**Preferred: `--from-file`** — write the JSON array to a local UTF-8 file (e.g., `.workdir/fetch-batch.json`), then pass the path. Avoids shell-pipe encoding issues on Windows:

```bash
venv-python -m scripts.cli fetch --from-file .workdir/fetch-batch.json
```

**`--from-stdin`** (bash only — PowerShell 5.1 pipes can corrupt UTF-8 content):

```bash
echo '[{"url": "...", "content": "...", "tier": 1, "direction": "tech_arch"}]' | venv-python -m scripts.cli fetch --from-stdin
```

JSON item fields: `url` (required), `content`, `title`, `tier`, `direction`, `snippet`, `tier_override_reason`.

Tier auto-assignment: if `tier` not provided, CLI matches URL domain against config.json. Unknown domains default to Tier 3.

### `verify`

Deterministic source verification. Automatically invoked between Phase 3 and Phase 4.

### `report`

Generates final report. Output: `reports/<english_title>.md`

Tier definitions: see CONTEXT.md `source_tier`. Goal type routes: see config.json `routes`. Routes are advisory — agent may deviate when justified.
