"""Tests for merge automation + URL consistency check (ADR 0054) + section ordering (ADR 0059)."""

from __future__ import annotations

import json

import pytest

from scripts.proceed import _merge_section_files, _check_url_consistency, _sort_sections


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestMergeSectionFiles:
    def test_merges_section_files_into_analysis(self, tmp_path):
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "A", "depth_strategy": "overview", "claims": [],
        })
        _write_json(tmp_path / "analysis_section_comparison.json", {
            "id": "comparison", "title": "Comparison", "content": "B", "depth_strategy": "comparison", "claims": [],
        })

        result = _merge_section_files(tmp_path, topic="T", goal_type="tech_selection")
        assert result["topic"] == "T"
        assert result["goal_type"] == "tech_selection"
        assert len(result["sections"]) == 2
        ids = [s["id"] for s in result["sections"]]
        assert "overview" in ids
        assert "comparison" in ids

    def test_writes_analysis_json(self, tmp_path):
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "A", "depth_strategy": "overview", "claims": [],
        })

        _merge_section_files(tmp_path, topic="T", goal_type="tech_selection")
        analysis_path = tmp_path / "analysis.json"
        assert analysis_path.exists()
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        assert len(data["sections"]) == 1

    def test_no_section_files_returns_none(self, tmp_path):
        result = _merge_section_files(tmp_path, topic="T", goal_type="tech_selection")
        assert result is None

    def test_idempotent_no_duplicate_merge(self, tmp_path):
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "A", "depth_strategy": "overview", "claims": [],
        })

        result1 = _merge_section_files(tmp_path, topic="T", goal_type="tech_selection")
        result2 = _merge_section_files(tmp_path, topic="T", goal_type="tech_selection")
        assert result2 is not None
        assert len(result2["sections"]) == 1


class TestCheckUrlConsistency:
    def test_all_urls_match_no_warnings(self, tmp_path):
        analysis = {
            "sections": [{
                "content": "See {{ref:https://a.com}}.",
                "claims": [{"summary": "C", "sources": ["https://a.com"]}],
            }]
        }
        collected_urls = {"https://a.com/"}
        warnings = _check_url_consistency(analysis, collected_urls)
        assert warnings == []

    def test_mismatched_url_warns(self, tmp_path):
        analysis = {
            "sections": [{
                "content": "See {{ref:https://evil.com}}.",
                "claims": [{"summary": "C", "sources": ["https://evil.com"]}],
            }]
        }
        collected_urls = {"https://a.com/"}
        warnings = _check_url_consistency(analysis, collected_urls)
        assert len(warnings) > 0

    def test_suggests_similar_urls(self, tmp_path):
        analysis = {
            "sections": [{
                "content": "See {{ref:https://groundy.com/gpt-4}}.",
                "claims": [],
            }]
        }
        collected_urls = {"https://groundy.com/gpt-4-6/"}
        warnings = _check_url_consistency(analysis, collected_urls)
        assert len(warnings) > 0
        assert any("did you mean" in w.lower() or "similar" in w.lower() for w in warnings)


