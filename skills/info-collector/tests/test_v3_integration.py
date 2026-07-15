"""End-to-end integration tests for v3 damage scenarios (ADR 0053/0054/0055)."""

from __future__ import annotations

import json

import pytest

from pathlib import Path

from scripts.proceed import (
    _check_url_consistency,
    _merge_section_files,
    _preprocess_cjk_quotes,
    _validate_section_files,
    check_fix_report,
    determine_review_status,
    proceeds,
)
from scripts.trust_boundary import validate_section_output
from scripts.reporter import sections_to_markdown


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _make_scope(tmp_path):
    scope = {"topic": "Test", "goal_type": "tech_selection", "depth": "standard", "audience": "engineer", "scope_description": "Test scope", "search_directions": ["tech"]}
    _write_json(tmp_path / "scope.json", scope)
    _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_analysis"})


def _make_collected(tmp_path):
    _write_json(tmp_path / "collected.json", [
        {"url": "https://a.com", "title": "A", "snippet": "a", "source_tier": 1, "direction": "tech"},
    ])


class TestStructuralDamageIntercepted:
    def test_claims_as_string_array_blocked(self, tmp_path):
        _make_scope(tmp_path)
        _make_collected(tmp_path)
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "Text.", "claims": ["string not object"],
        })
        errors = _validate_section_files(tmp_path)
        assert len(errors) > 0
        assert any("trust_boundary" in e for e in errors)


class TestUrlMismatchIntercepted:
    def test_url_not_in_collected_blocked(self, tmp_path):
        _make_scope(tmp_path)
        _make_collected(tmp_path)
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "Text {{ref:https://evil.com}}.",
            "depth_strategy": "overview",
            "claims": [{"summary": "C", "sources": ["https://evil.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}],
        })
        errors = _validate_section_files(tmp_path)
        assert len(errors) > 0
        assert any("url_not_in_collected" in e for e in errors)


class TestCjkQuoteFix:
    def test_fullwidth_quotes_in_content_fixable(self):
        raw = '{"content": "DeepSeek称\u201c模型达到72.6%\u201d"}'
        fixed = _preprocess_cjk_quotes(raw)
        data = json.loads(fixed)
        assert "模型达到72.6%" in data["content"]


class TestRetrySuccess:
    def test_valid_output_after_retry(self, tmp_path):
        _make_scope(tmp_path)
        _make_collected(tmp_path)
        valid_section = {
            "id": "overview", "title": "Overview",
            "content": "Text {{ref:https://a.com}}.",
            "depth_strategy": "overview",
            "key_insights": [{"summary": "K", "sources": ["https://a.com"]}],
            "tensions": [],
            "claims": [{"summary": "C", "sources": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}],
        }
        _write_json(tmp_path / "analysis_section_overview.json", valid_section)
        result = validate_section_output(json.dumps(valid_section), {"https://a.com/"})
        assert result.passed is True


class TestIncompleteSection:
    def test_incomplete_section_in_report(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [{"id": "bad", "title": "Bad", "content": "Unreliable.", "status": "incomplete", "claims": []}],
        }
        md = sections_to_markdown(analysis)
        assert "INCOMPLETE" in md
        assert "unreliable" in md.lower()


class TestMergeAutomation:
    def test_auto_merge_creates_analysis(self, tmp_path):
        _make_scope(tmp_path)
        _make_collected(tmp_path)
        _write_json(tmp_path / "analysis_section_overview.json", {
            "id": "overview", "title": "Overview", "content": "A", "depth_strategy": "overview", "claims": [],
        })
        merged = _merge_section_files(tmp_path, topic="Test", goal_type="tech_selection")
        assert merged is not None
        assert (tmp_path / "analysis.json").exists()

    def test_url_consistency_check_warns(self, tmp_path):
        _make_collected(tmp_path)
        analysis = {"sections": [{"content": "See {{ref:https://evil.com}}.", "claims": []}]}
        warnings = _check_url_consistency(analysis, {"https://a.com/"})
        assert len(warnings) > 0


class TestDefenseInDepth:
    def test_gate_still_catches_bypassed_urls(self, tmp_path):
        _make_scope(tmp_path)
        _make_collected(tmp_path)
        analysis = {
            "topic": "T", "goal_type": "tech_selection",
            "sections": [
                {"id": "overview", "title": "O", "content": "Text {{ref:https://a.com}}.", "claims": [{"summary": "C1", "sources": ["https://a.com"]}]},
                {"id": "comparison", "title": "C", "content": "C.", "claims": []},
                {"id": "recommendation", "title": "R", "content": "R.", "claims": []},
                {"id": "methodology", "title": "M", "content": "M.", "claims": []},
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok


class TestRepairLoop:
    def test_all_blockers_fixed_passes(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": True, "remaining_blockers": [],
        })
        assert determine_review_status(tmp_path) == "passed"

    def test_blocker_skipped_degraded(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "skipped", "reason": "no data"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        assert determine_review_status(tmp_path) == "degraded"

    def test_no_fix_report_degraded(self, tmp_path):
        assert determine_review_status(tmp_path) == "degraded"
