from __future__ import annotations

from pathlib import Path

from scripts.cli import cmd_reset
from scripts.proceed import detect_current_phase

import argparse


def _make_args(phase: str, workdir=None) -> argparse.Namespace:
    ns = argparse.Namespace(phase=phase)
    if workdir is not None:
        ns._workdir = workdir
    return ns


class TestResetScope:
    def test_removes_all_artifacts(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        (tmp_path / "review_report.md").write_text("review")
        cmd_reset(_make_args("scope", workdir=tmp_path))
        assert not (tmp_path / "scope.json").exists()
        assert not (tmp_path / "collected.json").exists()
        assert not (tmp_path / "analysis.json").exists()
        assert not (tmp_path / "review_report.md").exists()

    def test_phase_after_reset(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        cmd_reset(_make_args("scope", workdir=tmp_path))
        assert detect_current_phase(tmp_path) == "pre_scope"


class TestResetSearch:
    def test_removes_collected_and_after(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        (tmp_path / "review_report.md").write_text("review")
        cmd_reset(_make_args("search", workdir=tmp_path))
        assert (tmp_path / "scope.json").exists()
        assert not (tmp_path / "collected.json").exists()
        assert not (tmp_path / "analysis.json").exists()
        assert not (tmp_path / "review_report.md").exists()

    def test_phase_after_reset(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        cmd_reset(_make_args("search", workdir=tmp_path))
        assert detect_current_phase(tmp_path) == "post_scope"


class TestResetAnalysis:
    def test_removes_analysis_and_after(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        (tmp_path / "review_report.md").write_text("review")
        cmd_reset(_make_args("analysis", workdir=tmp_path))
        assert (tmp_path / "scope.json").exists()
        assert (tmp_path / "collected.json").exists()
        assert not (tmp_path / "analysis.json").exists()
        assert not (tmp_path / "review_report.md").exists()

    def test_phase_after_reset(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        cmd_reset(_make_args("analysis", workdir=tmp_path))
        assert detect_current_phase(tmp_path) == "post_search"


class TestResetReview:
    def test_removes_only_review(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        (tmp_path / "review_report.md").write_text("review")
        cmd_reset(_make_args("review", workdir=tmp_path))
        assert (tmp_path / "scope.json").exists()
        assert (tmp_path / "collected.json").exists()
        assert (tmp_path / "analysis.json").exists()
        assert not (tmp_path / "review_report.md").exists()

    def test_phase_after_reset(self, tmp_path, monkeypatch):
        _write_json(tmp_path / "scope.json", {"topic": "test"})
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "test", "sections": []})
        (tmp_path / "review_report.md").write_text("review")
        cmd_reset(_make_args("review", workdir=tmp_path))
        assert detect_current_phase(tmp_path) == "post_analysis"


class TestResetNothingToRemove:
    def test_no_error_when_nothing_exists(self, tmp_path, monkeypatch):
        tmp_path.mkdir(parents=True, exist_ok=True)
        cmd_reset(_make_args("scope", workdir=tmp_path))


class TestResetInvalidPhase:
    def test_invalid_phase_exits(self, tmp_path, monkeypatch):
        tmp_path.mkdir(parents=True, exist_ok=True)
        try:
            cmd_reset(_make_args("invalid", workdir=tmp_path))
        except SystemExit as e:
            assert e.code == 1
