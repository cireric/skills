"""Tests for info-collector CLI cmd_* functions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.cli import cmd_clean, cmd_gateway, cmd_proceed, cmd_report, cmd_source, main, WORKDIR
from scripts.lib.exceptions import InfoCollectorError


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_namespace(**kwargs):
    return argparse.Namespace(**kwargs)


class TestCmdProceed:
    def test_scope_gate_pass(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(
            workdir / "scope.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "depth": "standard",
                "audience": "engineer",
                "scope_description": "Test scope",
                "search_directions": ["AI"],
            },
        )
        with patch("scripts.cli.WORKDIR", workdir), patch("sys.exit") as mock_exit:
            cmd_proceed(_make_namespace(from_phase="scope", to_phase="search"))
            mock_exit.assert_called_with(0)

    def test_scope_gate_fail(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(workdir / "scope.json", {"topic": "T"})
        with patch("scripts.cli.WORKDIR", workdir), patch("sys.exit") as mock_exit:
            cmd_proceed(_make_namespace(from_phase="scope", to_phase="search"))
            mock_exit.assert_called_with(1)


class TestCmdGateway:
    def test_gateway_with_full_data(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(
            workdir / "scope.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "depth": "standard",
                "audience": "engineer",
                "scope_description": "Test scope",
                "search_directions": ["AI"],
            },
        )
        _write_json(
            workdir / "collected.json",
            [
                {"url": "https://a.com", "title": "AI", "snippet": "About AI"},
            ],
        )
        _write_json(
            workdir / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently.",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "methodology",
                        "title": "Method",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        with patch("scripts.cli.WORKDIR", workdir), patch("sys.exit") as mock_exit:
            cmd_gateway(_make_namespace(command="gateway"))
            mock_exit.assert_not_called()


class TestCmdReport:
    def test_report_generation(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(
            workdir / "scope.json",
            {
                "topic": "Test Topic",
                "goal_type": "tech_selection",
                "depth": "standard",
                "audience": "engineer",
                "scope_description": "Test",
                "search_directions": ["AI"],
            },
        )
        _write_json(
            workdir / "collected.json",
            [{"url": "https://a.com", "title": "AI", "snippet": "About AI"}],
        )
        _write_json(
            workdir / "analysis.json",
            {
                "topic": "Test Topic",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "C",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"text": "T", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "methodology",
                        "title": "Method",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        output_dir = tmp_path / "reports"
        with patch("scripts.cli.WORKDIR", workdir), patch("sys.exit"):
            cmd_report(
                _make_namespace(
                    quality="passed",
                    search_rounds=1,
                    source_count=1,
                    version=1,
                    parent=None,
                    output=str(output_dir),
                )
            )
        report_files = list(output_dir.glob("*.md"))
        assert len(report_files) >= 1
        content = report_files[0].read_text(encoding="utf-8")
        assert "topic:" in content
        assert "goal_type: tech_selection" in content

    def test_report_missing_analysis(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(
            workdir / "scope.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "depth": "standard",
                "audience": "engineer",
                "scope_description": "Test",
                "search_directions": ["AI"],
            },
        )
        with patch("scripts.cli.WORKDIR", workdir), patch("scripts.cli.sys.exit") as mock_exit:
            with patch("scripts.reporter.generate_report", return_value=""):
                cmd_report(
                    _make_namespace(
                        quality="passed",
                        search_rounds=1,
                        source_count=1,
                        version=1,
                        parent=None,
                        output=None,
                    )
                )
                mock_exit.assert_called_with(1)


class TestCmdSource:
    def test_source_recommendation(self, capsys):
        with patch("sys.exit"):
            cmd_source(_make_namespace(goal_type="tech_selection"))
        captured = capsys.readouterr()
        assert "entry_tier" in captured.out


class TestCmdClean:
    def test_clean_existing_workdir(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "dummy.txt").write_text("data")
        with patch("scripts.cli.WORKDIR", workdir):
            cmd_clean(_make_namespace())
        assert not workdir.exists()

    def test_clean_nonexistent_workdir(self, tmp_path):
        workdir = tmp_path / ".workdir"
        with patch("scripts.cli.WORKDIR", workdir):
            cmd_clean(_make_namespace())
        assert not workdir.exists()


class TestProjectRootDetection:
    def test_find_project_root_finds_git(self, tmp_path):
        from scripts.cli import _find_project_root

        (tmp_path / ".git").mkdir()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            assert _find_project_root() == tmp_path

    def test_find_project_root_walks_up(self, tmp_path):
        from scripts.cli import _find_project_root

        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "skills" / "info-collector"
        subdir.mkdir(parents=True)
        with patch("pathlib.Path.cwd", return_value=subdir):
            assert _find_project_root() == tmp_path

    def test_find_project_root_fallback_to_cwd(self, tmp_path):
        from scripts.cli import _find_project_root

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            assert _find_project_root() == tmp_path


class TestMain:
    def test_catches_info_collector_error(self, monkeypatch):
        def _raise_error(*_args, **_kwargs):
            raise InfoCollectorError("something went wrong")

        monkeypatch.setattr("scripts.cli.cmd_proceed", _raise_error)
        monkeypatch.setattr("sys.argv", ["prog", "proceed", "--from", "scope", "--to", "search"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
