"""Tests for repair loop integration (ADR 0055)."""

from __future__ import annotations

import json

import pytest

from pathlib import Path

from scripts.repair_loop import check_fix_report, determine_review_status


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestCheckFixReport:
    def test_all_fixed(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
            {"issue_id": 2, "status": "fixed"},
        ])
        result = check_fix_report(tmp_path)
        assert result["blocker_fixed"] == 2
        assert result["blocker_skipped"] == 0
        assert result["warn_skipped"] == 0

    def test_blocker_skipped(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
            {"issue_id": 2, "status": "skipped", "reason": "no data"},
        ])
        fix_list = [
            {"issue_id": 1, "severity": "BLOCKER"},
            {"issue_id": 2, "severity": "BLOCKER"},
        ]
        _write_json(tmp_path / "fix_list.json", fix_list)
        result = check_fix_report(tmp_path)
        assert result["blocker_skipped"] == 1

    def test_warn_skipped_does_not_affect_blocker(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
            {"issue_id": 2, "status": "skipped", "reason": "minor"},
        ])
        fix_list = [
            {"issue_id": 1, "severity": "BLOCKER"},
            {"issue_id": 2, "severity": "WARN"},
        ]
        _write_json(tmp_path / "fix_list.json", fix_list)
        result = check_fix_report(tmp_path)
        assert result["blocker_skipped"] == 0
        assert result["warn_skipped"] == 1

    def test_no_fix_report(self, tmp_path):
        result = check_fix_report(tmp_path)
        assert result is None


class TestDetermineReviewStatus:
    def test_no_fix_report_degraded(self, tmp_path):
        status = determine_review_status(tmp_path)
        assert status == "degraded"

    def test_all_blockers_fixed_passed(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": True,
            "remaining_blockers": [],
        })
        status = determine_review_status(tmp_path)
        assert status == "passed"

    def test_blocker_skipped_degraded(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "skipped", "reason": "no data"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        status = determine_review_status(tmp_path)
        assert status == "degraded"

    def test_warn_skipped_only_passed(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
            {"issue_id": 2, "status": "skipped", "reason": "minor"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
            {"issue_id": 2, "severity": "WARN"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": True,
            "remaining_blockers": [],
        })
        status = determine_review_status(tmp_path)
        assert status == "passed"

    def test_lightweight_review_found_remaining_degraded(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": False,
            "remaining_blockers": [{"issue_id": 1, "description": "not actually fixed"}],
        })
        status = determine_review_status(tmp_path)
        assert status == "degraded"

    def test_all_blockers_fixed_no_lightweight_review_passed(self, tmp_path):
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        status = determine_review_status(tmp_path)
        assert status == "passed"


class TestGateReviewRepairLoop:
    def test_blocker_skipped_blocks_final(self, tmp_path, monkeypatch):
        from scripts.lib.check_types import CheckResult

        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "skipped", "reason": "no data"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert any("repair_loop" in e and "BLOCKER" in e for e in errors)

    def test_all_fixed_passes_final(self, tmp_path, monkeypatch):
        from scripts.lib.check_types import CheckResult

        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": True,
            "remaining_blockers": [],
        })

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert errors == []

    def test_no_fix_report_degraded_does_not_block(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "fix_list.json", [])

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert errors == []

    def test_no_fix_list_blocks_when_review_report_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert any("repair_loop_not_started" in e for e in errors)

    def test_warn_skipped_does_not_block(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "fix_report.json", [
            {"issue_id": 1, "status": "fixed"},
            {"issue_id": 2, "status": "skipped", "reason": "minor"},
        ])
        _write_json(tmp_path / "fix_list.json", [
            {"issue_id": 1, "severity": "BLOCKER"},
            {"issue_id": 2, "severity": "WARN"},
        ])
        _write_json(tmp_path / "lightweight_review_result.json", {
            "all_blockers_fixed": True,
            "remaining_blockers": [],
        })

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert errors == []
        captured = capsys.readouterr()
        assert "WARN" in captured.err


class TestGateReviewReMergeAfterFix:
    def test_re_merge_triggered_when_blockers_fixed(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")

        section_data = {"id": "s1", "title": "S1", "content": "Fixed content",
                        "claims": [{"summary": "c1", "sources": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]}
        _write_json(tmp_path / "analysis_section_01.json", section_data)

        old_analysis = {"topic": "T", "goal_type": "exploratory", "sections": [{"id": "s1", "title": "S1", "content": "OLD content", "claims": []}], "_merge_completed": True}
        _write_json(tmp_path / "analysis.json", old_analysis)
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "exploratory"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s"}])

        _write_json(tmp_path / "fix_report.json", [{"issue_id": 1, "status": "fixed"}])
        _write_json(tmp_path / "fix_list.json", [{"issue_id": 1, "severity": "BLOCKER"}])
        _write_json(tmp_path / "lightweight_review_result.json", {"all_blockers_fixed": True, "remaining_blockers": []})

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert errors == []

        from scripts.lib.utils import read_json
        merged = read_json(tmp_path / "analysis.json")
        assert merged["sections"][0]["content"] == "Fixed content"

    def test_no_re_merge_when_no_fix_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "fix_list.json", [])

        old_analysis = {"topic": "T", "goal_type": "exploratory", "sections": [{"id": "s1", "title": "S1", "content": "OLD content"}], "_merge_completed": True}
        _write_json(tmp_path / "analysis.json", old_analysis)

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        assert errors == []

        from scripts.lib.utils import read_json
        analysis = read_json(tmp_path / "analysis.json")
        assert analysis["sections"][0]["content"] == "OLD content"


class TestGateReviewSelfLoop:
    def test_self_loop_blocks_without_review_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="review")
        assert any("review_report" in e.lower() for e in errors)

    def test_self_loop_passes_with_review_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: [])
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass_with_issues**\n", encoding="utf-8")

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="review")
        assert errors == []