class TestSortSections:
    def test_overview_comes_first_for_tech_selection(self):
        sections = [
            {"id": "comparison", "title": "Comparison", "content": "B"},
            {"id": "overview", "title": "Overview", "content": "A"},
            {"id": "recommendation", "title": "Rec", "content": "C"},
            {"id": "methodology", "title": "Method", "content": "D"},
        ]
        result = _sort_sections(sections, goal_type="tech_selection")
        ids = [s["id"] for s in result]
        assert ids == ["overview", "comparison", "recommendation", "methodology"]

    def test_overview_comes_first_for_panoramic(self):
        sections = [
            {"id": "community_evaluation", "title": "Community", "content": "E"},
            {"id": "technical_architecture", "title": "Tech", "content": "A"},
            {"id": "overview", "title": "Overview", "content": "O"},
            {"id": "reported_limitations", "title": "Limits", "content": "F"},
            {"id": "model_product_family", "title": "Models", "content": "B"},
            {"id": "open_source_strategy", "title": "OSS", "content": "C"},
        ]
        result = _sort_sections(sections, goal_type="panoramic_understanding")
        ids = [s["id"] for s in result]
        assert ids[0] == "overview"
        assert ids.index("technical_architecture") < ids.index("model_product_family")
        assert ids.index("model_product_family") < ids.index("open_source_strategy")
        assert ids.index("open_source_strategy") < ids.index("community_evaluation")
        assert ids.index("community_evaluation") < ids.index("reported_limitations")

    def test_explicit_order_overrides_required_ids(self):
        sections = [
            {"id": "overview", "title": "Overview", "content": "A", "order": 2},
            {"id": "comparison", "title": "Comparison", "content": "B", "order": 1},
        ]
        result = _sort_sections(sections, goal_type="tech_selection")
        ids = [s["id"] for s in result]
        assert ids == ["comparison", "overview"]

    def test_mixed_order_and_no_order(self):
        sections = [
            {"id": "overview", "title": "Overview", "content": "A"},
            {"id": "comparison", "title": "Comparison", "content": "B", "order": 0},
            {"id": "methodology", "title": "Method", "content": "D"},
            {"id": "recommendation", "title": "Rec", "content": "C", "order": 1},
        ]
        result = _sort_sections(sections, goal_type="tech_selection")
        ids = [s["id"] for s in result]
        assert ids[0] == "comparison"
        assert ids[1] == "recommendation"
        assert ids[2] == "overview"
        assert ids[3] == "methodology"

    def test_unknown_ids_after_known_ids(self):
        sections = [
            {"id": "custom_section", "title": "Custom", "content": "X"},
            {"id": "overview", "title": "Overview", "content": "A"},
            {"id": "another_custom", "title": "Another", "content": "Y"},
        ]
        result = _sort_sections(sections, goal_type="tech_selection")
        ids = [s["id"] for s in result]
        assert ids[0] == "overview"
        assert "custom_section" in ids[1:]
        assert "another_custom" in ids[1:]

    def test_no_goal_type_falls_back_to_id_lexicographic(self):
        sections = [
            {"id": "z_section", "title": "Z", "content": "Z"},
            {"id": "a_section", "title": "A", "content": "A"},
        ]
        result = _sort_sections(sections, goal_type="")
        ids = [s["id"] for s in result]
        assert ids == ["a_section", "z_section"]

    def test_merge_uses_sort_for_panoramic(self, tmp_path):
        _write_json(tmp_path / "analysis_section_community_evaluation.json", {
            "id": "community_evaluation", "title": "Community", "content": "E", "depth_strategy": "overview", "claims": [],
        })
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "O", "depth_strategy": "overview", "claims": [],
        })
        _write_json(tmp_path / "analysis_section_technical_architecture.json", {
            "id": "technical_architecture", "title": "Tech", "content": "A", "depth_strategy": "overview", "claims": [],
        })
        result = _merge_section_files(tmp_path, topic="T", goal_type="panoramic_understanding")
        ids = [s["id"] for s in result["sections"]]
        assert ids[0] == "overview"
        assert ids.index("technical_architecture") < ids.index("community_evaluation")

    def test_background_check_ordering(self):
        sections = [
            {"id": "reported_limitations", "title": "Limits", "content": "F"},
            {"id": "overview", "title": "Overview", "content": "O"},
            {"id": "technical_architecture", "title": "Tech", "content": "A"},
            {"id": "community_evaluation", "title": "Community", "content": "E"},
            {"id": "open_source_strategy", "title": "OSS", "content": "C"},
            {"id": "model_product_family", "title": "Models", "content": "B"},
        ]
        result = _sort_sections(sections, goal_type="background_check")
        ids = [s["id"] for s in result]
        assert ids == [
            "overview", "technical_architecture", "model_product_family",
            "open_source_strategy", "community_evaluation", "reported_limitations",
        ]
