from __future__ import annotations

import json
from pathlib import Path

from scripts.artifact_checks import (
    CheckResult,
    check_analysis_schema,
    check_artifact_exists,
    check_methodology_depth,
    check_quality_heuristics,
    check_recommendation_structure,
    check_section_coverage,
    check_source_tier_balance,
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
                    {"id": "methodology"},
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
        assert "comparison" in result.message

    def test_missing_methodology_tech_selection(self, tmp_path):
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
        assert not result.passed
        assert "methodology" in result.message

    def test_missing_methodology_feasibility_assessment(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "analysis"},
                    {"id": "conclusion"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "feasibility_assessment")
        assert not result.passed
        assert "methodology" in result.message

    def test_missing_methodology_competitive_comparison(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "comparison"},
                    {"id": "positioning"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "competitive_comparison")
        assert not result.passed
        assert "methodology" in result.message

    def test_missing_methodology_market_analysis(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "data"},
                    {"id": "trends"},
                    {"id": "conclusion"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "market_analysis")
        assert not result.passed
        assert "methodology" in result.message

    def test_missing_methodology_academic_research(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "abstract"},
                    {"id": "findings"},
                    {"id": "references"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "academic_research")
        assert not result.passed
        assert "methodology" in result.message

    def test_with_methodology_tech_selection(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "comparison"},
                    {"id": "recommendation"},
                    {"id": "methodology"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "tech_selection")
        assert result.passed

    def test_with_methodology_feasibility_assessment(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "analysis"},
                    {"id": "conclusion"},
                    {"id": "methodology"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "feasibility_assessment")
        assert result.passed

    def test_with_methodology_competitive_comparison(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "comparison"},
                    {"id": "positioning"},
                    {"id": "methodology"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "competitive_comparison")
        assert result.passed

    def test_with_methodology_market_analysis(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview"},
                    {"id": "data"},
                    {"id": "trends"},
                    {"id": "conclusion"},
                    {"id": "methodology"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "market_analysis")
        assert result.passed

    def test_with_methodology_academic_research(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "abstract"},
                    {"id": "findings"},
                    {"id": "references"},
                    {"id": "methodology"},
                ],
            },
        )
        result = check_section_coverage(tmp_path, "academic_research")
        assert result.passed

    def test_non_quantitative_no_methodology(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "overview"}, {"id": "details"}],
            },
        )
        result = check_section_coverage(tmp_path, "exploratory")
        assert result.passed

    def test_panoramic_understanding_loose_check_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "overview"}, {"id": "findings"}],
            },
        )
        result = check_section_coverage(tmp_path, "panoramic_understanding")
        assert result.passed

    def test_panoramic_understanding_missing_overview_fails(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "findings"}, {"id": "methodology"}],
            },
        )
        result = check_section_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "overview" in result.message

    def test_panoramic_understanding_only_overview_fails(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "overview"}],
            },
        )
        result = check_section_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "2" in result.message


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


class TestCheckAnalysisSchemaDuplicateTitle:
    def test_duplicate_heading_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "## Section Title",
                        "claims": [{"text": "Claim", "source_urls": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert result.level == "WARN"
        assert result.passed
        assert "duplicate" in result.message.lower()

    def test_no_duplicate_heading_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "Test",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Normal content without headings",
                        "claims": [{"text": "Claim", "source_urls": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert result.level == "BLOCKER"
        assert result.passed

    def test_schema_failure_still_blocker(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "goal_type": "tech_selection",
                "sections": [],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert result.level == "BLOCKER"
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


class TestCheckMethodologyDepth:
    def test_non_quantitative_skipped(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"sections": []})
        result = check_methodology_depth(tmp_path, "exploratory")
        assert result.passed
        assert result.level == "WARN"
        assert "Skipped" in result.message

    def test_short_methodology_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": "Short methodology content.",
                        "claims": [],
                    }
                ],
            },
        )
        result = check_methodology_depth(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "words" in result.message.lower()

    def test_no_table_warns(self, tmp_path):
        content = "word " * 200
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": content,
                        "claims": [],
                    }
                ],
            },
        )
        result = check_methodology_depth(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "table" in result.message.lower()

    def test_proper_methodology_passes(self, tmp_path):
        content = ("word " * 200) + "\n| col1 | col2 |\n| a | b |"
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": content,
                        "claims": [],
                    }
                ],
            },
        )
        result = check_methodology_depth(tmp_path, "tech_selection")
        assert result.passed
        assert result.level == "WARN"

    def test_missing_methodology_section_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Some content",
                        "claims": [],
                    }
                ],
            },
        )
        result = check_methodology_depth(tmp_path, "tech_selection")
        assert result.passed
        assert "no methodology section" in result.message.lower() or "Skipped" in result.message


