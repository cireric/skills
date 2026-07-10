# ADR 0043: Section plan as reference template, remove source_hints

## Context

T2 run showed that orchestrator's source_hints excluded valuable sources (Reddit 6fb4b30407a3.md was never hinted to any subagent and thus never used). source_hints creates an asymmetric information problem: orchestrator pre-judges which sources each section needs, but its judgment is imperfect, and subagents only see hinted sources.

Section plan's deep_dive_topics provide genuine value — they suggest which findings are worth arguing with 3+ sources based on tension/impact/mechanism criteria. However, the plan's section structure should not be rigid, as agent may discover important topics during analysis that the orchestrator didn't anticipate (e.g., automotive chips, software ecosystem).

## Decision

1. **Section plan is a reference template, not a constraint.** Agent may add, remove, merge, or split sections. Only minimum gate requirements remain (ADR 0002: overview + ≥1 other section for exploratory types).

2. **Remove source_hints from section plan.** Subagent prompt injects all collected.json sources (title + source_file + snippet) equally, without classification. Subagent self-selects relevant sources based on snippet content, not orchestrator labels. Rationale: orchestrator classification is error-prone (proven by T2); flat source list avoids misclassification and negative guidance.

3. **deep_dive_topics retained as advisory.** Suggests anchors worth arguing, but agent may add new anchors beyond the plan. Gate still enforces key_insights ≥2 for panoramic/exploratory sections.

4. **Add WARN check**: if analysis.json's section list deviates >50% from plan (e.g., plan had 5 sections, agent kept only 2), emit WARN to prompt agent review — not a BLOCKER.

## Consequences

- Subagent sees all sources equally → higher source utilization
- Section structure more responsive to discovered content → broader coverage
- deep_dive_topics still provide anchoring guidance → maintains analytical depth floor
- Removes: source_hints field, orchestrator source-to-section mapping logic
- Simplifies: subagent prompt construction (flat source list, no per-section filtering)

## Status: accepted
