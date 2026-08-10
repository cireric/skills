# Intent-Research Domain Vocabulary

## Core Concepts

**decision_questions**:
3-5 questions the research must answer. Declared in Phase 1, used as convergence criterion throughout. Every decision_question must have a directly answering claim in the final report. Recommend 3-5, covering the core value of the research.
_Avoid_: research questions, key questions, DQs (as standalone noun)

**goal_type**:
10-option classification of research intent. Determines search route order (advisory, not enforced). Valid values: tech_selection, competitive_comparison, feasibility_assessment, fact_check, background_check, market_analysis, academic_research, panoramic_understanding, exploratory, other.
_Avoid_: research type, objective type, research category

**depth**:
quick / standard / deep. Drives search budget (max rounds, expected sources, DQ coverage requirement). Hard limit on rounds; early convergence allowed.
_Avoid_: research level, thoroughness, depth level

**search_directions**:
Named search axes declared in scope. Each must have ≥1 source (WARN-level check). Exist as Phase 1 interview context; not gate-enforced as hard constraints.
_Avoid_: search axes, research directions, facets

**direction**:
Per-source field in collected.json indicating which search_direction produced it, or `"other"` for discoveries outside declared directions. Agent-assigned during search.
_Avoid_: facet, topic, coverage tag

**source_tier**:
1-4 authority level. Auto-assigned by URL domain matching against config.json; unknown domains default to Tier 3. Agent may override with `tier_override_reason`. Valid values: 1 (Academic/Standards, precision exact), 2 (Documentation/Open Source, precision exact), 3 (Industry/Expert Blogs, precision range/qualitative), 4 (Community/UGC, precision qualitative only). Source domain→tier mapping: see config.json `sources`.
_Avoid_: source level, source category, authority level

**source_verification**:
Deterministic classification computed by Python code (number matching + indirect rules), never by LLM. Indirect takes priority over confirmed/absent. Valid values: source_confirmed (no marker), source_absent (†), source_indirect (‡). Indirect source rules: see SKILL.md Verify section.
_Avoid_: verification level, trust level, verification status

**evidence_type**:
Claim metadata classifying the evidence: `official_data`, `independent_benchmark`, `third_party_estimate`, `qualitative_trend`, `expert_opinion`. Constrained by precision rules (e.g., `expert_opinion` cannot be `exact`).
_Avoid_: evidence category, evidence class

**precision**:
Claim metadata classifying specificity: `exact`, `range`, `qualitative`. Precision rules: `exact` requires `official_data` or `independent_benchmark`; `third_party_estimate`, `qualitative_trend`, `expert_opinion` must not use `exact`.
_Avoid_: granularity, specificity

**tier_override_reason**:
Required when agent overrides the default tier for a source. ‡ marker in report is not removed by override — the indirect classification reflects source provenance, not agent judgment of authority.
_Avoid_: tier justification, tier note

**convergence**:
Search stops when decision_questions have required source coverage per depth level. Three depth-driven thresholds: quick (each DQ ≥1 source), standard (each DQ ≥1 Tier 1-2 source), deep (each DQ ≥2 Tier 1-2 sources + tension coverage). Convergence failure: mark unanswerable questions, explain why evidence is insufficient.
_Avoid_: completion, search end, stop condition

**tension**:
Conflicting findings across sources. The substance of insight, not the absence of it. The insight is not "X sometimes works" (trivial) but "X's effect depends on condition Z" (incremental).
_Avoid_: contradiction, conflict, disagreement (as standalone)

**audience**:
Report reader type (CTO, engineer, researcher, general). A hint field — recorded in scope.json, informs AI writing tone, but does not drive deterministic code logic.
_Avoid_: reader, target reader

**report_language**:
Language for the final report output (e.g., "zh", "en"). Stored in scope.json, falls back to config.json `default_report_language`, then "en". CJK topic auto-infers "zh"; user may override.
_Avoid_: output language, language

**english_title**:
Required field in scope.json when topic contains non-ASCII characters. Used as the report filename base, ensuring filenames are ASCII-only.
_Avoid_: english name, translated title

**false depth**:
Using analytical language to wrap listed content and create an illusion of depth. Three patterns: pseudo-synthesis (causal language without causal evidence), name-as-analysis (mentioning an entity + one-sentence description without evaluation), action-platitude ("readers need to understand X" without actionable guidance). Pseudo-synthesis is hard-prohibited; name-as-analysis requires ≥2 analytical entries per section; action-platitude is prohibited.
_Avoid_: shallow analysis, fake analysis

**synthesis guard**:
The standard for genuine synthesis: causal direction must be explicitly stated (A→B), and each step in the causal chain must have at least one source supporting it. When this standard cannot be met, the writer must present the observations as "co-occurring phenomena" rather than synthesis.
_Avoid_: synthesis rule, causation requirement

**source_type**:
Field inside a claim's `source_metadata` describing benchmark/test provenance, NOT the authority of the publishing venue. Valid values: official_report, independent_test, production_case, survey, vendor_benchmark, analyst_forecast, vendor_survey, vendor_blog.
_Avoid_: conflating source_type with venue authority; tagging academic papers as vendor_benchmark

**source_metadata**:
Metadata about a claim's source testing conditions: test_conditions (hardware, OS, runtime), test_date, source_type.
_Avoid_: test metadata, benchmark metadata

**reference numbering**:
[N] citation system in the final report. Global numbering across all sections, assigned by first-appearance order. In analysis.json content, sources are referenced via `{{ref:URL}}` markers (URL must match collected.json entry). Hardcoded reference numbers in content are prohibited.
_Avoid_: citation numbering, footnote numbering

## Relationships

- `decision_questions` → `sections` (each DQ maps to ≥1 section via `decision_questions_answered`)
- `goal_type` → search route (advisory order, not enforced)
- `depth` → search budget (hard limit on rounds, early convergence allowed)
- `evidence_type` + `precision` → precision rules (BLOCKER if inconsistent)
- `source_verification` → report markers (†/‡) and verification summary table
- `source_tier` → auto-assigned by URL domain matching against config.json; unknown domains default to Tier 3
- `tier_override_reason` → required when agent overrides default tier; ‡ marker persists regardless
- `audience` does not drive deterministic logic — hint field only
- `report_language` → CJK topic auto-infers "zh"; drives AI writing language and reporter fixed label i18n
- `english_title` → used as report filename base; BLOCKER-required when topic contains non-ASCII
- `false depth` is prohibited by `synthesis guard` and writing-guide content rules
- `synthesis guard` requires explicit causal direction (A→B) with source-supported chain; fallback to "co-occurring phenomena"
- `reference numbering` uses `{{ref:URL}}` markers in analysis.json content; claim.sources must be a subset of content `{{ref:URL}}` markers in the same section
- scope.json → collected.json (search_directions constrain direction field) → analysis.json (claims reference collected URLs) → report (auto-rendered from analysis.json + collected.json)
- config.json sources serve as post-search repair toolbook, not pre-search plan
