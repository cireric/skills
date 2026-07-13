"""Tests for info-collector CLI cmd_* functions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.cli import _detect_review_status, _build_report_filename, cmd_clean, cmd_gateway, cmd_proceed, cmd_report, cmd_reset, cmd_source, cmd_fetch, main, _resolve_workdir
from scripts.fetcher import FetchResult
from scripts.lib.exceptions import InfoCollectorError
from scripts.lib.utils import compute_url_hash


def _make_namespace(**kwargs):
    return argparse.Namespace(**kwargs)


class TestDetectReviewStatus:
    def test_verdict_pass(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass**\n", encoding="utf-8"
        )
        assert _detect_review_status(workdir) == "passed"

    def test_verdict_pass_with_issues(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass_with_issues**\n", encoding="utf-8"
        )
        assert _detect_review_status(workdir) == "degraded"

    def test_verdict_fail_exits(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**fail**\n", encoding="utf-8"
        )
        with pytest.raises(SystemExit) as exc:
            _detect_review_status(workdir)
        assert exc.value.code == 1

    def test_verdict_unparseable_fallback(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**unknown_verdict**\n", encoding="utf-8"
        )
        assert _detect_review_status(workdir) == "degraded"

    def test_no_review_report(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        assert _detect_review_status(workdir) == "degraded"


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
        with patch("sys.exit") as mock_exit:
            cmd_proceed(_make_namespace(from_phase="scope", to_phase="search", _workdir=workdir))
            mock_exit.assert_called_with(0)

    def test_scope_gate_fail(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(workdir / "scope.json", {"topic": "T"})
        with patch("sys.exit") as mock_exit:
            cmd_proceed(_make_namespace(from_phase="scope", to_phase="search", _workdir=workdir))
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
                {"url": "https://a.com", "title": "AI", "snippet": "About AI", "source_file": f"sources/{compute_url_hash('https://a.com')}.md"},
            ],
        )
        sources_dir = workdir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        (sources_dir / f"{compute_url_hash('https://a.com')}.md").write_text("x" * 2100, encoding="utf-8")
        _write_json(
            workdir / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration {{ref:https://a.com}}.",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility {{ref:https://a.com}}.",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
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
        for sec_id in ["overview", "comparison", "recommendation", "methodology"]:
            _write_json(workdir / f"analysis_section_{sec_id}.json", {"id": sec_id})
        with patch("sys.exit") as mock_exit:
            cmd_gateway(_make_namespace(command="gateway", _workdir=workdir))
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
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
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
        with patch("sys.exit"):
            cmd_report(
                _make_namespace(
                    review_status="passed",
                    search_rounds=1,
                    source_count=1,
                    output=str(output_dir),
                    _workdir=workdir,
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
        with patch("scripts.cli.sys.exit") as mock_exit:
            with patch("scripts.reporter.generate_report", return_value=""):
                cmd_report(
                    _make_namespace(
                        review_status="passed",
                        search_rounds=1,
                        source_count=1,
                        output=None,
                        _workdir=workdir,
                    )
                )
                mock_exit.assert_called_with(1)

    def test_report_cjk_topic_uses_english_title(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(
            workdir / "scope.json",
            {
                "topic": "智能体编程趋势",
                "english_title": "agentic coding trends",
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
                "topic": "智能体编程趋势",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "C",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"summary": "T", "sources": ["https://a.com"]}],
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
        with patch("sys.exit"):
            cmd_report(
                _make_namespace(
                    review_status="passed",
                    search_rounds=1,
                    source_count=1,
                    output=str(output_dir),
                    _workdir=workdir,
                )
            )
        report_files = list(output_dir.glob("*.md"))
        assert len(report_files) >= 1
        filename = report_files[0].name
        assert not any('\u4e00' <= c <= '\u9fff' for c in filename)
        assert "agentic_coding_trends" in filename


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
        cmd_clean(_make_namespace(_workdir=workdir))
        assert not workdir.exists()

    def test_clean_nonexistent_workdir(self, tmp_path):
        workdir = tmp_path / ".workdir"
        cmd_clean(_make_namespace(_workdir=workdir))
        assert not workdir.exists()


class TestProjectRootDetection:
    def test_find_project_root_finds_git(self, tmp_path):
        from scripts.lib.utils import find_project_root

        (tmp_path / ".git").mkdir()
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            assert find_project_root() == tmp_path

    def test_find_project_root_walks_up(self, tmp_path):
        from scripts.lib.utils import find_project_root

        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "skills" / "info-collector"
        subdir.mkdir(parents=True)
        with patch("pathlib.Path.cwd", return_value=subdir):
            assert find_project_root() == tmp_path

    def test_find_project_root_fallback_to_cwd(self, tmp_path):
        from scripts.lib.utils import find_project_root

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            assert find_project_root() == tmp_path


class TestCmdReset:
    def test_reset_scope_removes_all(self, tmp_path, monkeypatch):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(workdir / "scope.json", {"topic": "test"})
        _write_json(workdir / "collected.json", [{"url": "https://a.com"}])
        _write_json(workdir / "analysis.json", {"topic": "test", "sections": []})
        (workdir / "review_report.md").write_text("review")
        cmd_reset(_make_namespace(phase="scope", _workdir=workdir))
        assert not (workdir / "scope.json").exists()
        assert not (workdir / "collected.json").exists()
        assert not (workdir / "analysis.json").exists()
        assert not (workdir / "review_report.md").exists()

    def test_reset_analysis_preserves_scope_and_collected(self, tmp_path, monkeypatch):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        _write_json(workdir / "scope.json", {"topic": "test"})
        _write_json(workdir / "collected.json", [{"url": "https://a.com"}])
        _write_json(workdir / "analysis.json", {"topic": "test", "sections": []})
        cmd_reset(_make_namespace(phase="analysis", _workdir=workdir))
        assert (workdir / "scope.json").exists()
        assert (workdir / "collected.json").exists()
        assert not (workdir / "analysis.json").exists()

    def test_reset_invalid_phase_exits(self, tmp_path, monkeypatch):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        with pytest.raises(SystemExit) as exc_info:
            cmd_reset(_make_namespace(phase="invalid", _workdir=workdir))
        assert exc_info.value.code == 1

    def test_main_parses_reset(self, monkeypatch):
        called = []
        monkeypatch.setattr("scripts.cli.cmd_reset", lambda args: called.append(args))
        monkeypatch.setattr("sys.argv", ["prog", "reset", "--phase", "scope"])
        main()
        assert len(called) == 1
        assert called[0].phase == "scope"


class TestBuildReportFilename:
    def test_ascii_topic_no_english_title(self, tmp_path):
        scope_data = {"topic": "agentic coding trends"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert result.name == "agentic_coding_trends.md"

    def test_cjk_topic_uses_english_title(self, tmp_path):
        scope_data = {"topic": "智能体编程趋势", "english_title": "agentic coding trends"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert result.name == "agentic_coding_trends.md"

    def test_cjk_topic_without_english_title_falls_back(self, tmp_path):
        scope_data = {"topic": "智能体编程趋势"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert result.name == "untitled.md"

    def test_mixed_topic_without_english_title_keeps_ascii(self, tmp_path):
        scope_data = {"topic": "2026 AI 趋势"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert result.name == "2026_ai.md"

    def test_date_suffix_when_file_exists(self, tmp_path):
        scope_data = {"topic": "test topic"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        (output_path / "test_topic.md").write_text("old report", encoding="utf-8")
        result = _build_report_filename(scope_data, output_path)
        assert "test_topic_" in result.name
        assert result.name.endswith(".md")

    def test_no_date_suffix_when_file_not_exists(self, tmp_path):
        scope_data = {"topic": "test topic"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert result.name == "test_topic.md"

    def test_special_chars_sanitized(self, tmp_path):
        scope_data = {"topic": "AI/ML: Frameworks & Tools!"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert "/" not in result.name
        assert "!" not in result.name
        assert "&" not in result.name

    def test_consecutive_underscores_collapsed(self, tmp_path):
        scope_data = {"topic": "AI   ML   Frameworks"}
        output_path = tmp_path / "reports"
        output_path.mkdir()
        result = _build_report_filename(scope_data, output_path)
        assert "__" not in result.name


class TestMain:
    def test_catches_info_collector_error(self, monkeypatch):
        def _raise_error(*_args, **_kwargs):
            raise InfoCollectorError("something went wrong")

        monkeypatch.setattr("scripts.cli.cmd_proceed", _raise_error)
        monkeypatch.setattr("sys.argv", ["prog", "proceed", "--from", "scope", "--to", "search"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


class TestCmdFetch:
    def test_fetch_autonomous_success(self, tmp_path, capsys):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        (workdir / "sources").mkdir()
        mock_result = FetchResult(
            url="https://example.com/paper", actual_url="https://example.com/paper",
            source_file="sources/abc123.md", url_hash="abc123def456",
            char_count=5000, fetched_content="# Title",
            fetch_failed=False, tool_used="webfetch",
            content_insufficient=False, source_tier=None,
        )
        with patch("scripts.fetcher.Fetcher") as MockFetcher:
            MockFetcher.return_value.fetch.return_value = mock_result
            args = _make_namespace(url="https://example.com/paper", tier=None, no_playwright=False, from_stdin=False, _workdir=workdir)
            cmd_fetch(args)
        output = json.loads(capsys.readouterr().out)
        assert output["fetch_failed"] is False
        assert output["source_file"] == "sources/abc123.md"

    def test_fetch_failed_exits_1(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        mock_result = FetchResult(
            url="https://example.com/404", actual_url="https://example.com/404",
            source_file=None, url_hash="abc123def456",
            char_count=0, fetched_content="",
            fetch_failed=True, tool_used="",
            content_insufficient=True, source_tier=None,
        )
        with patch("scripts.fetcher.Fetcher") as MockFetcher:
            MockFetcher.return_value.fetch.return_value = mock_result
            args = _make_namespace(url="https://example.com/404", tier=None, no_playwright=False, from_stdin=False, _workdir=workdir)
            with pytest.raises(SystemExit) as exc:
                cmd_fetch(args)
            assert exc.value.code == 1

    def test_fetch_from_stdin_passes_raw_to_save_piped(self, tmp_path, capsys):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        mock_result = FetchResult(
            url="https://example.com/paper", actual_url="https://example.com/paper",
            source_file="sources/abc123.md", url_hash="abc123def456",
            char_count=5000, fetched_content="# Title",
            fetch_failed=False, tool_used="exa_web_fetch_exa",
            content_insufficient=False, source_tier=1,
        )
        stdin_content = '{"content": "# Paper\\n\\ncontent", "tool_used": "exa_web_fetch_exa"}'
        with patch("scripts.fetcher.Fetcher") as MockFetcher, \
             patch("sys.stdin.read", return_value=stdin_content):
            MockFetcher.return_value.save_piped.return_value = mock_result
            args = _make_namespace(url="https://example.com/paper", tier=1, no_playwright=False, from_stdin=True, _workdir=workdir)
            cmd_fetch(args)
        call_args = MockFetcher.return_value.save_piped.call_args
        assert call_args[0][1] == stdin_content

    def test_fetch_auto_infers_tier_when_none(self, tmp_path, capsys):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        mock_result = FetchResult(
            url="https://arxiv.org/abs/2503.15223", actual_url="https://ar5iv.labs.arxiv.org/html/2503.15223",
            source_file="sources/abc123.md", url_hash="abc123def456",
            char_count=5000, fetched_content="# Title",
            fetch_failed=False, tool_used="webfetch",
            content_insufficient=False, source_tier=1,
        )
        with patch("scripts.fetcher.Fetcher") as MockFetcher:
            MockFetcher.return_value.infer_tier.return_value = 1
            MockFetcher.return_value.fetch.return_value = mock_result
            args = _make_namespace(url="https://arxiv.org/abs/2503.15223", tier=None, no_playwright=False, from_stdin=False, _workdir=workdir)
            cmd_fetch(args)
        MockFetcher.return_value.fetch.assert_called_once()
        assert MockFetcher.return_value.fetch.call_args[1]["tier"] == 1
