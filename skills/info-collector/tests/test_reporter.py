from __future__ import annotations

import json
from pathlib import Path

from scripts.reporter import (
    _build_reference_map,
    _label,
    _render_references,
    _render_test_conditions,
    build_front_matter,
    generate_report,
    sections_to_markdown,
)


class TestBuildReferenceMap:
    def test_overlapping_urls_deduped(self):
        analysis = {
            "sections": [
                {"claims": [{"text": "A", "source_urls": ["https://a.com"]}]},
                {"claims": [{"text": "B", "source_urls": ["https://b.com", "https://a.com"]}]},
            ]
        }
        ref_map = _build_reference_map(analysis, [])
        # a.com appears first, gets 1; b.com second, gets 2
        assert ref_map == {"https://a.com/": 1, "https://b.com/": 2}

    def test_no_source_urls(self):
        analysis = {"sections": [{"claims": [{"text": "A", "source_urls": []}]}]}
        ref_map = _build_reference_map(analysis, [])
        assert ref_map == {}

    def test_first_appearance_ordering(self):
        analysis = {
            "sections": [
                {"claims": [{"text": "A", "source_urls": ["https://z.com"]}]},
                {"claims": [{"text": "B", "source_urls": ["https://a.com"]}]},
            ]
        }
        ref_map = _build_reference_map(analysis, [])
        assert ref_map["https://z.com/"] == 1
        assert ref_map["https://a.com/"] == 2


class TestRenderReferences:
    def test_format_with_titles(self):
        ref_map = {"https://a.com/": 1, "https://b.com/": 2}
        collected = [
            {"url": "https://a.com", "title": "Source A"},
            {"url": "https://b.com", "title": "Source B"},
        ]
        md = _render_references(ref_map, collected)
        assert "## References" in md
        assert "[1]: https://a.com/ — Source A" in md
        assert "[2]: https://b.com/ — Source B" in md

    def test_url_without_collected_entry(self):
        ref_map = {"https://unknown.com/": 1}
        md = _render_references(ref_map, [])
        assert "[1]: https://unknown.com/" in md

    def test_empty_map(self):
        md = _render_references({}, [])
        assert md == ""


class TestBuildFrontMatter:
    def test_basic_structure(self):
        fm = build_front_matter("Test Topic", "tech_selection", "Scope desc", "passed", 2, 10)
        assert fm.startswith("---")
        assert fm.endswith("---")
        assert "topic: Test Topic" in fm
        assert "quality: passed" in fm
        assert "version: 1" in fm

    def test_no_parent_field(self):
        """ADR 0009: cross-session iteration removed, no parent in front matter."""
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3)
        assert "parent:" not in fm

    def test_custom_version(self):
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3, version=3)
        assert "version: 3" in fm


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
                    "content": "Some content here.",
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
                    "content": "Just intro.",
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
                    "content": "Some content here.",
                    "claims": [{"text": "A claim.", "source_urls": ["https://example.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "## Overview" in md
        assert "Some content here." in md
        assert "A claim." in md
        assert "https://example.com" in md

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
                        "content": "PyTorch vs TensorFlow.",
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
            quality="passed",
            search_rounds=2,
            source_count=5,
        )
        assert "topic: AI Frameworks" in report
        assert "quality: passed" in report
        assert "## Comparison" in report
        assert "PyTorch vs TensorFlow." in report
        assert "PyTorch is popular." in report

    def test_report_language_explicit_parameter(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "t", "scope_description": "S"})
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            quality="passed",
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
            quality="passed",
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
            quality="passed",
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
                "content": "Content.",
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
            quality="passed",
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


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
