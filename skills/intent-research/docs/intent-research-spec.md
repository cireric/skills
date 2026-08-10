# Intent-Research Skill Specification

> **Status**: Draft (post-grilling revision)
> **Date**: 2026-08-06
> **Supersedes**: info-collector (deprecated, ADR 0065), info-collector-plus (evolves into intent-research)
> **Related**: [research-writing-guide.md](research-writing-guide.md), [research-tooling-options.md](research-tooling-options.md)

## 1. Problem Statement

Existing research skills fall into two camps:

| Camp | Representative | What it does | What it doesn't do |
|------|---------------|--------------|-------------------|
| Saturation | deep-research, ulw-research | Fan out, cover exhaustively, vote/verify claims | Align to user intent; distinguish source authority; deterministic verification |
| Lightweight | Matt Pocock research skill | Quick investigation, primary sources, zero code | Structure; tier routing; precision control; CJK sources |

Three gaps none of them address:

1. **Intent alignment** — "搜了很多但没回答我的问题" is the most common failure mode. No skill uses the user's decision questions as the convergence criterion.
2. **Source authority discrimination** — No skill routes search order by goal type or prevents precision inflation (vendor self-test data presented as exact fact).
3. **Deterministic verification** — deep-research uses LLM voting; ulw-research uses LLM claim graphs. Both are AI-verifying-AI. No skill uses code-level number matching + tier rules.

## 2. Design Principles

Sourced from info-collector's 64 ADRs, especially ADR 0028, 0029, 0042, 0065:

| # | Principle | Source | Implication |
|---|-----------|--------|-------------|
| 1 | Positioning = implementation | ADR 0065 L1 | "Research starting point" means no quality-gated report infrastructure |
| 2 | No AI-verifying-AI | ADR 0028, ADR 0065 L2 | All quality checks are deterministic code, not LLM judgment |
| 3 | Leverage in prompt, not gate | ADR 0065 L3 | writing-guide pre-guidance > post-hoc gate checking |
| 4 | Exit condition defined | ADR 0065 L4 | decision_questions with Tier 1-2 sources = done |
| 5 | Gates ensure structure only | ADR 0029 | BLOCKERs only for data integrity, not content quality |
| 6 | Allow deletion | ADR 0065 L6 | Unneeded checks are not built; built-and-useless ones are deleted |

## 3. Three Pillars

### 3.1 Source Authority Tiering

Four tiers of information sources:

| Tier | Definition | Examples | Precision default |
|------|-----------|----------|-------------------|
| 1 | Academic / Standards | arXiv, CNKI, Wanfang, CQVIP, PubMed, Semantic Scholar | exact |
| 2 | Documentation / Open Source | GitHub, Wikipedia, HuggingFace, MDN, PyPI, Gitee | exact |
| 3 | Industry / Expert Blogs | Medium, IEEE Spectrum, 36氪, 机器之心, InfoQ 中文 | range, qualitative |
| 4 | Community / UGC | Reddit, HN, Zhihu, Weibo, V2EX, 掘金 | qualitative only |

**Tier override**: Default tier is assigned by URL domain matching against config.json. Agent may override with `tier_override_reason` field. ‡ marker in report is not removed by override — readers still see the source's default tier. Override is a property of the claim-source pair, not the URL alone.

**Goal type routing** — search order determined by research objective:

| goal_type | Route | Rationale |
|-----------|-------|-----------|
| tech_selection | [2,3,4,1] | Docs → industry → community → academic |
| competitive_comparison | [2,1,3,4] | Docs → academic benchmarks → industry → community |
| feasibility_assessment | [2,1,3] | Docs → academic → industry |
| fact_check | [1,2,4] | Authoritative first |
| background_check | [3,2,1,4] | Industry → docs → academic → community |
| market_analysis | [3,4,1,2] | Industry → community (earliest signals) → academic → docs |
| academic_research | [1]+[2] | Academic primary, docs supplementary |
| panoramic_understanding | [2,1,3,4] | Docs → academic → industry → community |
| exploratory | [4,3,2] | Community signals → industry → docs |
| other | auto | Agent infers from decision_questions; fallback [2,3,1,4] |

