# PRD: Info-Collector Quality Optimization

> Generated: 2026-06-11
> Supersedes: docs/info-collector-improvement-proposal.md (P0 items only; P1/P2 deferred)
> Status: completed

---

## Problem Statement

Info-collector's reporter.py produces reports that violate SKILL.md's own mandatory requirements: missing methodology sections for quantitative goal types, no test environment summaries for benchmark claims, no reference appendix, and claim metadata (evidence_type/confidence/precision) is collected and validated but never rendered. Additionally, the final report is regenerated from analysis.json, discarding any quality improvements made during draft review. There is no first-run setup wizard, so users must manually configure output_dir and other settings. The search phase lacks guidance on query language, causing Chinese-topic searches to miss high-quality English sources.

## Solution

Two focused improvements:

1. **First-run setup wizard** (AI conversational, no new code): Guide users through config.json setup on first run — output_dir, default_report_language, default_depth, and source customization. Add report_language to scope.json (per-research, with config.json default). Add English-query-for-English-sources guidance to SKILL.md Phase 2.

2. **Reporter.py quality fixes** (4 bugs): Add methodology section requirement for quantitative goal types. Generate Test Conditions table from source_metadata. Generate [N] reference numbering + References appendix from collected.json. Add i18n for fixed labels (Sources/数据来源, References/参考文献, etc.) driven by report_language. Clarify draft as review-readable rendering of analysis.json; final report rendered from (reviewed) analysis.json by reporter.py.

## User Stories

### Setup Wizard

1. As a first-time user, I want to be guided through config.json setup when I invoke info-collector for the first time, so that I don't have to manually edit JSON
2. As a first-time user, I want to set my report output directory during setup, so that reports go to the right place
3. As a user, I want to specify an absolute or relative path for output_dir, so that I can place reports inside or outside my project
4. As a first-time user, I want to set a default report language (e.g., zh or en), so that I don't have to specify it every time I start a research
5. As a first-time user, I want to set a default search depth (quick/standard/deep), so that it matches my typical research intensity
6. As a first-time user, I want to add or remove sources from the 4-tier source list, so that I can include sources relevant to my domain (e.g., Dev.to instead of Medium)
7. As a returning user, I want to re-run the setup wizard at any time, so that I can update my configuration without editing JSON manually
8. As a user, I want report_language to be decided per-research in Phase 1 interview, so that I can write Chinese reports for my team and English reports for international audiences
9. As a user, I want report_language to fall back to config.json's default_report_language if I don't specify it, so that I save time on typical researches

### Search Language

10. As a Chinese-speaking researcher, I want English-language sources to be searched with English queries, so that I get high-quality results from arXiv, GitHub, etc. even when my topic is in Chinese
11. As a researcher, I want Chinese-language sources (CNKI, Zhihu) to be searched with Chinese queries, so that I get relevant Chinese results

### Reporter Quality

12. As a report reader, I want quantitative reports (tech_selection, competitive_comparison, etc.) to include a methodology section, so that I can assess the rigor of the analysis
13. As a report reader, I want benchmark claims to show test conditions (hardware, OS, runtime, date) in a structured table, so that I can evaluate comparability across sources
14. As a report reader, I want claims to use [N] reference numbers instead of raw URLs, so that the report text is readable
15. As a report reader, I want a References appendix at the end of the report mapping [N] to full URLs and titles, so that I can look up sources
16. As a Chinese report reader, I want fixed labels (Sources, References, Test Conditions) to appear in Chinese, so that the report feels natural
17. As an English report reader, I want fixed labels to appear in English, so that the report feels natural
18. As a researcher, I want the draft to be a readable rendering of analysis.json for review purposes, so that I can spot issues in the structured data
19. As a researcher, I want the final report to be rendered from the reviewed (and possibly fixed) analysis.json, so that review fixes are reflected in the output
20. As a researcher, I want AI to write full Markdown narrative in analysis.json sections[].content, so that the final report has rich formatting (tables, emphasis, transitions)
21. As a researcher doing iterative research, I want version auto-increment to work correctly, so that v1, v2, v3 are all preserved in output_dir

### Fact Check Bug Fix

22. As a fact-check researcher, I want fact_check to route to Academic/Standards tier first, so that I get authoritative sources instead of an empty source list

## Implementation Decisions

### Module 1: SKILL.md — Setup Wizard Flow

