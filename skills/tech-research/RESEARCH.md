# Research — Phase 2 Reference

## Search — Iterative Strategy

### Round 1: Breadth search

| Parameter | Requirement |
|---|---|
| Min queries | 3 (different angles: official docs, community, opposing view) |
| Results per query | 5–8 |
| Source diversity | Official docs + blog + ≥1 contrarian/comparative perspective |
| Languages | English + Chinese |
| Fetch failure | Skip, record error in `collected.json > errors` |
| Time-sensitive topics | Add "2025", "latest" qualifiers |

After round 1: extract new keywords from results, check coverage against `scope.json`. Log in `scope.json > search_log`.

### Round 2+: Depth search (on-demand)

- Triggered only when coverage gaps exist
- 2-3 queries per round, based on new keywords / uncovered areas
- Re-check coverage after each round
- Stop when no gaps remain (or after reasonable effort)

### Search log format

Append to `scope.json > search_log` after each round:

```json
{
  "round": 1,
  "queries": ["query1", "query2", "query3"],
  "results_count": 15,
  "new_keywords": ["keyword1", "keyword2"],
  "coverage_after": {"covered": 5, "gaps": ["deployment"]}
}
```

## Collect Workflow

1. Call `exa_web_search_exa` (English + Chinese) — meet query count and angle diversity
2. Call `exa_web_fetch_exa` on each successful result
3. Save fetched content to `collected.json`. On fetch failure, record error and skip. Alternatively, use `research.py collect <sources.json>`.
4. Collect user-provided URLs/files if any

### collected.json Schema

```json
{
  "topic": "<research topic>",
  "sources": [
    {
      "url": "<page URL>",
      "title": "<page title>",
      "type": "<semantic label: guide | comparison | official_docs | blog | ...>",
      "source_type": "web | github | docs | user_file",
      "key_topics": ["<topic tag>"],
      "content": "<full fetched text — stored inline>",
      "quality": "high | medium | low | excluded",
      "published_date": "2025-03-01 | null",
      "duplicate_of": "url | null",
      "filter_note": ""
    }
  ],
  "errors": [
    { "url": "<failed URL>", "error": "<error message>", "stage": "search | fetch" }
  ]
}
```

> `type` = semantic label (what content covers) — for coverage diversity checks.
> `source_type` = where retrieved from — for report presentation.
> `quality`, `duplicate_of`, `filter_note` = filled during Filter step (next section).

## Filter — Dedup & Quality Screening

### Python side (deterministic)

Run after collection:
```bash
python ~/.agents/skills/tech-research/research.py filter
```

- URL normalization: lowercase scheme+host, remove trailing slash, sort query params, remove www prefix
- Marks duplicates with `duplicate_of` field
- Outputs report: total sources, unique count, duplicates marked

### Agent side (judgment-based)

After running `research.py filter`, apply these rules:

**Quality rating** for each source:
- `high`: Official docs, authoritative reports, GitHub official repos
- `medium`: Known blogs, high-voted community answers
- `low`: SEO content, unsigned articles, marketing material
- `excluded`: Clearly wrong / outdated / biased → mark but do not delete

**Content dedup**: Same topic across multiple articles → keep 1-2 most complete/authoritative. Mark others with `duplicate_of`.

**Timeliness**: Compare `published_date` with topic's timeliness needs. Flag outdated sources in `filter_note`.

## Coverage Matrix

After filtering, verify coverage against `scope.json > standardized`. **Only count sources where `quality != "excluded"` AND `duplicate_of == null`.**

| Goal type | Check |
|---|---|
| Exploratory | Each `focus_aspect` → ≥1 source (relaxed) |
| Panoramic understanding | Each `focus_aspect` → ≥1 source covers it |
| Tech selection | Each `candidate` → ≥2 sources; elimination criteria addressed |
| Feasibility assessment | Technology's architecture, limitations, real-world cases covered; constraints addressed |
| Competitive comparison | Each `candidate` → ≥1 source; each `comparison_dimension` → data exists |

Build matrix and save to `scope.json > coverage`. If gaps exist, run supplementary search. After reasonable effort, note insufficient coverage in report rather than forcing analysis.

## Analysis — 3-Step Structured Process

Read `scope.json` and `collected.json` (filtered sources only).

### Step 1: Claim Extraction

From each source, extract key claims:

```json
{
  "claims": [
    {
      "statement": "The claim in plain text",
      "sources": ["url1", "url2"],
      "type": "fact | opinion | prediction",
      "confidence": "high | medium | low",
      "contradicted_by": [],
      "section_id": "analysis | comparison | risks | ..."
    }
  ]
}
```

- `type`: `fact` (verifiable), `opinion` (subjective), `prediction` (future-oriented)
- `confidence`: initial rating based on source quality and claim type

### Step 2: Cross-Validation

For each claim:
- **Multi-source confirmation** (2+ sources agree) → upgrade to `high` confidence
- **Single source only** → keep at `medium`, add "needs-confirmation" note
- **Sources contradict** → record in `contradictions` with both viewpoints, set `contradicted_by` on the claim

### Step 3: Synthesize

- Organize validated claims into section structure
- Each section's overall confidence = lowest confidence among its claims
- Build `analysis.json` with claims + sections