Routes are advisory — agent may deviate when justified. The route changes search order, not gate enforcement.

**`other` goal_type**: Route is `"auto"`. Agent infers search order from decision_questions and topic context. If no clear signal, default to [2,3,1,4] (docs → industry → academic → community) — Tier 2 is the safest starting point, authoritative yet accessible.

**CJK sources** — 9 CJK-specific sources across all tiers:

- Tier 1: CNKI, Wanfang, CQVIP, CBOA
- Tier 2: Wikipedia (zh), Gitee
- Tier 3: 36氪, InfoQ 中文, 机器之心, 少数派
- Tier 4: Zhihu, Weibo, V2EX, 掘金, 豆瓣

Exa (`exa_web_fetch_exa` / `exa_web_search_exa`) is the primary fetch path for CJK sources due to anti-bot walls on autonomous fetch.

### 3.2 Deterministic Verification

**`source_verification`** — three-level classification computed by Python code, never by LLM:

| Level | Meaning | Report marker |
|-------|---------|---------------|
| source_confirmed | Number/claim found in fetched source text | (none) |
| source_absent | Number/claim not found in fetched source text | † |
| source_indirect | Source is indirect (see rules below) | ‡ |

**Indirect source rules** (any one triggers `source_indirect`):

1. **Low-tier authoritative claim**: Source tier ≥ 3 AND evidence_type is `official_data` or `third_party_estimate`. Low-tier sources claiming high-authority data are inherently suspect.
2. **Vendor self-test**: source_type is `vendor_benchmark`/`vendor_survey`/`vendor_blog` AND precision is `exact`/`range` AND source venue is non-authoritative (tier ≥ 3). An authoritative venue (e.g., arXiv paper) mislabeled as `vendor_benchmark` is NOT flipped.
3. **Citation entity mismatch**: Claim text mentions entity X but source URL hosts entity Y. E.g., "OpenAI reports" but URL is a third-party blog.

**Priority rule** (ADR 0028): `indirect` > `confirmed`/`absent`. Even if a number IS found in source text, an indirect classification means the source itself is not primary.

**Number matching algorithm**:

```python
_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:,\d{3})*|\d+)"
    r"(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?"
    r"(?!\w)"
)

def number_found_in_source(claim_text: str, source_text: str) -> str:
    claim_nums = normalize_numbers(claim_text)
    if not claim_nums:
        return "source_confirmed"  # qualitative claim, no number to verify
    source_nums = normalize_numbers(source_text)
    if claim_nums & source_nums:
        return "source_confirmed"
    return "source_absent"
```

Supports: plain numbers, percentages, units (ms, MB, GB), ranges (45-48%), billions ($1.5B).

**Precision rules** (hard constraint, enforced by BLOCKER gate):

- `evidence_type` in {`third_party_estimate`, `qualitative_trend`, `expert_opinion`} → `precision` MUST NOT be `exact`
- `precision: exact` → `evidence_type` MUST be `official_data` or `independent_benchmark`

This is a logical consistency check, not a quality judgment — `expert_opinion` cannot be `exact` by definition.

### 3.3 Intent-Driven Convergence

**`decision_questions`** — 3-5 questions the research must answer, declared by the user in Phase 1.

Convergence operates at three levels:

| Level | Criterion | Effect |
|-------|-----------|--------|
| Search | Every decision_question has ≥1 Tier 1-2 source that can answer it | Search can stop |
| Analysis | Every decision_question has ≥1 claim that directly answers it | Analysis is complete |
| Report | Every decision_question maps to ≥1 section | Report is complete |

**Depth-driven search budget**:

| depth | Max rounds | Expected sources | DQ coverage requirement |
|-------|-----------|-----------------|------------------------|
| quick | 1 | 5-10 | Each DQ ≥1 source |
| standard | 2 | 10-20 | Each DQ ≥1 Tier 1-2 source |
| deep | 3 | 20-40 | Each DQ ≥2 Tier 1-2 sources + tension coverage |

