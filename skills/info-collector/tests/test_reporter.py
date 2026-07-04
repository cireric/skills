from __future__ import annotations

import json
from pathlib import Path

from scripts.reporter import (
    _TIER_LABELS,
    _build_sv_map,
    _label,
    _render_references,
    _render_test_conditions,
    _render_verification_summary,
    _resolve_ref_markers,
    build_front_matter,
    generate_report,
    sections_to_markdown,
)


class TestResolveRefMarkers:
    def test_single_marker_replaced(self):
        ref_map: dict[str, int] = {}
        result = _resolve_ref_markers("See {{ref:https://example.com}} for details.", ref_map)
        assert "{{ref:" not in result
        assert "[&#91;1&#93;](#refs)" in result
        assert ref_map == {"https://example.com/": 1}

    def test_multiple_markers_numbered_by_first_appearance(self):
        ref_map: dict[str, int] = {}
        result = _resolve_ref_markers("{{ref:https://a.com}} and {{ref:https://b.com}}", ref_map)
        assert "[&#91;1&#93;](#refs)" in result
        assert "[&#91;2&#93;](#refs)" in result
        assert ref_map == {"https://a.com/": 1, "https://b.com/": 2}

    def test_same_url_gets_same_number(self):
        ref_map: dict[str, int] = {}
        result = _resolve_ref_markers("{{ref:https://a.com}} then {{ref:https://a.com}}", ref_map)
        assert result.count("[&#91;1&#93;](#refs)") == 2
        assert ref_map == {"https://a.com/": 1}

    def test_ref_map_accumulates_across_calls(self):
        ref_map: dict[str, int] = {}
        _resolve_ref_markers("{{ref:https://a.com}}", ref_map)
        _resolve_ref_markers("{{ref:https://b.com}}", ref_map)
        assert ref_map == {"https://a.com/": 1, "https://b.com/": 2}

    def test_no_markers_returns_content_unchanged(self):
        ref_map: dict[str, int] = {}
        result = _resolve_ref_markers("No markers here.", ref_map)
        assert result == "No markers here."
        assert ref_map == {}


class TestRenderReferences:
    def test_format_with_titles(self):
        ref_map = {"https://a.com/": 1, "https://b.com/": 2}
        collected = [
            {"url": "https://a.com", "title": "Source A"},
            {"url": "https://b.com", "title": "Source B"},
        ]
        md = _render_references(ref_map, collected)
        assert "## References" in md
        assert '- [1] [Source A](https://a.com/)' in md
        assert '- [2] [Source B](https://b.com/)' in md

    def test_url_without_collected_entry(self):
        ref_map = {"https://unknown.com/": 1}
        md = _render_references(ref_map, [])
        assert '- [1] [https://unknown.com/](https://unknown.com/)' in md

    def test_empty_map(self):
        md = _render_references({}, [])
        assert md == ""


