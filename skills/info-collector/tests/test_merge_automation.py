"""Tests for merge automation + URL consistency check (ADR 0054)."""

from __future__ import annotations

import json

import pytest

from scripts.proceed import _merge_section_files, _check_url_consistency


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
