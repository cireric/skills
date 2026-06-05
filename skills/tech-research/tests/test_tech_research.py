#!/usr/bin/env python3
"""Tests for tech-research skill — data structures, validation, report generation."""

import argparse
import json
import sys
from pathlib import Path

import pytest
from research import (
    _clean_workfiles,
    _find_project_root,
    parse_analysis,
    validate_analysis,
)
from scripts.config import ResearchConfig, load_config, resolve_output_path, save_config
from scripts.models import (
    SECTION_IDS_DEEP,
    SECTION_IDS_STANDARD,
    AnalysisResult,
    Comparison,
    DataPoint,
    Section,
    Source,
)
from scripts.reporter import Reporter

# ── validate_analysis ────────────────────────────────────────────────────


class TestValidateAnalysis:
    """validate_analysis() — input validation."""

    def test_valid_minimal(self):
        data = {
            "topic": "Test",
            "depth": "standard",
            "sections": [{"id": "summary", "title": "S", "content": "..."}],
        }
        assert validate_analysis(data) == []

    def test_valid_deep(self):
        data = {
            "topic": "Test",
            "depth": "deep",
            "sections": [{"id": "summary", "title": "S", "content": "..."}],
        }
        assert validate_analysis(data) == []

    def test_missing_topic(self):
        data = {"depth": "standard", "sections": []}
        errors = validate_analysis(data)
        assert any("topic" in e for e in errors)

    def test_missing_depth(self):
        data = {"topic": "Test", "sections": []}
        errors = validate_analysis(data)
        assert any("depth" in e for e in errors)

    def test_invalid_depth(self):
        data = {"topic": "Test", "depth": "ultra", "sections": []}
        errors = validate_analysis(data)
        assert any("Invalid depth" in e for e in errors)

    def test_empty_sections(self):
        data = {"topic": "Test", "depth": "standard", "sections": []}
        errors = validate_analysis(data)
        assert any("empty" in e for e in errors)

    def test_sections_not_list(self):
        data = {"topic": "Test", "depth": "standard", "sections": "foo"}
        errors = validate_analysis(data)
        assert any("list" in e for e in errors)


# ── parse_analysis ───────────────────────────────────────────────────────


class TestParseAnalysis:
    """parse_analysis() — JSON → dataclass conversion."""

    def test_minimal(self):
        data = {
            "topic": "Test",
            "lang": "zh",
            "depth": "standard",
            "sections": [{"id": "summary", "title": "摘要", "content": "## Summary"}],
        }
        result = parse_analysis(data)
        assert result.topic == "Test"
        assert result.lang == "zh"
        assert result.depth == "standard"
        assert len(result.sections) == 1
        assert result.sections[0].id == "summary"

    def test_full_structure(self):
        data = {
            "topic": "Full Test",
            "lang": "en",
            "depth": "deep",
            "summary": "Core conclusion.",
            "sources": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "source_type": "web",
                    "source_lang": "en",
                    "content": "Full text...",
                    "confidence": "high",
                }
            ],
            "sections": [
                {"id": "summary", "title": "Summary", "content": "## Summary\nContent"},
                {"id": "conclusion", "title": "Conclusion", "content": "## Conclusion\nFinal."},
            ],
            "data_points": [
                {"key": "latency", "value": "10ms", "source_url": "https://example.com"}
            ],
            "comparisons": [
                {
                    "dimension": "performance",
                    "values": {"A": "fast", "B": "slow"},
                    "winner": "A",
                }
            ],
            "contradictions": ["Source A says X, Source B says Y"],
            "timelines": [
                {"date": "2025-01", "event": "Initial release", "source_url": "https://example.com"}
            ],
        }
        result = parse_analysis(data)
        assert result.topic == "Full Test"
        assert len(result.sources) == 1
        assert result.sources[0].source_type == "web"
        assert len(result.sections) == 2
        assert len(result.data_points) == 1
        assert len(result.comparisons) == 1
        assert len(result.contradictions) == 1
        assert len(result.timelines) == 1

    def test_none_fields_get_defaults(self):
        data = {
            "topic": "Defaults",
            "depth": "standard",
            "sections": [{"id": "s", "title": "S", "content": "C"}],
        }
        result = parse_analysis(data)
        assert result.lang == "zh"
        assert result.summary == ""
        assert result.sources == []
        assert result.data_points == []
        assert result.comparisons == []
        assert result.contradictions == []
        assert result.timelines == []

    def test_missing_source_fields_get_defaults(self):
        data = {
            "topic": "Missing fields",
            "depth": "standard",
            "sections": [{"id": "s", "title": "S", "content": "C"}],
            "sources": [{"url": "https://x.com", "title": "X"}],
        }
        result = parse_analysis(data)
        assert len(result.sources) == 1
        src = result.sources[0]
        assert src.source_type == "web"
        assert src.source_lang == "en"
        assert src.content == ""
        assert src.confidence == "medium"