class TestRenderReferencesWithTier:
    def test_tier_1_reference(self):
        ref_map = {"https://a.com/": 1}
        collected = [{"url": "https://a.com", "title": "Source A", "source_tier": "1"}]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source A (★★★☆ Tier 1)](https://a.com/)' in md

    def test_tier_2_reference(self):
        ref_map = {"https://b.com/": 1}
        collected = [{"url": "https://b.com", "title": "Source B", "source_tier": "2"}]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source B (★★☆☆ Tier 2)](https://b.com/)' in md

    def test_tier_3_reference(self):
        ref_map = {"https://c.com/": 1}
        collected = [{"url": "https://c.com", "title": "Source C", "source_tier": "3"}]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source C (★☆☆☆ Tier 3)](https://c.com/)' in md

    def test_tier_4_reference(self):
        ref_map = {"https://d.com/": 1}
        collected = [{"url": "https://d.com", "title": "Source D", "source_tier": "4"}]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source D (☆☆☆☆ Tier 4)](https://d.com/)' in md

    def test_no_tier_no_label(self):
        ref_map = {"https://e.com/": 1}
        collected = [{"url": "https://e.com", "title": "Source E"}]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source E](https://e.com/)' in md
        assert "Tier" not in md

    def test_mixed_tier_references(self):
        ref_map = {"https://a.com/": 1, "https://b.com/": 2, "https://c.com/": 3}
        collected = [
            {"url": "https://a.com", "title": "Source A", "source_tier": "1"},
            {"url": "https://b.com", "title": "Source B"},
            {"url": "https://c.com", "title": "Source C", "source_tier": "3"},
        ]
        md = _render_references(ref_map, collected)
        assert '- [1] [Source A (★★★☆ Tier 1)](https://a.com/)' in md
        assert '- [2] [Source B](https://b.com/)' in md
        assert '- [3] [Source C (★☆☆☆ Tier 3)](https://c.com/)' in md
        lines = md.splitlines()
        ref_lines = [l for l in lines if l.startswith("- [")]
        assert len(ref_lines) == 3

    def test_tier_labels_dict(self):
        assert _TIER_LABELS["1"] == "★★★☆ Tier 1"
        assert _TIER_LABELS["2"] == "★★☆☆ Tier 2"
        assert _TIER_LABELS["3"] == "★☆☆☆ Tier 3"
        assert _TIER_LABELS["4"] == "☆☆☆☆ Tier 4"


class TestBuildFrontMatter:
    def test_basic_structure(self):
        fm = build_front_matter("Test Topic", "tech_selection", "Scope desc", "passed", 2, 10)
        assert fm.startswith("---")
        assert fm.endswith("---")
        assert "topic: Test Topic" in fm
        assert "review_status: passed" in fm
        assert "quality:" not in fm
        assert "version:" not in fm

    def test_no_parent_field(self):
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3)
        assert "parent:" not in fm

    def test_custom_version_removed(self):
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3)
        assert "version:" not in fm


class TestRenderTestConditions:
    def test_two_claims_with_metadata(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "A100-80GB, CUDA 12.1, Ubuntu 22.04",
                    "test_date": "2026-Q1",
                    "source_type": "independent_test",
                },
            },
            {
                "text": "Claim B",
                "source_urls": ["https://b.com"],
                "source_metadata": {
                    "test_conditions": "H100-80GB, CUDA 12.2",
                    "test_date": "2026-03",
                    "source_type": "vendor_benchmark",
                },
            },
        ]
        md = _render_test_conditions(claims)
        assert "**Test Conditions:**" in md
        assert "| Claim | Conditions | Date | Source Type |" in md
        assert "A100-80GB, CUDA 12.1, Ubuntu 22.04" in md
        assert "2026-Q1" in md
        assert "independent_test" in md
        assert "H100-80GB, CUDA 12.2" in md
        assert "2026-03" in md
        assert "vendor_benchmark" in md

    def test_claims_without_metadata(self):
        claims = [
            {"text": "Claim A", "source_urls": ["https://a.com"]},
            {"text": "Claim B", "source_urls": ["https://b.com"]},
        ]
        md = _render_test_conditions(claims)
        assert md == ""

    def test_mixed_claims(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "A100-80GB",
                    "test_date": "2026-Q1",
                    "source_type": "independent_test",
                },
            },
            {"text": "Claim B", "source_urls": ["https://b.com"]},
            {
                "text": "Claim C",
                "source_urls": ["https://c.com"],
                "source_metadata": {
                    "test_conditions": "H100-80GB",
                    "test_date": "2026-03",
                    "source_type": "vendor_benchmark",
                },
            },
        ]
        md = _render_test_conditions(claims)
        assert "**Test Conditions:**" in md
        assert "A100-80GB" in md
        assert "H100-80GB" in md
        assert "Claim B" not in md

    def test_empty_test_conditions_field(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "",
                    "test_date": "2026-Q1",
                    "source_type": "independent_test",
                },
            },
        ]
        md = _render_test_conditions(claims)
        assert "**Test Conditions:**" in md
        assert "| " in md

    def test_reference_map_provided(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "A100-80GB",
                    "test_date": "2026-Q1",
                    "source_type": "independent_test",
                },
            },
        ]
        ref_map = {"https://a.com/": 1}
        md = _render_test_conditions(claims, ref_map)
        assert "[1]" in md

    def test_all_empty_metadata_fields_no_row(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "",
                    "test_date": "",
                    "source_type": "",
                },
            },
        ]
        md = _render_test_conditions(claims)
        assert md == ""

    def test_mixed_empty_and_populated_metadata(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://a.com"],
                "source_metadata": {
                    "test_conditions": "",
                    "test_date": "",
                    "source_type": "",
                },
            },
            {
                "text": "Claim B",
                "source_urls": ["https://b.com"],
                "source_metadata": {
                    "test_conditions": "H100-80GB",
                    "test_date": "2026-Q1",
                    "source_type": "vendor_benchmark",
                },
            },
        ]
        md = _render_test_conditions(claims)
        assert "**Test Conditions:**" in md
        assert "Claim A" not in md
        assert "H100-80GB" in md
        assert "2026-Q1" in md
        assert "vendor_benchmark" in md

    def test_reference_map_with_non_normalized_url(self):
        claims = [
            {
                "text": "Claim A",
                "source_urls": ["https://WWW.Example.COM/Path/"],
                "source_metadata": {
                    "test_conditions": "A100-80GB",
                    "test_date": "2026-Q1",
                    "source_type": "independent_test",
                },
            },
        ]
        ref_map = {"https://example.com/path": 1}
        md = _render_test_conditions(claims, ref_map)
        assert "[1]" in md


