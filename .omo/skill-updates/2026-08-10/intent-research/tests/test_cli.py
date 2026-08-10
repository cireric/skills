import json
import pytest
from argparse import Namespace
from pathlib import Path

from scripts.cli import cmd_scope_check, cmd_fetch, cmd_verify, cmd_report
from scripts.lib.utils import write_json, read_json


class _FakeStdin:
    def __init__(self, text):
        self._text = text

    def read(self, size=-1):
        return self._text


def _scope_check_args(tmp_path):
    return Namespace(workdir=str(tmp_path))


def _fetch_args(tmp_path, from_stdin=True):
    return Namespace(workdir=str(tmp_path), from_stdin=from_stdin)


def _verify_args(tmp_path):
    return Namespace(workdir=str(tmp_path))


def _report_args(tmp_path, output_dir=None):
    return Namespace(workdir=str(tmp_path), output_dir=output_dir)


class TestCmdScopeCheck:
    def test_workdir_not_found(self, tmp_path):
        missing = tmp_path / "no_workdir"
        args = Namespace(workdir=str(missing))
        with pytest.raises(SystemExit) as exc_info:
            cmd_scope_check(args)
        assert exc_info.value.code == 1

    def test_blocker_exits_1(self, tmp_path):
        scope = {"topic": "", "goal_type": "tech_selection"}
        write_json(scope, tmp_path / "scope.json")
        with pytest.raises(SystemExit) as exc_info:
            cmd_scope_check(_scope_check_args(tmp_path))
        assert exc_info.value.code == 1

    def test_all_pass_exits_0(self, tmp_path):
        scope = {
            "topic": "Test",
            "goal_type": "tech_selection",
            "scope_description": "test",
            "search_directions": ["a"],
            "decision_questions": [{"id": "dq1", "question": "What?"}],
        }
        collected = [{"url": "http://a.com", "source_tier": 1, "direction": "a", "title": "A"}]
        analysis = {"sections": [{"id": "s1", "title": "S1", "content": "see {{ref:http://a.com}}", "claims": [
            {"summary": "a is good", "sources": ["http://a.com"], "evidence_type": "official_data", "precision": "exact"}
        ], "key_insights": [], "tensions": []}]}
        write_json(scope, tmp_path / "scope.json")
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")
        cmd_scope_check(_scope_check_args(tmp_path))


class TestCmdFetch:
    def test_from_stdin_writes_files(self, tmp_path, monkeypatch, capsys):
        import sys
        items = [{"url": "http://arxiv.org/paper1", "content": "Paper content", "tier": 1, "direction": "academic", "title": "Paper1"}]
        monkeypatch.setattr(sys, "stdin", _FakeStdin(json.dumps(items)))
        cmd_fetch(_fetch_args(tmp_path))
        collected = read_json(tmp_path / "collected.json")
        assert len(collected) == 1
        assert collected[0]["source_tier"] == 1
        assert (tmp_path / "sources").exists()
        captured = capsys.readouterr()
        assert "Fetched" in captured.out

    def test_from_stdin_auto_tier(self, tmp_path, monkeypatch, capsys):
        import sys
        items = [{"url": "http://unknown-domain.xyz/page", "content": "Content", "direction": "other"}]
        monkeypatch.setattr(sys, "stdin", _FakeStdin(json.dumps(items)))
        cmd_fetch(_fetch_args(tmp_path))
        collected = read_json(tmp_path / "collected.json")
        assert collected[0]["source_tier"] == 3

    def test_from_stdin_empty_json(self, tmp_path, monkeypatch, capsys):
        import sys
        monkeypatch.setattr(sys, "stdin", _FakeStdin(json.dumps([])))
        cmd_fetch(_fetch_args(tmp_path))
        collected = read_json(tmp_path / "collected.json")
        assert len(collected) == 0

    def test_no_from_stdin_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            cmd_fetch(_fetch_args(tmp_path, from_stdin=False))
        assert exc_info.value.code == 1

    def test_from_stdin_appends_to_existing(self, tmp_path, monkeypatch):
        import sys
        existing = [{"url": "http://a.com", "source_tier": 1, "direction": "a", "title": "A"}]
        write_json(existing, tmp_path / "collected.json")
        new_items = [{"url": "http://b.com", "content": "B content", "tier": 2, "direction": "b", "title": "B"}]
        monkeypatch.setattr(sys, "stdin", _FakeStdin(json.dumps(new_items)))
        cmd_fetch(_fetch_args(tmp_path))
        collected = read_json(tmp_path / "collected.json")
        assert len(collected) == 2

    def test_from_stdin_invalid_json(self, tmp_path, monkeypatch):
        import sys
        monkeypatch.setattr(sys, "stdin", _FakeStdin("not json"))
        with pytest.raises(SystemExit) as exc_info:
            cmd_fetch(_fetch_args(tmp_path))
        assert exc_info.value.code == 1

    def test_from_file_writes_files(self, tmp_path):
        items = [{"url": "http://arxiv.org/paper2", "content": "File content", "tier": 1, "direction": "academic", "title": "Paper2"}]
        batch_file = tmp_path / "batch.json"
        batch_file.write_text(json.dumps(items), encoding="utf-8")
        args = Namespace(workdir=str(tmp_path), from_stdin=False, from_file=str(batch_file))
        cmd_fetch(args)
        collected = read_json(tmp_path / "collected.json")
        assert len(collected) == 1
        assert collected[0]["source_tier"] == 1

    def test_from_file_missing_exits(self, tmp_path):
        args = Namespace(workdir=str(tmp_path), from_stdin=False, from_file=str(tmp_path / "nope.json"))
        with pytest.raises(SystemExit) as exc_info:
            cmd_fetch(args)
        assert exc_info.value.code == 1


