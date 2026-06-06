"""Tests for CLI command functions."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from research import (
    cmd_clean,
    cmd_collect,
    cmd_filter,
    cmd_generate,
    cmd_init_config,
    cmd_show_config,
    cmd_validate_scope,
)


class TestCmdGenerate:
    """cmd_generate() — full report generation from analysis JSON."""

    def test_generates_report_success(self, tmp_path):
        analysis = {
            "topic": "Test Topic",
            "depth": "standard",
            "lang": "en",
            "sections": [
                {"id": "summary", "title": "Summary", "content": "# Summary\nHello"}
            ],
        }
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        args = type("Args", (), {
            "analysis_json": str(analysis_file),
            "template": "standard",
            "no_validate": False,
            "output_dir": str(tmp_path / "output"),
            "draft": False,
        })()

        with patch("research._SKILL_DIR", tmp_path):
            cmd_generate(args)

        output_files = list((tmp_path / "output").glob("*.md"))
        assert len(output_files) == 1
        content = output_files[0].read_text()
        assert "Test Topic" in content
        assert "# Summary" in content

    def test_generates_draft_report(self, tmp_path):
        analysis = {
            "topic": "Test",
            "depth": "standard",
            "lang": "en",
            "sections": [{"id": "summary", "title": "S", "content": "..."}],
        }
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        args = type("Args", (), {
            "analysis_json": str(analysis_file),
            "template": "standard",
            "no_validate": False,
            "output_dir": str(tmp_path / "output"),
            "draft": True,
        })()

        with patch("research._SKILL_DIR", tmp_path):
            cmd_generate(args)

        output_files = list((tmp_path / "output").glob("*.md"))
        assert len(output_files) == 1
        content = output_files[0].read_text()
        assert "status: draft" in content

    def test_fails_on_missing_file(self, tmp_path):
        args = type("Args", (), {
            "analysis_json": str(tmp_path / "nonexistent.json"),
            "template": "standard",
            "no_validate": False,
            "output_dir": None,
            "draft": False,
        })()
        with pytest.raises(SystemExit):
            cmd_generate(args)

    def test_fails_on_invalid_json(self, tmp_path):
        analysis_file = tmp_path / "bad.json"
        analysis_file.write_text('{"topic": "Bad"')  # truncated

        args = type("Args", (), {
            "analysis_json": str(analysis_file),
            "template": "standard",
            "no_validate": False,
            "output_dir": None,
            "draft": False,
        })()
        with pytest.raises(json.JSONDecodeError):
            cmd_generate(args)

    def test_no_validate_skips_validation(self, tmp_path):
        """With --no-validate, should accept malformed input."""
        analysis_file = tmp_path / "bad.json"
        analysis_file.write_text('{"topic": "Bad"}')  # missing required fields

        args = type("Args", (), {
            "analysis_json": str(analysis_file),
            "template": "standard",
            "no_validate": True,
            "output_dir": str(tmp_path),
            "draft": False,
        })()
        with patch("research._SKILL_DIR", tmp_path):
            # Should not raise with --no-validate
            cmd_generate(args)

    def test_generates_deep_template(self, tmp_path):
        analysis = {
            "topic": "Test",
            "depth": "deep",
            "lang": "en",
            "sections": [
                {"id": "summary", "title": "Summary", "content": "..."},
                {"id": "timeline", "title": "Timeline", "content": "..."},
            ],
        }
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        args = type("Args", (), {
            "analysis_json": str(analysis_file),
            "template": "deep",
            "no_validate": False,
            "output_dir": str(tmp_path / "output"),
            "draft": False,
        })()

        with patch("research._SKILL_DIR", tmp_path):
            cmd_generate(args)

        output_files = list((tmp_path / "output").glob("*.md"))
        assert len(output_files) == 1
        content = output_files[0].read_text()
        assert "Test" in content


class TestCmdFilter:
    """cmd_filter() — URL deduplication in collected.json."""

    def test_marks_duplicates(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        collected = {
            "sources": [
                {"url": "https://example.com/page", "title": "Page 1"},
                {"url": "https://example.com/page/", "title": "Page 2"},  # duplicate
                {"url": "https://other.com", "title": "Other"},
            ]
        }
        (tmp_path / "collected.json").write_text(json.dumps(collected))

        args = type("Args", (), {})()
        cmd_filter(args)

        result = json.loads((tmp_path / "collected.json").read_text())
        sources = result["sources"]
        assert sources[0].get("duplicate_of") is None  # original kept
        assert sources[1].get("duplicate_of") == "https://example.com/page"
        assert sources[2].get("duplicate_of") is None  # unique

    def test_no_collected_json_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)
        args = type("Args", (), {})()
        with pytest.raises(SystemExit):
            cmd_filter(args)

    def test_no_sources_message(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)
        (tmp_path / "collected.json").write_text(json.dumps({"sources": []}))

        args = type("Args", (), {})()
        cmd_filter(args)

        captured = capsys.readouterr()
        assert "No sources to filter" in captured.out

    def test_duplicate_note_includes_normalized_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        collected = {
            "sources": [
                {"url": "https://WWW.EXAMPLE.COM/path", "title": "Page 1"},
                {"url": "https://example.com/path/", "title": "Page 2"},
            ]
        }
        (tmp_path / "collected.json").write_text(json.dumps(collected))

        args = type("Args", (), {})()
        cmd_filter(args)

        result = json.loads((tmp_path / "collected.json").read_text())
        dup = result["sources"][1]
        assert dup.get("duplicate_of") == "https://WWW.EXAMPLE.COM/path"
        assert "normalized" in dup.get("filter_note", "").lower()


class TestCmdValidateScope:
    """cmd_validate_scope() — scope.json validation."""

    def test_valid_scope_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        scope = {
            "topic": "Test",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "days",
            },
        }
        scope_file = tmp_path / "scope.json"
        scope_file.write_text(json.dumps(scope))

        args = type("Args", (), {"scope_json": str(scope_file)})()
        # Should not raise
        cmd_validate_scope(args)

    def test_invalid_scope_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        scope = {"topic": "Test"}  # missing standardized
        scope_file = tmp_path / "scope.json"
        scope_file.write_text(json.dumps(scope))

        args = type("Args", (), {"scope_json": str(scope_file)})()
        with pytest.raises(SystemExit):
            cmd_validate_scope(args)

    def test_missing_file_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        args = type("Args", (), {"scope_json": str(tmp_path / "nope.json")})()
        with pytest.raises(SystemExit):
            cmd_validate_scope(args)


class TestCmdInitConfig:
    """cmd_init_config() — config.json initialization."""

    def test_creates_default_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        args = type("Args", (), {
            "output_dir": "reports",
            "lang": "zh",
        })()
        cmd_init_config(args)

        config_file = tmp_path / "config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert "output_dir" in config
        assert "lang" in config

    def test_overwrites_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        existing = {"output_dir": "old", "lang": "zh"}
        (tmp_path / "config.json").write_text(json.dumps(existing))

        args = type("Args", (), {
            "output_dir": "reports",
            "lang": "zh",
        })()
        cmd_init_config(args)

        config = json.loads((tmp_path / "config.json").read_text())
        assert config["output_dir"] == "reports"  # default from args


class TestCmdShowConfig:
    """cmd_show_config() — config display."""

    def test_shows_config(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        config = {"output_dir": "docs/out", "lang": "zh"}
        (tmp_path / "config.json").write_text(json.dumps(config))

        args = type("Args", (), {})()
        cmd_show_config(args)

        captured = capsys.readouterr()
        assert "docs/out" in captured.out
        assert "zh" in captured.out


class TestCmdClean:
    """cmd_clean() — workfile cleanup."""

    def test_removes_workfiles(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        (tmp_path / "scope.json").write_text('{"topic": "test"}')
        (tmp_path / "collected.json").write_text('{"sources": []}')
        (tmp_path / "analysis.json").write_text('{"topic": "test"}')

        args = type("Args", (), {})()
        cmd_clean(args)

        assert not (tmp_path / "scope.json").exists()
        assert not (tmp_path / "collected.json").exists()
        assert not (tmp_path / "analysis.json").exists()

    def test_missing_files_ok(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        args = type("Args", (), {})()
        # Should not raise
        cmd_clean(args)

        captured = capsys.readouterr()
        # Should report nothing to clean or success


class TestCmdCollect:
    """cmd_collect() — source collection."""

    def test_collect_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("research._SKILL_DIR", tmp_path)

        args = type("Args", (), {
            "input_file": str(tmp_path / "sources.json"),
            "topic": None,
        })()

        sources = {
            "sources": [
                {"url": "https://example.com", "title": "Example", "content": "..."}
            ]
        }
        (tmp_path / "sources.json").write_text(json.dumps(sources))

        cmd_collect(args)

        collected = json.loads((tmp_path / "collected.json").read_text())
        assert len(collected["sources"]) == 1