Max rounds are hard limits — agent may not exceed them. Early convergence is allowed: if all DQs meet coverage requirements before the round limit, search stops.

**Convergence failure**: After reaching the round limit, mark unanswerable questions. Explain in analysis why evidence is insufficient. Never lower source quality to fill the count.

**Report skeleton**: Each decision_question maps to ≥1 section. Tightly related questions may share a section. At most 1 background/overview section. This prevents the common failure of "comprehensive but unfocused" reports.

**Comparison with alternative convergence mechanisms**:

| Mechanism | Used by | Driven by | Failure mode |
|-----------|---------|-----------|--------------|
| Claim voting | deep-research | Information completeness | Covers a lot, answers nothing specific |
| EXPAND lead exhaustion | ulw-research | Information saturation | Expensive, no guarantee of intent alignment |
| decision_questions | intent-research | User intent | May miss tangential discoveries — mitigated by `"other"` direction and free search |

## 4. Architecture

```
┌──────────────────────────────────────────────────┐
│  SKILL.md (Agent behavioral instructions)         │
│  - Phase 0-1: Main agent, sync                    │
│  - Phase 2-5: Background agent, async              │
│  - Search strategy: goal_type route + DQs          │
│  - Analysis strategy: 3-layer filter + tension     │
│  - Self-edit checklist (prompt-level)               │
│  - Writing standards: writing-guide (prompt-level) │
├──────────────────────────────────────────────────┤
│  CLI (Python, deterministic infrastructure)         │
│  - scope-check: 7 checks (3 BLOCKER + 2 WARN)    │
│  - fetch --from-stdin: Source file writing          │
│  - verify: Deterministic source_verification        │
│  - report: Markdown rendering + tier + †/‡ marks   │
├──────────────────────────────────────────────────┤
│  config.json (Declarative, no code changes needed) │
│  - sources: 4 Tier definitions + CJK sources       │
│  - routes: 10 goal_type routes                      │
│  - tier_rules: Indirect downgrade rules             │
└──────────────────────────────────────────────────┘
```

## 5. Workflow

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

**Auto-inferred** (no dedicated interview step; agent infers and confirms with user):

| Field | Inference rule | Confirmation |
|-------|---------------|-------------|
| `audience` | From topic + goal_type (e.g., "tech_selection" → engineer/CTO) | Agent asks: "这份报告是给谁看的？我推测是[推断结果]" |
| `report_language` | CJK topic → `"zh"`, otherwise `"en"` | User may override |
| `english_title` | Required when topic contains non-ASCII characters | Auto-triggered |
| Search language strategy | CJK topic → bilingual search (match source `language` field in config.json: `"zh"` sources use CJK keywords, others use English keywords) | No confirmation needed (agent behavior) |

**Goal type selection** — agent analyzes the user's topic and recommends one goal_type with rationale. Present the 10 options with descriptions:

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

User confirms or selects a different one.

**Decision questions are the quality anchor**:

- Every decision_question must have a directly answering claim in the final report
- Source sufficiency checks against them: does each have Tier 1-2 sources?
- Recommend 3–5, covering the core value of the research
- Phase 1 interview should prompt: "What decisions will this research help you make?"

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

CJK topics require `english_title`.

Gate: `python -m scripts.cli scope-check`

### Phase 2–5: Background Task

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
- Use config.json sources as repair toolbook (not pre-search plan, per ADR 0042)
- Converge when: every decision_question has ≥2 Tier 1-2 sources + tension coverage

**Early convergence**: If all DQs meet coverage requirements before the round limit, search stops.

**Convergence failure**: After reaching the round limit, mark unanswerable questions; explain in analysis why evidence is insufficient. Never lower source quality to fill the count.

**Requirements**:

- Every `collected.json` entry must have a `direction` field (one of `scope.search_directions` or `"other"`)
- `source_tier` is auto-assigned by URL domain matching against config.json; if domain not in config, default Tier 3; agent may override with `tier_override_reason`
- Source files must be written through the fetch tool — never write source content directly
- Prefer primary sources; match search language to source language
- Exa is the primary fetch path: `exa_web_fetch_exa` → `python -m scripts.cli fetch --from-stdin`

Gate: `python -m scripts.cli scope-check`

### Phase 3: Analysis (background agent, async)

**Decision_questions as skeleton, tensions as substance.**

Follow [research-writing-guide.md](research-writing-guide.md) for writing standards.

**Value extraction — four steps**:

1. **Skeleton**: Each decision_question maps to ≥1 section. Section's job: answer that question. Tightly related questions may share a section. At most 1 background/overview section.

2. **Three-layer filter** — for each candidate piece of information:
   - *Relevance*: related to any decision_question? No → skip
   - *Incrementality*: does the reader already know this, or is it better stated elsewhere? No increment → skip
   - *Actionability*: can it change the reader's judgment or action? No → demote to background, not a core claim

3. **Tension-driven insight**: conflicting findings across sources are where value lives. Source A says "X works", Source B says "X fails for Y" → the insight is not "X sometimes works" (trivial) but "X's effect depends on condition Z" (incremental). Tension sources: inter-source disagreement, conditional variation within a source, gap between common belief and evidence.

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
- `decision_questions_answered` per section — explicit traceability from section to DQs it answers. This is a section-level annotation (which DQs this section answers). It does not need to align with `direction` (a source-level annotation of which search direction produced the source).
- `confidence` field removed — not needed; reliability is expressed by `evidence_type` + `precision` + `source_verification`.
- `tier_override_reason` on claims — if agent overrides the default tier for a source, this field is required.

Gate: `python -m scripts.cli scope-check`

Verify: `python -m scripts.cli verify` (automatically invoked between Phase 3 and Phase 4)

### Verify (automatic, between Phase 3 and Phase 4)

```bash
python -m scripts.cli verify
```

Reads analysis.json + collected.json + sources/ directory. For each claim:

1. Read source file from `sources/` directory
2. Run number matching
3. Apply indirect source rules
4. Write `source_verification` field back to analysis.json
5. Print verification summary

This is not optional — it is the core IP of the skill. Results are written back as data annotations (not gate BLOCKERs), consistent with ADR 0028's INFO-level design.

### Phase 4: Self-Edit Checklist (background agent, async)

Prompt-level checklist — not a formal review phase. After writing analysis, the agent checks against this list and fixes directly:

1. **Context twist** — generalized a narrow finding?
2. **Precision inflation** — presented a secondhand number as exact?
3. **Vendor bias** — presented vendor self-reported data without noting the source?
4. **Tier misattribution** — presented a Tier 3 finding with Tier 1 authority language?
5. **Verification gaps** — verify output shows †/‡ claims; check if any need supplementary sources

