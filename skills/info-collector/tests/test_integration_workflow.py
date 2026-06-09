"""End-to-end workflow tests for the complete research pipeline."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cmd(cmd, cwd=None):
    """Helper to run a command and return result."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    return result


class TestFullWorkflowPipeline:
    """End-to-end tests for the complete research workflow."""

    def test_scope_to_report_full_pipeline(self, tmp_path, monkeypatch):
        """Complete pipeline: scope.json → research → report."""
        # Set up isolated skill directory
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        # Phase 1: Create valid scope.json
        scope = {
            "topic": "Rust Async Programming",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "days",
            },
        }
        scope_file = skill_dir / "scope.json"
        scope_file.write_text(json.dumps(scope, indent=2))

        # Validate scope via CLI
        from research import cmd_validate_scope
        from argparse import Namespace

        args = Namespace(scope_json=str(scope_file))
        # Should not raise
        cmd_validate_scope(args)

        # Phase 2: Simulate collected.json (normally from search/collect)
        collected = {
            "topic": "Rust Async Programming",
            "sources": [
                {
                    "url": "https://rust-lang.org/async-book",
                    "title": "Async Rust Book",
                    "source_type": "web",
                    "source_lang": "en",
                    "content": "Async Rust allows concurrent operations...",
                },
                {
                    "url": "https://docs.rs/tokio",
                    "title": "Tokio Runtime",
                    "source_type": "web",
                    "source_lang": "en",
                    "content": "Tokio is a runtime for writing reliable async applications...",
                },
            ],
        }
        (skill_dir / "collected.json").write_text(json.dumps(collected, indent=2))

        # Phase 3: Create analysis.json (normally from human analysis)
        analysis = {
            "topic": "Rust Async Programming",
            "depth": "standard",
            "lang": "en",
            "sections": [
                {
                    "id": "summary",
                    "title": "Summary",
                    "content": "Rust's async programming model is built on futures and async/await syntax.",
                },
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "The async ecosystem in Rust centers around the Future trait and runtimes like Tokio.",
                },
            ],
            "sources": collected["sources"],
        }
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis, indent=2))

        # Phase 4: Generate report via CLI
        from research import cmd_generate

        output_dir = tmp_path / "reports"
        args = Namespace(
            analysis_json=str(analysis_file),
            template="standard",
            no_validate=False,
            output_dir=str(output_dir),
            draft=False,
        )
        cmd_generate(args)

        # Verify report was created
        reports = list(output_dir.glob("*.md"))
        assert len(reports) == 1, f"Expected 1 report, got {len(reports)}"

        report = reports[0].read_text()
        assert "Rust Async Programming" in report
        assert "## Summary" in report or "# Summary" in report
        assert "## Overview" in report or "# Overview" in report
        assert "Async Rust" in report

    def test_workflow_with_filter_and_generate(self, tmp_path, monkeypatch):
        """Test filter → generate workflow with duplicate URLs."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        # Create collected.json with duplicate URLs (different forms)
        collected = {
            "sources": [
                {"url": "https://www.example.com/page", "title": "Page 1"},
                {"url": "https://example.com/page/", "title": "Page 2"},  # duplicate
                {"url": "https://EXAMPLE.com/PAGE", "title": "Page 3"},  # duplicate
                {"url": "https://other.com", "title": "Other"},
            ]
        }
        (skill_dir / "collected.json").write_text(json.dumps(collected))

        # Run filter command
        from research import cmd_filter
        from argparse import Namespace

        cmd_filter(Namespace())

        # Verify duplicates were marked
        filtered = json.loads((skill_dir / "collected.json").read_text())
        sources = filtered["sources"]

        # First occurrence should have no duplicate_of
        assert sources[0].get("duplicate_of") is None
        # Others should be marked as duplicates
        assert sources[1].get("duplicate_of") == "https://www.example.com/page"
        assert sources[2].get("duplicate_of") == "https://www.example.com/page"
        assert sources[3].get("duplicate_of") is None

    def test_workflow_config_lifecycle(self, tmp_path, monkeypatch):
        """Test init-config → show-config workflow."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        from research import cmd_init_config, cmd_show_config
        from argparse import Namespace
        import io
        from contextlib import redirect_stdout

        # Initialize config
        args = Namespace(output_dir="my_reports", lang="en")
        cmd_init_config(args)

        config_file = skill_dir / "config.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert config["output_dir"] == "my_reports"
        assert config["lang"] == "en"

        # Show config (capture output)
        f = io.StringIO()
        with redirect_stdout(f):
            cmd_show_config(Namespace())
        output = f.getvalue()

        assert "my_reports" in output
        assert "en" in output

    def test_workflow_clean_removes_workfiles(self, tmp_path, monkeypatch):
        """Test clean command removes workfiles."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        # Create workfiles
        (skill_dir / "scope.json").write_text('{"topic": "test"}')
        (skill_dir / "collected.json").write_text('{"sources": []}')
        (skill_dir / "analysis.json").write_text('{"topic": "test"}')

        from research import cmd_clean
        from argparse import Namespace
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            cmd_clean(Namespace())

        # Verify files removed
        assert not (skill_dir / "scope.json").exists()
        assert not (skill_dir / "collected.json").exists()
        assert not (skill_dir / "analysis.json").exists()

        output = f.getvalue()
        assert "Cleaned up" in output or "scope.json" in output

    def test_subprocess_full_cli_workflow(self, tmp_path):
        """Test full workflow using subprocess CLI calls."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()

        # Copy research.py and scripts to temp location
        import shutil
        orig_skill_dir = Path(__file__).resolve().parent.parent
        shutil.copytree(orig_skill_dir / "scripts", skill_dir / "scripts")
        shutil.copy(orig_skill_dir / "research.py", skill_dir / "research.py")

        # Create scope.json
        scope = {
            "topic": "Test CLI",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "days",
            },
        }
        (skill_dir / "scope.json").write_text(json.dumps(scope))

        # Run validate-scope via subprocess
        result = subprocess.run(
            [sys.executable, "research.py", "validate-scope", "scope.json"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Validation failed: {result.stderr}"

        # Create analysis.json
        analysis = {
            "topic": "Test CLI",
            "depth": "standard",
            "lang": "en",
            "sections": [
                {"id": "summary", "title": "Summary", "content": "Test content"}
            ],
        }
        (skill_dir / "analysis.json").write_text(json.dumps(analysis))

        # Run generate
        result = subprocess.run(
            [
                sys.executable,
                "research.py",
                "generate",
                "analysis.json",
                "--output-dir",
                str(skill_dir / "output"),
            ],
            cwd=skill_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Generate failed: {result.stderr}"

        # Verify report
        reports = list((skill_dir / "output").glob("*.md"))
        assert len(reports) == 1
        content = reports[0].read_text()
        assert "Test CLI" in content

    def test_workflow_with_missing_config_uses_defaults(self, tmp_path, monkeypatch):
        """Test that missing config falls back to defaults."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        # No config.json exists

        # Create analysis.json
        analysis = {
            "topic": "Test Defaults",
            "depth": "standard",
            "lang": "en",
            "sections": [{"id": "summary", "title": "S", "content": "..."}],
        }
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        from research import cmd_generate
        from argparse import Namespace

        output_dir = tmp_path / "reports"
        args = Namespace(
            analysis_json=str(analysis_file),
            template="standard",
            no_validate=False,
            output_dir=str(output_dir),
            draft=False,
        )
        # Should work even without config
        cmd_generate(args)

        reports = list(output_dir.glob("*.md"))
        assert len(reports) == 1


class TestWorkflowErrorHandling:
    """Test error handling in workflow."""

    def test_invalid_scope_stops_pipeline(self, tmp_path, monkeypatch):
        """Invalid scope should fail validation."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        scope = {"topic": "Test"}  # Missing standardized
        scope_file = skill_dir / "scope.json"
        scope_file.write_text(json.dumps(scope))

        from research import cmd_validate_scope
        from argparse import Namespace

        args = Namespace(scope_json=str(scope_file))
        with pytest.raises(SystemExit):
            cmd_validate_scope(args)

    def test_invalid_analysis_stops_generation(self, tmp_path, monkeypatch):
        """Invalid analysis should fail validation."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        analysis = {"topic": "Test"}  # Missing depth, sections
        analysis_file = tmp_path / "analysis.json"
        analysis_file.write_text(json.dumps(analysis))

        from research import cmd_generate
        from argparse import Namespace

        args = Namespace(
            analysis_json=str(analysis_file),
            template="standard",
            no_validate=False,
            output_dir=None,
            draft=False,
        )
        with pytest.raises(SystemExit):
            cmd_generate(args)

    def test_filter_with_no_sources(self, tmp_path, monkeypatch):
        """Filter should handle empty collected.json gracefully."""
        skill_dir = tmp_path / "info-collector"
        skill_dir.mkdir()
        monkeypatch.setattr("research._SKILL_DIR", skill_dir)

        (skill_dir / "collected.json").write_text(json.dumps({"sources": []}))

        from research import cmd_filter
        from argparse import Namespace
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            cmd_filter(Namespace())

        output = f.getvalue()
        assert "No sources to filter" in output