# ── Reporter ─────────────────────────────────────────────────────────────


class TestReporter:
    """Reporter.generate() — Markdown output structure."""

    def test_basic_structure(self):
        analysis = AnalysisResult(
            topic="Test",
            lang="en",
            depth="standard",
            summary="A quick test.",
            sources=[
                Source(
                    url="https://x.com",
                    title="X",
                    source_type="web",
                    source_lang="en",
                    content="...",
                )
            ],
            sections=[
                Section(id="summary", title="Summary", content="## Summary\nHello"),
                Section(id="overview", title="Overview", content="## Overview\nWorld"),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis, template="standard")
        assert "title: Test" in output
        assert "date: " in output
        assert "depth: standard" in output
        assert "## Summary" in output
        assert "Hello" in output
        assert "## Overview" in output
        assert "World" in output
        assert "[X](https://x.com)" in output
        assert "A quick test." in output

    def test_standard_section_order(self):
        assert Reporter.TEMPLATES["standard"] == SECTION_IDS_STANDARD

    def test_deep_section_order(self):
        assert Reporter.TEMPLATES["deep"] == SECTION_IDS_DEEP

    def test_missing_section_skipped(self):
        """Analysis with a section missing from template — should be skipped silently."""
        analysis = AnalysisResult(
            topic="Partial",
            depth="standard",
            sections=[],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        # Should produce front matter only + sources header
        assert "title: Partial" in output

    def test_data_points_table_zh(self):
        analysis = AnalysisResult(
            topic="Data",
            lang="zh",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            data_points=[
                DataPoint(key="latency", value="10ms", source_url="https://a.com"),
            ],
        )
        output = Reporter().generate(analysis)
        assert "关键数据" in output
        assert "| latency | 10ms" in output

    def test_data_points_table_en(self):
        analysis = AnalysisResult(
            topic="Data",
            lang="en",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            data_points=[
                DataPoint(key="latency", value="10ms", source_url="https://a.com"),
            ],
        )
        output = Reporter().generate(analysis)
        assert "Key Data" in output
        assert "| latency | 10ms" in output

    def test_comparisons_table_zh(self):
        analysis = AnalysisResult(
            topic="Compare",
            lang="zh",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            comparisons=[
                Comparison(dimension="speed", values={"A": "fast", "B": "slow"}, winner="A"),
            ],
        )
        output = Reporter().generate(analysis)
        assert "对比分析" in output
        assert "| A |" in output
        assert "| B |" in output
        assert "| speed | fast | slow |" in output

    def test_comparisons_table_en(self):
        analysis = AnalysisResult(
            topic="Compare",
            lang="en",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            comparisons=[
                Comparison(dimension="speed", values={"A": "fast", "B": "slow"}, winner="A"),
            ],
        )
        output = Reporter().generate(analysis)
        assert "Comparison" in output
        assert "| A |" in output
        assert "| B |" in output

    def test_contradictions_zh(self):
        analysis = AnalysisResult(
            topic="Contra",
            lang="zh",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            contradictions=["Source A says X, Source B says Y"],
        )
        output = Reporter().generate(analysis)
        assert "已发现的矛盾点" in output
        assert "Source A says X" in output

    def test_contradictions_en(self):
        analysis = AnalysisResult(
            topic="Contra",
            lang="en",
            depth="standard",
            sections=[Section(id="summary", title="Summary", content=".")],
            contradictions=["Source A says X, Source B says Y"],
        )
        output = Reporter().generate(analysis)
        assert "Contradictions" in output
        assert "Source A says X" in output


# ── Config ───────────────────────────────────────────────────────────────


class TestResolveOutputPath:
    """resolve_output_path() — path computation."""

    def test_default_output(self, tmp_path):
        cfg = ResearchConfig()
        path = resolve_output_path("Test Topic", cfg, tmp_path)
        assert str(path).startswith(str(tmp_path / "reports"))
        assert path.name.endswith(".md")
        assert path.parent == tmp_path / "reports"

    def test_topic_sanitized(self, tmp_path):
        cfg = ResearchConfig()
        path = resolve_output_path("Foo/Bar", cfg, tmp_path)
        assert "/" not in path.stem
        assert "foo-bar" in path.stem

    def test_custom_output_dir(self, tmp_path):
        cfg = ResearchConfig(output_dir="docs/research")
        path = resolve_output_path("Test", cfg, tmp_path)
        assert path.parent == tmp_path / "docs" / "research"

    def test_output_dir_created(self, tmp_path):
        cfg = ResearchConfig(output_dir="deep/nested/dir")
        path = resolve_output_path("Test", cfg, tmp_path)
        assert path.parent.exists()

    def test_fixed_filename_format(self, tmp_path):
        """After refactor, filename is fixed as {date}-{topic}-research.md."""
        cfg = ResearchConfig()
        path = resolve_output_path("My Topic", cfg, tmp_path)
        # Should match pattern: YYYY-MM-DD-my-topic-research.md
        parts = path.name.split("-")
        assert parts[-1] == "research.md"
        assert parts[0].isdigit()  # year


class TestLoadConfig:
    """load_config() — file read."""

    def test_no_file_returns_none(self, tmp_path):
        # Create a fake skill dir with no config
        fake_skill = tmp_path / "skills" / "tech-research"
        fake_skill.mkdir(parents=True)
        result = load_config(fake_skill)
        assert result is None

    def test_valid_config_no_filename_template(self, tmp_path):
        """After refactor, filename_template field is removed from config."""
        fake_skill = tmp_path / "skill"
        fake_skill.mkdir(parents=True)
        cfg_path = fake_skill / "config.json"
        cfg_path.write_text(
            json.dumps({"output_dir": "my_reports", "lang": "en"}),
            encoding="utf-8",
        )
        config = load_config(fake_skill)
        assert config is not None
        assert config.output_dir == "my_reports"
        assert config.lang == "en"

    def test_valid_config_with_legacy_fields(self, tmp_path):
        """Old configs with filename_template should still load (field ignored)."""
        fake_skill = tmp_path / "skill"
        fake_skill.mkdir(parents=True)
        cfg_path = fake_skill / "config.json"
        cfg_path.write_text(
            json.dumps(
                {"output_dir": "my_reports", "filename_template": "{date}-{topic}", "lang": "en"}
            ),
            encoding="utf-8",
        )
        config = load_config(fake_skill)
        assert config is not None
        assert config.output_dir == "my_reports"
        assert config.lang == "en"
        # filename_template is gone — just ensure no KeyError/AttributeError
        assert not hasattr(config, "filename_template")

    def test_corrupted_config_returns_none(self, tmp_path):
        fake_skill = tmp_path / "skill"
        fake_skill.mkdir(parents=True)
        (fake_skill / "config.json").write_text("not json", encoding="utf-8")
        config = load_config(fake_skill)
        assert config is None

    def test_partial_config_uses_defaults(self, tmp_path):
        fake_skill = tmp_path / "skill"
        fake_skill.mkdir(parents=True)
        (fake_skill / "config.json").write_text('{"output_dir": "custom"}', encoding="utf-8")
        config = load_config(fake_skill)
        assert config is not None
        assert config.output_dir == "custom"
        assert config.lang == "zh"


# ── research.py helper functions ─────────────────────────────────────────


class TestFindProjectRoot:
    """_find_project_root() — auto-detection."""

    def test_finds_git(self, tmp_path):
        root = tmp_path / "project"
        (root / ".git").mkdir(parents=True)
        skill_dir = root / ".opencode" / "skills" / "tech-research"
        skill_dir.mkdir(parents=True)
        assert _find_project_root(skill_dir) == root

    def test_finds_agents(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        (root / "AGENTS.md").write_text("# Agents", encoding="utf-8")
        skill_dir = root / ".opencode" / "skills" / "tech-research"
        skill_dir.mkdir(parents=True)
        assert _find_project_root(skill_dir) == root

    def test_fallback_to_cwd(self, tmp_path):
        skill_dir = tmp_path / "orphan" / "skill"
        skill_dir.mkdir(parents=True)
        # No .git or AGENTS.md in any parent
        result = _find_project_root(skill_dir)
        assert result is not None  # falls back to Path.cwd()


class TestCleanWorkfiles:
    """_clean_workfiles() — file cleanup (no content/ dir anymore)."""

    def test_removes_workfiles(self, tmp_path):
        for name in ["scope.json", "collected.json", "analysis.json"]:
            (tmp_path / name).write_text("{}", encoding="utf-8")
        _clean_workfiles(tmp_path)
        for name in ["scope.json", "collected.json", "analysis.json"]:
            assert not (tmp_path / name).exists()

    def test_skips_missing_files(self, tmp_path):
        """Should not error if file already gone."""
        _clean_workfiles(tmp_path)  # no files exist

    def test_ignores_other_files(self, tmp_path):
        """Should not remove non-workfiles."""
        (tmp_path / "other.json").write_text("{}", encoding="utf-8")
        (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
        _clean_workfiles(tmp_path)
        assert (tmp_path / "other.json").exists()
        assert (tmp_path / "keep.txt").exists()


# ── Scope Validator ──────────────────────────────────────────────────────


class TestScopeValidator:
    """validate_scope() — scope.json schema validation."""

    def test_valid_minimal(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Rust embedded",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "days",
                "quality_standard": "3_sources",
            },
        }
        assert validate_scope(data) == []

    def test_missing_topic(self):
        from scripts.scope_validator import validate_scope

        data = {
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "hours",
            }
        }
        errors = validate_scope(data)
        assert any("topic" in e for e in errors)

    def test_missing_standardized(self):
        from scripts.scope_validator import validate_scope

        data = {"topic": "Test"}
        errors = validate_scope(data)
        assert any("standardized" in e for e in errors)

    def test_invalid_goal_type(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "invalid",
                "audience": "myself",
                "time_constraint": "hours",
            },
        }
        errors = validate_scope(data)
        assert any("goal_type" in e for e in errors)

    def test_invalid_audience(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "everyone",
                "time_constraint": "hours",
            },
        }
        errors = validate_scope(data)
        assert any("audience" in e for e in errors)

    def test_invalid_time_constraint(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "minutes",
            },
        }
        errors = validate_scope(data)
        assert any("time_constraint" in e for e in errors)

    def test_invalid_quality_standard(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "panoramic_understanding",
                "audience": "myself",
                "time_constraint": "hours",
                "quality_standard": "best",
            },
        }
        errors = validate_scope(data)
        assert any("quality_standard" in e for e in errors)

    def test_tech_selection_requires_candidates(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "tech_selection",
                "audience": "myself",
                "time_constraint": "days",
            },
        }
        errors = validate_scope(data)
        assert any("candidates" in e for e in errors)

    def test_competitive_comparison_requires_dimensions(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "competitive_comparison",
                "audience": "myself",
                "time_constraint": "days",
            },
        }
        errors = validate_scope(data)
        assert any("comparison_dimensions" in e for e in errors)

    def test_feasibility_requires_technology(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "feasibility_assessment",
                "audience": "myself",
                "time_constraint": "weeks",
            },
        }
        errors = validate_scope(data)
        assert any("technology" in e for e in errors)

    def test_tech_selection_with_candidates_passes(self):
        from scripts.scope_validator import validate_scope

        data = {
            "topic": "Test",
            "standardized": {
                "goal_type": "tech_selection",
                "audience": "decision_maker",
                "time_constraint": "days",
                "candidates": ["Rust", "Go"],
            },
        }
        assert validate_scope(data) == []