This is self-edit (author's checklist), not a quality gate. It belongs to "leverage in prompt, not gate" (principle 3).

### Phase 5: Report (background agent, async)

```bash
python -m scripts.cli report
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

## 6. CLI Commands

### `scope-check`

Checks scope.json, collected.json, and analysis.json compliance:

| Check | Level | Condition |
|-------|-------|-----------|
| scope_topic | BLOCKER | topic non-empty |
| scope_goal_type | BLOCKER | goal_type in valid set |
| scope_english_title | BLOCKER | CJK topic requires english_title |
| precision_rules | BLOCKER | No `expert_opinion`+`exact` etc. |
| ref_marker_validity | BLOCKER | All `{{ref:URL}}` in collected.json |
| source_sufficiency | WARN | Each DQ has Tier 1-2 sources |
| direction_coverage | WARN | Each search_direction has ≥1 source |
| collected_empty | BLOCKER | collected.json non-empty (implementation extension) |
| direction_tagging | WARN | Every entry has direction field (implementation extension) |

### `fetch --from-stdin`

Reads JSON array from stdin, writes source files and updates collected.json:

```bash
echo '[{"url": "...", "content": "...", "tier": 1, "direction": "tech_arch"}]' | python -m scripts.cli fetch --from-stdin
```

**Tier auto-assignment**: If `tier` is not provided, CLI matches URL domain against config.json sources. If domain not found, defaults to Tier 3. Agent may override by providing `tier` + `tier_override_reason`.

### `verify`

Deterministic source verification. Automatically invoked between Phase 3 and Phase 4.

```bash
python -m scripts.cli verify
```

Reads analysis.json + collected.json + sources/ directory. For each claim:

1. Read source file from `sources/` directory
2. Run number matching
3. Apply indirect source rules
4. Write `source_verification` field back to analysis.json
5. Print verification summary

Structured mode only — requires analysis.json + collected.json + sources/. No free mode.

### `report`

Generates final report from `.workdir/` scope.json + collected.json + analysis.json. Output: `reports/<english_title>.md`

## 7. Code Structure

```
skills/intent-research/
├── SKILL.md                    # Agent behavioral instructions
├── CONTEXT.md                  # Domain vocabulary
├── config.json                 # Tier definitions + routes + CJK sources
├── references/
│   └── writing-guide.md        # -> ../../docs/research/research-writing-guide.md (symlink or copy)
├── scripts/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # ~100 lines: scope-check, fetch, verify, report subcommands
│   ├── gates.py                # ~100 lines: 7 checks (3 BLOCKER + 2 WARN)
│   ├── verify.py               # ~120 lines: source_verification logic
│   ├── reporter.py             # ~130 lines: Markdown rendering + tier labels + †/‡ marks
│   └── lib/
│       ├── __init__.py
│       ├── check_types.py      # ~15 lines: CheckResult dataclass
│       ├── constants.py        # ~50 lines: Valid enums, tier labels, route definitions
│       ├── exceptions.py       # ~10 lines: ArtifactError
│       └── utils.py            # ~70 lines: URL normalization, JSON I/O, project root
└── tests/
    ├── conftest.py             # sys.path setup
    ├── test_gates.py           # ~80 lines: 7 gate tests
    ├── test_verify.py          # ~100 lines: source_verification tests
    └── test_reporter.py        # ~50 lines: rendering tests
```

**Target**: ~550 lines Python + ~230 lines tests

## 8. What is NOT Carried Over from info-collector

| Dropped feature | Reason (ADR) |
|----------------|--------------|
| 39 checks → 7 checks | ADR 0029: gates ensure structure only; ADR 0065: gate treadmill |
| trust_boundary / repair_loop | ADR 0065: AI-verifying-AI anti-pattern |
| deep_dive phase | ADR 0065: empty shell merged in ADR 0064, never provided real value |
| search_plan | ADR 0042: half constraint, adds cognitive load without guidance |
| topic_coverage (token matching) | ADR 0042: narrows search horizon |
| facet_coverage (derived) | Simplified: direction_coverage WARN is sufficient |
| claim_dedup / entity_number_conflict / metric_type_homogeneity | ADR 0029: force LLM judgment checks, auto-downgrade is better |
| subagent delegation requirement | ADR 0065: adds complexity without quality improvement |
| review subagent | ADR 0065: AI-verifying-AI; self-edit checklist sufficient |
| report_checks (10 checks) | ADR 0065: markdownlint's job |
| confidence field | Not needed; reliability expressed by evidence_type + precision + source_verification |
| verify free mode | Cannot work without structured claims; violates YAGNI |
| 3 goal_type options | Replaced by 10 goal_type options with descriptions; 3-option grouping lost routing information |

## 9. Relationship to Other Research Skills

```
                    ┌─────────────────────────┐
                    │   User's research need   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  What's the priority?    │
                    └──┬──────┬──────┬────────┘
                       │      │      │
         ┌─────────────▼┐  ┌──▼──────▼──────┐  ┌──────────────▼┐
         │  Speed        │  │  Intent +      │  │  Saturation   │
         │               │  │  Source quality │  │               │
         │  research     │  │  intent-       │  │  deep-        │
         │  skill        │  │  research      │  │  research /   │
         │               │  │               │  │  ulw-research │
         └───────────────┘  └───────────────┘  └───────────────┘
```

**Complementary, not competitive**:

- **research skill**: Quick lookup, zero code, single agent → use when speed matters
- **intent-research**: Structured investigation with intent alignment + source quality → use when the research informs a decision
- **deep-research / ulw-research**: Maximum saturation → use when you need exhaustive coverage

## 10. Verified Claims from info-collector ADRs

The following design decisions are explicitly validated by production runs and ADR analysis. Each is preserved with its ADR reference:

| Decision | ADR | Evidence |
|----------|-----|----------|
| Indirect > confirmed/absent priority | ADR 0028 | Harness Engineering report: 6 fabricated numbers passed gates because indirect sources were treated as confirmed |
| Gate = structure only | ADR 0029 | 60-source production run: ~100 manual fixes despite all gates passing; gates forced LLM to make authority judgments it systematically got wrong |
| Free search > search_plan | ADR 0042 | RISC-V China run: 20/60 expected sources (33%) with search_plan; research skill (no plan) got 45 sources with broader coverage |
| direction field as WARN | ADR 0052 | v2 reports passed all gates but missed entire facets; direction field restores breadth contract without narrowing search horizon |
| AI-verifying-AI is anti-pattern | ADR 0065 | trust_boundary + repair_loop: subagent validation failed 3x → orchestrator rewrite also failed → incomplete section; the validator was as wrong as the writer |
| Leverage in prompt, not gate | ADR 0065 | writing-guide reduces false depth by ~5x vs. gate checking (measured across 3 production runs) |

## 11. Grilling Decisions

Decisions made during the grilling session (2026-08-06):

| # | Issue | Decision |
|---|-------|----------|
| 1 | Tier is property of source URL or claim-source pair? | Default by URL domain; agent may override with `tier_override_reason`; ‡ marker unchanged |
| 2 | Phase 1 3 goal_type options vs §3.1 10 routes | Use 10 goal_type options with descriptions; agent recommends one based on topic |
| 3 | depth field has no effect | depth drives search budget (max rounds + source count + DQ coverage); names: quick/standard/deep |
| 4 | Phase 4 is AI-verifying-AI? | Renamed to Self-Edit Checklist; prompt-level guidance, not a formal review phase |
| 5 | direction vs decision_questions_answered overlap | Different levels: direction = source-level, DQs_answered = section-level; no mapping required |
| 6 | verify free mode cannot work | Deleted; structured mode only |
| 7 | source_tier assignment missing | Auto-assigned by URL domain matching; default Tier 3 for unknown domains; agent may override with `tier_override_reason` |
| 8 | confidence field unused | Deleted; reliability expressed by evidence_type + precision + source_verification |
| 9 | .workdir/ lifecycle | Phase 0: not exist → create; exist → clear or cancel; preserved after report |
| 10 | report_language undefined | Auto-inferred from topic (CJK→zh, else→en); user may override; config.json default as fallback |
| 11 | verify optional vs mandatory | Mandatory; automatically invoked between Phase 3 and Phase 4; results written back as data annotations |
| 12 | depth rounds hard-coded or advisory | Hard limit; early convergence allowed; no exceeding limit |
| 13 | other goal_type route | Route = "auto"; agent infers from DQs; fallback [2,3,1,4] |

## 12. Open Questions

| # | Question | Default | Revisit trigger |
|---|----------|---------|-----------------|
| 1 | Should decision_questions be required (BLOCKER) or strongly recommended (WARN)? | WARN in v1 | User feedback on friction |
| 2 | Should goal_type routing be enforced (BLOCKER: tier_coverage per route) or advisory? | Advisory (WARN only) | Reports with systematic tier gaps |
