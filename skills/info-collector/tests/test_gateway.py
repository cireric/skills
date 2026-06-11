from __future__ import annotations

import json
from pathlib import Path

from scripts.gateway import (
    check_analysis_schema,
    check_artifact_exists,
    check_quality_heuristics,
    check_section_coverage,
    check_url_traceability,
    run_all,
)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class TestCheckArtifactExists:
    def test_all_present(self, tmp_path):
        for name in ("scope.json", "collected.json", "analysis.json"):
            _write_json(tmp_path / name, {})
        result = check_artifact_exists(tmp_path)
        assert result.passed

    def test_missing_file(self, tmp_path):
        result = check_artifact_exists(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"


class TestCheckUrlTraceability:
    def test_all_traceable(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"claims": [{"source_urls": ["https://example.com/a"]}]}],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/a"},
            ],
        )
        result = check_url_traceability(tmp_path)
        assert result.passed

    def test_untraceable_url(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"claims": [{"source_urls": ["https://example.com/b"]}]}],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/a"},
            ],
        )
        result = check_url_traceability(tmp_path)
        assert not result.passed


class TestCheckSectionCoverage:
    def test_required_sections_present(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "comparison"},
                    {"id": "recommendation"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "tech_selection")
        assert result.passed

    def test_missing_section(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "overview"}],
            },
        )
        result = check_section_coverage(tmp_path, "tech_selection")
        assert not result.passed


class TestCheckAnalysisSchema:
    def test_valid_schema(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                        "claims": [{"text": "Claim", "source_urls": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert result.passed

    def test_missing_topic(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "goal_type": "tech_selection",
                "sections": [],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert not result.passed

    def test_empty_sections(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert not result.passed


class TestCheckQualityHeuristics:
    def test_clean_heuristics(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://a.com", "https://b.com"]},
                            {"source_urls": ["https://c.com", "https://d.com"]},
                        ]
                    }
                ],
            },
        )
        result = check_quality_heuristics(tmp_path)
        assert result.passed

    def test_single_source_warning(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://a.com"]},
                            {"source_urls": ["https://b.com"]},
                            {"source_urls": ["https://c.com", "https://d.com"]},
                        ]
                    }
                ],
            },
        )
        result = check_quality_heuristics(tmp_path)
        assert not result.passed
        assert result.level == "WARN"


class TestRunAll:
    def test_returns_all_results(self, tmp_path):
        _write_json(tmp_path / "scope.json", {})
        _write_json(tmp_path / "collected.json", [])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [],
            },
        )
        results = run_all(tmp_path, "tech_selection")
        assert len(results) == 7  # noqa: PLR2004