- Add a "Setup Wizard" section before Phase 1 in SKILL.md
- Wizard triggers when config.json does not exist
- Wizard is AI-conversational (no new Python code)
- Wizard collects: output_dir (relative or absolute), default_report_language (zh/en/...), default_depth (quick/standard/deep), source customization (add/remove sources per tier)
- User can re-invoke wizard at any time by requesting it
- No new CLI subcommand needed

### Module 2: config.json — New Fields

- Add `"default_report_language": "zh"` field
- Add `"default_depth": "standard"` field
- Fix `"fact_check"` route: change `entry_tier` from 0 to 1, change `path` from [1, 2] to [1, 2, 4]
- Existing fields (`sources`, `routes`, `output_dir`, `goal_type_defaults`) remain unchanged

### Module 3: scope.json — report_language Field

- Add `"report_language"` field to scope.json schema
- Phase 1 interview asks for report_language, falls back to config.json `default_report_language`
- `proceed.py` `_check_scope_schema()` validates report_language is a non-empty string (no fixed enum — allows future languages)
- `reporter.py` reads report_language from scope.json to drive label i18n

### Module 4: SKILL.md — Phase 2 Search Language Guidance

- Add rule to Phase 2: "Search English-language sources using English queries even if the topic is in Chinese. Translate search keywords to English for site: queries on English domains. Use Chinese queries only for Chinese domains (cnki.net, zhihu.com)."
- No code change — this is an instruction to the AI agent

### Module 5: gateway.py — Methodology Section Requirement

- Add `"methodology"` to `_REQUIRED_SECTION_IDS` for all 5 quantitative goal types:
  - `tech_selection`: ["overview", "comparison", "recommendation", "methodology"]
  - `competitive_comparison`: ["overview", "comparison", "positioning", "methodology"]
  - `feasibility_assessment`: ["overview", "analysis", "conclusion", "methodology"]
  - `market_analysis`: ["overview", "data", "trends", "conclusion", "methodology"]
  - `academic_research`: ["abstract", "findings", "references", "methodology"]

### Module 6: SKILL.md — Phase 3a Methodology Guidance

- Add instruction: "For quantitative goal_types (tech_selection, competitive_comparison, feasibility_assessment, market_analysis, academic_research), include a section with id='methodology' in analysis.json sections. Content should describe: data sources and their test conditions, limitations of cross-source comparisons, date range of data collection."

### Module 7: reporter.py — Reference Numbering + Appendix

- New function: `_build_reference_map(analysis, collected) -> dict[str, int]` — traverses all claim source_urls, deduplicates, assigns sequential [N] numbers by first-appearance order
- New function: `_render_references(reference_map, collected) -> str` — generates `## References` / `## 参考文献` section with `[N]: URL — title` entries
- `sections_to_markdown()` changes:
  - Claim rendering: `- claim text [1][2]` instead of `- claim text (url1, url2)`
  - After all sections, append References appendix
- Title lookup: match claim source_url against collected.json entries by normalized URL

### Module 8: reporter.py — Test Conditions Table

- New function: `_render_test_conditions(claims_with_metadata) -> str` — generates a Markdown table from source_metadata fields
- Table columns: Claim | Hardware/Conditions | Runtime/Version | Date | Source Type
- Rendered after each section's Sources block, only if any claim in that section has source_metadata
- If source_metadata.test_conditions is a free-text string, render it in a single "Conditions" column instead of splitting into columns

### Module 9: reporter.py — i18n Label System

- New constant: `_LABELS` dict mapping `(label_key, language) -> str`:
  ```
  ("sources", "zh"): "数据来源"
  ("sources", "en"): "Sources"
  ("references", "zh"): "参考文献"
  ("references", "en"): "References"
  ("test_conditions", "zh"): "测试环境"
  ("test_conditions", "en"): "Test Conditions"
  ("claim", "zh"): "声明"
  ("claim", "en"): "Claim"
  ("conditions", "zh"): "条件"
  ("conditions", "en"): "Conditions"
  ("date", "zh"): "日期"
  ("date", "en"): "Date"
  ("source_type", "zh"): "来源类型"
  ("source_type", "en"): "Source Type"
  ```
- `reporter.py` reads `report_language` from scope.json (passed through `generate_report()`)
- Default to "en" if report_language not set
- All hardcoded labels replaced with `_label(key, lang)` — fallback chain: requested lang → "en" → return key as-is

### Module 10: SKILL.md — Draft Positioning Clarification

