from __future__ import annotations

import json
from pathlib import Path

from scripts.proceed import detect_current_phase, proceeds


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_scope(workdir, goal_type="tech_selection", depth="standard", report_language=None):
    data = {
        "topic": "Test",
        "goal_type": goal_type,
        "depth": depth,
        "audience": "engineer",
        "scope_description": "Test scope",
        "search_directions": ["AI", "ML"],
    }
    if report_language is not None:
        data["report_language"] = report_language
    _write_json(workdir / "scope.json", data)


class TestDetectCurrentPhase:
    def test_pre_scope(self, tmp_path):
        assert detect_current_phase(tmp_path / "nonexistent") == "pre_scope"

    def test_post_scope(self, tmp_path):
        _make_scope(tmp_path)
        assert detect_current_phase(tmp_path) == "post_scope"

    def test_post_search(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        assert detect_current_phase(tmp_path) == "post_search"

    def test_post_analysis(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        assert detect_current_phase(tmp_path) == "post_analysis"

    def test_post_draft(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        assert detect_current_phase(tmp_path) == "post_draft"

    def test_post_review(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        _write_json(tmp_path / "review_report.md", {})
        assert detect_current_phase(tmp_path) == "post_review"


class TestProceeds:
    def test_valid_scope_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_missing_fields(self, tmp_path):
        _write_json(tmp_path / "scope.json", {"topic": "T"})
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        error_text = "; ".join(errors)
        assert "goal_type" in error_text

    def test_scope_gate_with_valid_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language="zh")
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_with_empty_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language="")
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "report_language" in errors[0]

    def test_scope_gate_without_report_language(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_with_non_string_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language=123)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "report_language" in errors[0]

    def test_scope_gate_invalid_phase(self, tmp_path):
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "Phase mismatch" in errors[0]

    def test_search_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI"},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_search_gate_empty_collected(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_search_gate_topic_coverage(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://x.com", "title": "Unrelated", "snippet": "Something else"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_draft_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [{"id": "overview", "title": "O", "content": "C"}],
            },
        )
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        ok, errors = proceeds(tmp_path, "draft", "review")
        assert ok, errors

    def test_draft_gate_missing_draft(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [{"id": "overview", "title": "O", "content": "C"}],
            },
        )
        ok, errors = proceeds(tmp_path, "draft", "review")
        assert not ok

    def test_invalid_transition(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "final")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_review_gate_invokes_gateway(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "C",
                        "claims": [{"text": "C1", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"text": "C3", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        _write_json(tmp_path / "review_report.md", {})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok, errors