class TestSectionsToMarkdownWithTestConditions:
    def test_section_with_source_metadata_claims(self):
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "Some content here {{ref:https://a.com}}.",
                    "claims": [
                        {
                            "text": "Claim A",
                            "source_urls": ["https://a.com"],
                            "source_metadata": {
                                "test_conditions": "A100-80GB",
                                "test_date": "2026-Q1",
                                "source_type": "independent_test",
                            },
                        }
                    ],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "**Test Conditions:**" in md
        assert "A100-80GB" in md
        assert "2026-Q1" in md
        assert "independent_test" in md

    def test_section_without_source_metadata_claims(self):
        analysis = {
            "sections": [
                {
                    "id": "intro",
                    "title": "Intro",
                    "content": "Just intro {{ref:https://a.com}}.",
                    "claims": [
                        {"text": "Claim A", "source_urls": ["https://a.com"]}
                    ],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "**Test Conditions:**" not in md


class TestSectionsToMarkdown:
    def test_single_section(self):
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "Some content here {{ref:https://example.com}}.",
                    "claims": [{"text": "A claim.", "source_urls": ["https://example.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "## Overview" in md
        assert "Some content here" in md
        assert "A claim." in md
        assert "[&#91;1&#93;](#refs)" in md

    def test_section_without_claims(self):
        analysis = {
            "sections": [
                {
                    "id": "intro",
                    "title": "Intro",
                    "content": "Just intro.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "Just intro." in md
        assert "Sources:" not in md

    def test_duplicate_title_stripped(self):
        """Content starting with ## {title} — duplicate heading stripped."""
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "## Overview\nSome content here.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert md.count("## Overview") == 1
        assert "Some content here." in md

    def test_subheading_preserved(self):
        """### headings in content are NOT stripped."""
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "### Overview\nSome content here.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        lines = md.splitlines()
        h2_lines = [l for l in lines if l.strip().startswith("## ") and not l.strip().startswith("### ")]
        assert len(h2_lines) == 1
        assert h2_lines[0] == "## Overview"
        assert "### Overview" in md
        assert "Some content here." in md

    def test_non_matching_heading_preserved(self):
        """## Different Title in content is NOT stripped."""
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "## Different Title\nSome content here.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert md.count("## Overview") == 1
        assert "## Different Title" in md
        assert "Some content here." in md

    def test_panoramic_understanding_no_source_list(self):
        """panoramic_understanding goal_type skips per-section source lists."""
        analysis = {
            "topic": "T",
            "goal_type": "panoramic_understanding",
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "Some content here {{ref:https://example.com}}.",
                    "claims": [{"text": "A claim.", "source_urls": ["https://example.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "## Overview" in md
        assert "Some content here" in md
        assert "**Sources:**" not in md
        assert "**数据来源:**" not in md
        assert "A claim." not in md
        assert "## References" in md

    def test_tech_selection_still_has_source_list(self):
        """tech_selection goal_type still renders per-section source lists."""
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "Some content here {{ref:https://example.com}}.",
                    "claims": [{"text": "A claim.", "source_urls": ["https://example.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "**Sources:**" in md
        assert "A claim." in md


class TestSectionsToMarkdownRefMarkers:
    def test_markers_resolved_not_in_output(self):
        analysis = {
            "sections": [
                {
                    "id": "s1",
                    "title": "Section 1",
                    "content": "See {{ref:https://example.com}} for details.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "{{ref:" not in md
        assert "[&#91;1&#93;](#refs)" in md

    def test_claim_source_url_gets_correct_number(self):
        analysis = {
            "sections": [
                {
                    "id": "s1",
                    "title": "Section 1",
                    "content": "Some content {{ref:https://a.com}} here.",
                    "claims": [{"text": "Claim A", "source_urls": ["https://a.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "[&#91;1&#93;](#refs)" in md
        assert "- Claim A [1]" in md

    def test_multiple_sections_shared_urls_consistent_numbering(self):
        analysis = {
            "sections": [
                {
                    "id": "s1",
                    "title": "Section 1",
                    "content": "First {{ref:https://a.com}} and {{ref:https://b.com}}.",
                    "claims": [{"text": "Claim A", "source_urls": ["https://a.com"]}],
                },
                {
                    "id": "s2",
                    "title": "Section 2",
                    "content": "Second {{ref:https://a.com}} again.",
                    "claims": [{"text": "Claim B", "source_urls": ["https://a.com", "https://b.com"]}],
                },
            ],
        }
        md = sections_to_markdown(analysis)
        assert md.count("[&#91;1&#93;](#refs)") >= 2
        assert "[&#91;2&#93;](#refs)" in md
        assert "- Claim B [1][2]" in md


class TestGenerateReport:
    def test_full_report(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "AI Frameworks",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "comparison",
                        "title": "Comparison",
                        "content": "PyTorch vs TensorFlow {{ref:https://example.com}}.",
                        "claims": [
                            {"text": "PyTorch is popular.", "source_urls": ["https://example.com"]}
                        ],
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "scope.json",
            {
                "topic": "AI Frameworks",
                "goal_type": "tech_selection",
                "scope_description": "Compare PyTorch and TensorFlow",
            },
        )
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            review_status="passed",
            search_rounds=2,
            source_count=5,
        )
        assert "topic: AI Frameworks" in report
        assert "review_status: passed" in report
        assert "## Comparison" in report
        assert "PyTorch vs TensorFlow" in report
        assert "PyTorch is popular." in report

    def test_report_language_explicit_parameter(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "t", "scope_description": "S"})
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=1,
            report_language="fr",
        )
        assert "report_language: fr" in report

    def test_report_language_from_scope(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(
            tmp_path / "scope.json",
            {
                "topic": "T",
                "goal_type": "t",
                "scope_description": "S",
                "report_language": "zh",
            },
        )
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=1,
        )
        assert "report_language: zh" in report

    def test_report_language_defaults_to_en(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "t", "scope_description": "S"})
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=1,
        )
        assert "report_language: en" in report


class TestI18nLabels:
    _BASIC_SCOPE = {"topic": "AI", "goal_type": "tech_selection", "scope_description": "Desc"}
    _BASIC_ANALYSIS = {
        "topic": "AI",
        "goal_type": "tech_selection",
        "sections": [
            {
                "id": "s1",
                "title": "Section 1",
                "content": "Content. {{ref:https://a.com}}",
                "claims": [
                    {
                        "text": "Claim A",
                        "source_urls": ["https://a.com"],
                        "source_metadata": {
                            "test_conditions": "GPU A100",
                            "test_date": "2026",
                            "source_type": "benchmark",
                        },
                    }
                ],
            }
        ],
    }

    def _gen_report(self, tmp_path, report_language=None):
        _write_json(tmp_path / "analysis.json", self._BASIC_ANALYSIS)
        _write_json(tmp_path / "scope.json", self._BASIC_SCOPE)
        kwargs = dict(
            review_status="passed",
            search_rounds=1,
            source_count=1,
        )
        if report_language is not None:
            kwargs["report_language"] = report_language
        return generate_report(tmp_path / "analysis.json", tmp_path / "scope.json", **kwargs)

    def test_zh_labels(self, tmp_path):
        report = self._gen_report(tmp_path, report_language="zh")
        assert "数据来源" in report
        assert "参考文献" in report
        assert "测试环境" in report
        assert "声明" in report
        assert "条件" in report
        assert "日期" in report
        assert "来源类型" in report

    def test_en_labels(self, tmp_path):
        report = self._gen_report(tmp_path, report_language="en")
        assert "Sources" in report
        assert "References" in report
        assert "Test Conditions" in report
        assert "Claim" in report
        assert "Conditions" in report
        assert "Date" in report
        assert "Source Type" in report

    def test_unsupported_lang_falls_back_to_en(self, tmp_path):
        report = self._gen_report(tmp_path, report_language="ja")
        assert "Sources" in report
        assert "References" in report
        assert "Test Conditions" in report

    def test_no_report_language_defaults_to_en(self, tmp_path):
        report = self._gen_report(tmp_path)
        assert "Sources" in report
        assert "References" in report
        assert "Test Conditions" in report

    def test_label_helper_directly(self):
        assert _label("sources", "en") == "Sources"
        assert _label("sources", "zh") == "数据来源"
        assert _label("references", "en") == "References"
        assert _label("references", "zh") == "参考文献"
        assert _label("test_conditions", "en") == "Test Conditions"
        assert _label("test_conditions", "zh") == "测试环境"
        assert _label("claim", "en") == "Claim"
        assert _label("claim", "zh") == "声明"
        assert _label("conditions", "en") == "Conditions"
        assert _label("conditions", "zh") == "条件"
        assert _label("date", "en") == "Date"
        assert _label("date", "zh") == "日期"
        assert _label("source_type", "en") == "Source Type"
        assert _label("source_type", "zh") == "来源类型"
        # Unsupported lang falls back to en
        assert _label("sources", "ja") == "Sources"
        # Unknown key returns the key itself
        assert _label("nonexistent", "en") == "nonexistent"
        assert _label("nonexistent", "zh") == "nonexistent"


class TestResolveRefMarkersWithVerification:
    def test_confirmed_url_no_marker(self):
        ref_map = {}
        sv_map = {"https://a.com/": "source_confirmed"}
        result = _resolve_ref_markers("See {{ref:https://a.com}}", ref_map, sv_map)
        assert "[&#91;1&#93;](#refs)" in result
        assert "†" not in result
        assert "‡" not in result

    def test_absent_url_dagger_marker(self):
        ref_map = {}
        sv_map = {"https://a.com/": "source_absent"}
        result = _resolve_ref_markers("See {{ref:https://a.com}}", ref_map, sv_map)
        assert "[&#91;1†&#93;](#refs)" in result

    def test_indirect_url_double_dagger_marker(self):
        ref_map = {}
        sv_map = {"https://a.com/": "source_indirect"}
        result = _resolve_ref_markers("See {{ref:https://a.com}}", ref_map, sv_map)
        assert "[&#91;1‡&#93;](#refs)" in result

    def test_no_sv_map_backwards_compatible(self):
        ref_map = {}
        result = _resolve_ref_markers("See {{ref:https://a.com}}", ref_map)
        assert "[&#91;1&#93;](#refs)" in result


class TestBuildSvMap:
    def test_worst_status_per_url(self):
        analysis = {
            "sections": [{
                "claims": [
                    {"source_urls": ["https://a.com"], "source_verification": "source_confirmed"},
                    {"source_urls": ["https://a.com"], "source_verification": "source_absent"},
                ]
            }]
        }
        sv_map = _build_sv_map(analysis)
        assert sv_map["https://a.com/"] == "source_absent"


class TestFrontMatterRepositioning:
    def test_review_status_replaces_quality(self):
        fm = build_front_matter("T", "other", "S", "passed", 1, 3)
        assert "review_status: passed" in fm
        assert "quality:" not in fm

    def test_verification_required_field(self):
        fm = build_front_matter("T", "other", "S", "passed", 1, 3)
        assert "verification_required: true" in fm


class TestVerificationSummary:
    def test_summary_includes_disclaimer(self):
        analysis = {"sections": [{"claims": [{"source_verification": "source_confirmed", "source_urls": []}]}]}
        result = _render_verification_summary(analysis)
        assert "research starting point" in result
        assert "†" in result
        assert "‡" in result

    def test_no_summary_when_no_verification(self):
        analysis = {"sections": [{"claims": [{"source_urls": []}]}]}
        result = _render_verification_summary(analysis)
        assert result == ""


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