- Clarify that draft/report.md is a readable rendering of analysis.json for review purposes
- Clarify that review fixes target analysis.json (not draft)
- Clarify that final report is rendered by reporter.py from the reviewed analysis.json
- Clarify that AI should write full Markdown narrative in sections[].content (tables, emphasis, transitions are all valid)

### Module 11: source_router.py — Default Depth Fallback

- `get_default_depth()` currently reads from `goal_type_defaults` only
- Add fallback: if goal_type not in `goal_type_defaults`, check config.json `default_depth` before falling back to hardcoded "standard"
- Priority: goal_type_defaults[goal_type].depth > config.json.default_depth > "standard"

## Testing Decisions

### What makes a good test

- Test external behavior (rendered output), not implementation details (internal function structure)
- Use `tmp_path` for file isolation (existing pattern)
- Use config injection for source_router tests (existing pattern)
- No mocking — real file I/O with constructed test data

### Modules to test

| Module | Test file | Priority |
|--------|-----------|----------|
| `_build_reference_map()` | test_reporter.py | High — new logic, core to reference numbering |
| `_render_references()` | test_reporter.py | High — output format must be exact |
| `_render_test_conditions()` | test_reporter.py | High — new logic, table formatting |
| i18n label system | test_reporter.py | Medium — simple dict lookup, but must cover zh/en |
| `sections_to_markdown()` with [N] refs | test_reporter.py | High — changes existing output format |
| gateway `_REQUIRED_SECTION_IDS` with methodology | test_gateway.py | Medium — verify new section IDs are correct |
| scope.json `report_language` validation | test_proceed.py | Medium — new field validation |
| `get_default_depth()` with config fallback | test_source_router.py | Low — simple priority chain |
| fact_check route fix | test_source_router.py | Medium — verify entry_tier=1, path=[1,2,4] |

### Prior art

- Existing test_reporter.py: 27 tests (6 original + 3 ref map + 3 references + 5 test conditions + 2 sections-with-test-conditions + 2 sections + 4 generate-report + 2 report_language) — now 27 after adding i18n tests
- Existing test_gateway.py: 23 tests (9 original + 10 methodology + 4 others)
- Existing test_proceed.py: 20 tests (11 original + 4 report_language + 5 others)
- Existing test_source_router.py: 17 tests (10 original + 5 default_depth fallback + 2 fact_check)
- Total: 96 tests (was 36 before this PRD)

## Out of Scope

- Template engine (Jinja2 / Builder Pattern) — not needed; reporter.py direct fixes sufficient
- `audience`-driven output differentiation — audience has zero code-level behavior impact; only affects AI prompt guidance
- Claim metadata rendering (evidence_type/confidence/precision) — only used for gateway validation, not shown to report readers
- P1/P2 items from info-collector-improvement-proposal.md: preflight, dedupe, entity_extract, fusion, rerank, trust_level, provenance, OUTPUT_LAWS — these are separate future work
- `depth` field making any code-level behavior difference — currently only a hint to AI
- Cross-session iteration dedup/diff infrastructure — documented but not implemented
- CLI integration tests (cmd_* functions) — valuable but orthogonal to this PRD's quality focus
- `check_precision_inflation` / `check_claim_metadata` test coverage — valuable but orthogonal; should be a separate task

## Further Notes

### Relationship to existing improvement proposal

This PRD focuses on the quality and UX gaps identified through the grill-with-docs session. It supersedes only the P0 items from `docs/info-collector-improvement-proposal.md` (fact_check route fix). The P1/P2 items (preflight, dedupe, fusion, etc.) remain valid future work but are out of scope here.

### Key architectural insight

The grill session revealed that the "reporter.py output quality" problem is not a template system problem — it's 4 specific bugs plus a draft→final architecture issue. The fix is targeted: enrich analysis.json schema expectations (methodology section), add rendering logic for existing but ignored data (source_metadata → test conditions table, source_urls → reference numbering), and add i18n for fixed labels. No new dependencies, no template engine, no architectural overhaul.

### Draft→Final flow (corrected)

```
Phase 3a: AI writes analysis.json (content = full Markdown narrative)
Phase 3b: reporter.py renders draft/report.md (for review readability)
Phase 3c: subagent reviews draft + analysis.json → fixes analysis.json
Phase 3d: user confirms → reporter.py re-renders final report from analysis.json
```

This ensures review fixes are captured in structured data (analysis.json) and reflected in the final output, while giving AI freedom to write rich content in the content field.