### Template Selection

Depth depends on `time_constraint`:
- **hours** → "standard" template
- **days / weeks** → "deep" template

```python
time_constraint = scope["standardized"]["time_constraint"]
template = "standard" if time_constraint == "hours" else "deep"
```

### Per-Section Guide

| Section | Content | Goal-type adaptation |
|---|---|---|
| **summary** | One-sentence conclusion + 3-5 key findings table | Always |
| **overview** | What is this? Why now? Who for? 2-3 use cases | Always |
| **analysis** | Core technical substance | **Exploratory**: broad survey. **Panorama**: architecture, key concepts, trade-offs. **Selection**: per-candidate approach. **Feasibility**: maturity, complexity, integration points. **Comparison**: per-competitor strategy |
| **comparison** | Comparison matrix | **Exploratory**: optional, skip if no clear alternatives. **Panorama**: sub-areas comparison. **Selection**: weighted comparison with winner. **Feasibility**: vs status quo. **Comparison**: multi-dimensional matrix |
| **practice** | Practical usage guidance | **Selection**: getting started, integration, pitfalls. **Feasibility**: PoC steps. **Exploratory/Panorama/Comparison**: skip/minimize |
| **verification** | Demo/PoC results | Only if `time_constraint == "weeks"` AND runnable example exists. **Feasibility**: core section |
| **risks** | Limitations & risks | Adapts to goal type. **Exploratory**: general caveats |
| **conclusion** | Structured conclusion (see below) | **Exploratory**: can be "待定" with focus recommendations. **Selection**: winner recommendation. **Feasibility**: go/no-go. **Comparison**: summary per audience |
| **methodology** | Research approach | Deep template only |
| **timeline** | Chronological table | Deep template only |
| **decision_matrix** | Weighted scoring | Deep template only. Skip for exploratory and panoramic understanding |

> Skip sections marked "skip/minimize" or "Not applicable" for your goal_type, but keep `summary`, `overview`, `analysis`, `conclusion` always.

### Conclusion Section — Structured Format

The conclusion section MUST use structured format when `conclusion_data` is provided in `analysis.json`:

```json
{
  "conclusion_data": {
    "recommendation": "Option A | Go | Not Go | 待定",
    "reasoning": "Why this recommendation...",
    "confidence_assessments": [
      {"conclusion": "X is feasible", "confidence": "high", "evidence_strength": "3+ independent sources"}
    ],
    "action_items": ["Do PoC for X", "Investigate Y further"],
    "open_questions": ["Integration feasibility unclear"]
  }
}
```

When `conclusion_data` is present, the reporter renders:
- Recommendation + reasoning
- Confidence assessment table
- Action items (checkbox list)
- Open questions

When absent, falls back to plain section content (backward compatible).

### analysis.json Schema

**Required top-level fields**: `topic`, `depth`, `sections`.

```json
{
  "topic": "<research topic>",
  "depth": "standard | deep",
  "lang": "zh | en",
  "summary": "One-sentence conclusion + 3-5 key findings",
  "sources": [
    {
      "url": "<source URL>",
      "title": "<source title>",
      "source_type": "web | github | docs | user_file",
      "source_lang": "zh | en",
      "content": "<fetched or summarized content>",
      "confidence": "high | medium | low",
      "quality": "high | medium | low | excluded",
      "published_date": "2025-03-01 | null",
      "duplicate_of": "url | null",
      "filter_note": ""
    }
  ],
  "sections": [
    {
      "id": "<section ID — must match SECTION_IDS>",
      "title": "<display heading>",
      "content": "<Markdown body>",
      "confidence": "high | medium | low"
    }
  ],
  "claims": [
    {
      "statement": "claim text",
      "sources": ["url1", "url2"],
      "type": "fact | opinion | prediction",
      "confidence": "high | medium | low",
      "contradicted_by": [],
      "section_id": "analysis"
    }
  ],
  "conclusion_data": {
    "recommendation": "Go",
    "reasoning": "reasoning text",
    "confidence_assessments": [
      {"conclusion": "text", "confidence": "high", "evidence_strength": "3 sources"}
    ],
    "action_items": ["item1"],
    "open_questions": ["question1"]
  },
  "data_points": [
    { "key": "<metric name>", "value": "<metric value>", "source_url": "<URL>" }
  ],
  "comparisons": [
    { "dimension": "<comparison axis>", "values": {"OptionA": "...", "OptionB": "..."}, "winner": "OptionA | null" }
  ],
  "contradictions": ["<contradiction description>"],
  "timelines": [
    { "date": "<ISO date>", "event": "<description>", "source_url": "<URL>" }
  ]
}
```

#### Section IDs (must use these exact values)

**Standard template** (`depth: "standard"`):
`summary`, `overview`, `analysis`, `comparison`, `practice`, `verification`, `risks`, `conclusion`

**Deep template** (`depth: "deep"`):
All standard IDs + `methodology`, `timeline`, `decision_matrix`

> Skip sections not applicable to your goal_type (see Per-Section Guide above), but keep `summary`, `overview`, `analysis`, `conclusion` always.

Build `analysis.json` conforming to this schema. Validate with `research.py generate analysis.json --no-validate` to check structure before full generation.