# ── Save Config ──────────────────────────────────────────────────────────


class TestSaveConfig:
    """save_config() — config file write."""

    def test_creates_config_file(self, tmp_path):
        from scripts.config import ResearchConfig

        cfg = ResearchConfig(output_dir="my_output", lang="en")
        path = save_config(cfg, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["output_dir"] == "my_output"
        assert data["lang"] == "en"

    def test_roundtrip_load_save(self, tmp_path):
        from scripts.config import ResearchConfig, load_config

        original = ResearchConfig(output_dir="round_trip", lang="zh")
        save_config(original, tmp_path)
        loaded = load_config(tmp_path)
        assert loaded is not None
        assert loaded.output_dir == "round_trip"
        assert loaded.lang == "zh"


# ── Collect Command ──────────────────────────────────────────────────────


class TestCollectCommand:
    """cmd_collect() — add sources to collected.json."""

    def test_collect_from_list(self, tmp_path, monkeypatch):
        import research

        monkeypatch.setattr(research, "_SKILL_DIR", tmp_path)

        sources_file = tmp_path / "sources.json"
        sources_file.write_text(
            json.dumps(
                [
                    {
                        "url": "https://a.com",
                        "title": "A",
                        "type": "blog",
                        "source_type": "web",
                        "key_topics": ["perf"],
                        "content": "Content A",
                    }
                ]
            ),
            encoding="utf-8",
        )

        args = argparse.Namespace(input_file=str(sources_file), topic="Test Topic")
        research.cmd_collect(args)

        collected = json.loads((tmp_path / "collected.json").read_text(encoding="utf-8"))
        assert collected["topic"] == "Test Topic"
        assert len(collected["sources"]) == 1
        assert collected["sources"][0]["url"] == "https://a.com"

    def test_collect_from_dict_with_sources(self, tmp_path, monkeypatch):
        import research

        monkeypatch.setattr(research, "_SKILL_DIR", tmp_path)

        sources_file = tmp_path / "sources.json"
        sources_file.write_text(
            json.dumps(
                {
                    "sources": [{"url": "https://b.com", "title": "B", "content": "Content B"}],
                    "errors": [{"url": "https://fail.com", "error": "timeout", "stage": "fetch"}],
                }
            ),
            encoding="utf-8",
        )

        args = argparse.Namespace(input_file=str(sources_file), topic=None)
        research.cmd_collect(args)

        collected = json.loads((tmp_path / "collected.json").read_text(encoding="utf-8"))
        assert len(collected["sources"]) == 1
        assert len(collected["errors"]) == 1

    def test_collect_appends_to_existing(self, tmp_path, monkeypatch):
        import research

        monkeypatch.setattr(research, "_SKILL_DIR", tmp_path)

        existing = {
            "topic": "Old Topic",
            "sources": [{"url": "https://old.com", "title": "Old", "content": "Old"}],
            "errors": [],
        }
        (tmp_path / "collected.json").write_text(json.dumps(existing), encoding="utf-8")

        sources_file = tmp_path / "new_sources.json"
        sources_file.write_text(
            json.dumps([{"url": "https://new.com", "title": "New", "content": "New"}]),
            encoding="utf-8",
        )

        args = argparse.Namespace(input_file=str(sources_file), topic="Updated Topic")
        research.cmd_collect(args)

        collected = json.loads((tmp_path / "collected.json").read_text(encoding="utf-8"))
        assert collected["topic"] == "Updated Topic"
        assert len(collected["sources"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