class TestCmdVerify:
    def test_normal_flow(self, tmp_path, capsys):
        collected = [{"url": "http://arxiv.org/paper", "source_tier": 1, "fetched_content": "accuracy is 98%", "snippet": ""}]
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "accuracy is 98%", "sources": ["http://arxiv.org/paper"], "evidence_type": "official_data", "precision": "exact"}
        ]}]}
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")
        cmd_verify(_verify_args(tmp_path))
        captured = capsys.readouterr()
        assert "Confirmed" in captured.out

    def test_missing_files_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            cmd_verify(_verify_args(tmp_path))
        assert exc_info.value.code == 1


class TestCmdReport:
    def test_normal_flow(self, tmp_path):
        scope = {
            "topic": "Test",
            "goal_type": "tech_selection",
            "scope_description": "test",
            "audience": "engineers",
            "report_language": "en",
            "decision_questions": [{"id": "dq1", "question": "What?"}],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        analysis = {"topic": "Test", "goal_type": "tech_selection", "sections": [{
            "id": "s1", "title": "S1", "content": "X is good {{ref:http://a.com}}", "claims": [
                {"summary": "X is 98%", "sources": ["http://a.com"], "evidence_type": "official_data", "precision": "exact", "source_verification": "source_confirmed"}
            ], "decision_questions_answered": ["dq1"], "key_insights": [], "tensions": []
        }]}
        write_json(scope, tmp_path / "scope.json")
        write_json(analysis, tmp_path / "analysis.json")
        write_json(collected, tmp_path / "collected.json")
        output_dir = tmp_path / "reports"
        cmd_report(_report_args(tmp_path, output_dir=str(output_dir)))
        report_file = list(output_dir.glob("*.md"))[0]
        content = report_file.read_text(encoding="utf-8")
        assert "verification_required: true" in content
        assert "## S1" in content

    def test_missing_scope_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            cmd_report(_report_args(tmp_path))
        assert exc_info.value.code == 1

    def test_cjk_topic_uses_english_title(self, tmp_path):
        scope = {
            "topic": "测试主题",
            "english_title": "test_topic",
            "goal_type": "tech_selection",
            "scope_description": "test",
            "report_language": "zh",
        }
        analysis = {"topic": "测试主题", "goal_type": "tech_selection", "sections": []}
        write_json(scope, tmp_path / "scope.json")
        write_json(analysis, tmp_path / "analysis.json")
        output_dir = tmp_path / "reports"
        cmd_report(_report_args(tmp_path, output_dir=str(output_dir)))
        report_files = list(output_dir.glob("*.md"))
        assert len(report_files) == 1
        assert "test_topic" in report_files[0].name