class TestCheckRecommendationStructure:
    def test_tech_selection_without_table(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "recommendation", "title": "Recommendation", "content": "We recommend X for its performance."},
                ],
            },
        )
        result = check_recommendation_structure(tmp_path, "tech_selection")
        assert result.level == "WARN"
        assert not result.passed
        assert "comparison table" in result.message

    def test_tech_selection_without_not_recommended(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "recommendation", "title": "Recommendation",
                        "content": "| Feature | X | Y |\n|---------|---|---|\n| Speed   | 100 | 80 |",
                    },
                ],
            },
        )
        result = check_recommendation_structure(tmp_path, "tech_selection")
        assert result.level == "WARN"
        assert not result.passed
        assert "不推荐" in result.message or "not recommended" in result.message

    def test_proper_structure(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "recommendation", "title": "Recommendation",
                        "content": "| Feature | X | Y |\n|---------|---|---|\n不推荐 Y due to poor performance",
                    },
                ],
            },
        )
        result = check_recommendation_structure(tmp_path, "tech_selection")
        assert result.level == "WARN"
        assert result.passed

    def test_exploratory_goal_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"id": "recommendation", "content": "No table here"}]},
        )
        result = check_recommendation_structure(tmp_path, "exploratory")
        assert result.level == "WARN"
        assert result.passed
        assert "Skipped" in result.message

    def test_no_recommendation_section(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"id": "overview", "content": "Overview"}]},
        )
        result = check_recommendation_structure(tmp_path, "tech_selection")
        assert result.level == "WARN"
        assert result.passed
        assert "Skipped" in result.message


class TestCheckSourceTierBalance:
    def test_good_balance_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://example.com/a"]},
                            {"source_urls": ["https://example.com/b"]},
                        ],
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/a", "source_tier": 1},
                {"url": "https://example.com/b", "source_tier": 3},
            ],
        )
        result = check_source_tier_balance(tmp_path, "tech_selection")
        assert result.passed
        assert result.level == "WARN"

    def test_poor_balance_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://example.com/a"]},
                            {"source_urls": ["https://example.com/b"]},
                            {"source_urls": ["https://example.com/c"]},
                            {"source_urls": ["https://example.com/d"]},
                        ],
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/a", "source_tier": 3},
                {"url": "https://example.com/b", "source_tier": 4},
                {"url": "https://example.com/c", "source_tier": 3},
                {"url": "https://example.com/d", "source_tier": 4},
            ],
        )
        result = check_source_tier_balance(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "Tier 1+2" in result.message

    def test_non_quantitative_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://example.com/a"]},
                        ],
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/a", "source_tier": 1},
            ],
        )
        result = check_source_tier_balance(tmp_path, "exploratory")
        assert result.passed
        assert "Skipped" in result.message

    def test_no_collected_items_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "claims": [
                            {"source_urls": ["https://example.com/a"]},
                        ],
                    }
                ],
            },
        )
        _write_json(tmp_path / "collected.json", [])
        result = check_source_tier_balance(tmp_path, "tech_selection")
        assert result.passed
        assert "Skipped" in result.message


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
        assert len(results) >= 14


class TestCheckResultDataclass:
    def test_default_message_empty(self):
        r = CheckResult(name="x", level="BLOCKER", passed=True)
        assert r.message == ""

    def test_custom_message(self):
        r = CheckResult(name="x", level="WARN", passed=False, message="details")
        assert r.message == "details"

    def test_attribute_access(self):
        r = CheckResult(name="test", level="BLOCKER", passed=False, message="err")
        assert r.name == "test"
        assert r.level == "BLOCKER"
        assert not r.passed
        assert r.message == "err"
