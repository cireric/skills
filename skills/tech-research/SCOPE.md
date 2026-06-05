# Scope — Phase 1 Reference

## Config (first-time only)

Check `config.json`:
- Exists → read it. Verify `output_dir` path exists on disk. If missing, ask: "Output dir `{path}` doesn't exist. Create automatically?"
- Missing → ask 2 questions together: output_dir (default `reports/`), lang (default `zh`). Save after all answered.

Silently list existing reports in output dir to avoid duplicate topics.

## Scope Interview — Ask Together

**Q1: What decision does this research support?**
> Tech selection / Feasibility assessment / Panoramic understanding / Competitive comparison / Exploratory

**Q2: Who is the audience?**
> Myself / Team sharing / Decision maker

**Q3: Time budget?**
> Hours (quick scan) / Days (standard) / Weeks (deep research with PoC)

### Natural language → enum mapping

When the user answers in natural language, map to the exact enum values before saving `scope.json`:

| User's language (CN/EN) | `goal_type` enum |
|---|---|
| 了解、看看、探索、explore、learn、just curious | `exploratory` |
| 全面了解、全景、概览、landscape、overview、understand | `panoramic_understanding` |
| 选型、比较方案、choose、select、pick | `tech_selection` |
| 评估、可行性、feasible、assess、evaluate | `feasibility_assessment` |
| 对比、竞品分析、compare、versus、benchmark | `competitive_comparison` |

| User's language | `audience` enum |
|---|---|
| 自己、个人、myself、just me | `myself` |
| 团队、分享、team、sharing | `team_sharing` |
| 决策者、领导、老板、decision maker、boss、exec | `decision_maker` |

| User's language | `time_constraint` enum |
|---|---|
| 快速、几小时、hours、quick | `hours` |
| 标准、几天、days、standard | `days` |
| 深度、几周、weeks、deep、thorough | `weeks` |

| User's language | `quality_standard` enum |
|---|---|
| 3个以上来源、3+ sources、多方确认 | `3_sources` |
| Demo、PoC、跑通、prototype | `demo_poc` |
| 对比矩阵、comparison matrix、全维度 | `comparison_matrix` |

### Branch questions (adapt by Q1)

**Exploratory**: Also ask → "有没有特别感兴趣的方面？还是全面扫一遍？" If specific aspects → set `focus_aspects`. If broad → leave empty.

**Panoramic understanding**: Also ask → "Full landscape or deep-dive on one aspect? Which aspects?" (architecture / ecosystem / performance / community / security / practice / deployment)

**Tech selection**: Also ask → "Which candidates? Elimination criteria? Existing baseline?"

**Feasibility assessment**: Also ask → "Which technology? What constraints would make it infeasible?"

**Competitive comparison**: Also ask → "Which competitors? Comparison dimensions?" (features / performance / cost / ecosystem / community / security)

### Quality standard

Ask: "What's good enough? 3+ independent sources confirm / Demo/PoC passes / Comparison matrix covers all"

For `exploratory` goal type, default to `3_sources` if user has no preference.

## User Confirmation

After the interview, display scope summary:
- Topic
- Goal type + key constraints
- Audience
- Time budget

Ask: "以上理解是否正确？需要修改吗？"

Only proceed to Phase 2 after user confirms.

## Scope Revision

During Phase 2/3, if new constraints emerge:
1. Update relevant fields in `scope.json > standardized`
2. Append a revision record to `scope.json > revisions`
3. Notify user of the change (no full re-confirmation needed)

## scope.json Schema

```json
{
  "topic": "<research topic>",
  "revisions": [
    {
      "at": "2026-06-05T14:30:00",
      "phase": "research | report",
      "changes": "description of change",
      "fields_changed": ["standardized.candidates"]
    }
  ],
  "search_log": [
    {
      "round": 1,
      "queries": ["query1", "query2"],
      "results_count": 12,
      "new_keywords": ["keyword1"],
      "coverage_after": {"covered": 5, "gaps": ["deployment"]}
    }
  ],
  "coverage": {
    "checked_at": "2026-06-04T10:30:00",
    "supplementary_rounds": 0,
    "matrix": [
      { "item": "security", "sources": ["src1", "src2"], "status": "covered" },
      { "item": "deployment", "sources": [], "status": "gap", "note": "needs sources" }
    ],
    "unresolved_gaps": ["deployment"]
  },
  "standardized": {
    "goal_type": "exploratory | panoramic_understanding | tech_selection | feasibility_assessment | competitive_comparison",
    "audience": "myself | team_sharing | decision_maker",
    "depth": "landscape | deep_dive",
    "focus_aspects": ["architecture", "security"],
    "candidates": ["OptionA", "OptionB"],
    "elimination_criteria": "...",
    "baseline": "...",
    "technology": "...",
    "constraints": "...",
    "comparison_dimensions": ["features", "performance"],
    "existing_data": "...",
    "quality_standard": "3_sources | demo_poc | comparison_matrix",
    "time_constraint": "hours | days | weeks"
  }
}
```

> Fields in `standardized` populate based on `goal_type` — only relevant fields are filled. `goal_type`, `audience`, `quality_standard`, `time_constraint` are always present. `revisions` and `search_log` are optional, default to empty arrays.
