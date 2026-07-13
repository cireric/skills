from __future__ import annotations

from pathlib import Path

from scripts.artifact_checks import (
    CheckResult,
    check_analysis_schema,
    check_artifact_exists,
    check_key_insights_coverage,
    check_methodology_depth,
    check_quality_heuristics,
    check_recommendation_structure,
    check_section_coverage,
    check_source_tier_balance,
    check_subagent_delegation,
    check_url_traceability,
    run_all,
)


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
                "sections": [{"claims": [{"sources": ["https://example.com/a"]}]}],
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
                "sections": [{"claims": [{"sources": ["https://example.com/b"]}]}],
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
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
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
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
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
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
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
                            {"sources": ["https://a.com", "https://b.com"]},
                            {"sources": ["https://c.com", "https://d.com"]},
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
                            {"sources": ["https://a.com"]},
                            {"sources": ["https://b.com"]},
                            {"sources": ["https://c.com"]},
                        ]
                    }
                ],
            },
        )
        result = check_quality_heuristics(tmp_path)
        assert not result.passed
        assert result.level == "WARN"

    def test_single_source_threshold_depth_dynamic(self, tmp_path):
        # 2/3 single-source ratio = 0.667
        analysis = {
            "sections": [
                {
                    "claims": [
                        {"sources": ["https://a.com"]},
                        {"sources": ["https://b.com"]},
                        {"sources": ["https://c.com", "https://d.com"]},
                    ]
                }
            ]
        }
        # standard threshold is 70%: 0.667 does NOT warn
        _write_json(tmp_path / "analysis.json", analysis)
        _write_json(tmp_path / "scope.json", {"depth": "standard"})
        assert check_quality_heuristics(tmp_path).passed
        # deep threshold is 50%: 0.667 DOES warn
        _write_json(tmp_path / "scope.json", {"depth": "deep"})
        assert not check_quality_heuristics(tmp_path).passed
        # quick is not checked at all
        _write_json(tmp_path / "scope.json", {"depth": "quick"})
        assert check_quality_heuristics(tmp_path).passed


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
                            {"sources": ["https://example.com/a"]},
                            {"sources": ["https://example.com/b"]},
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
                            {"sources": ["https://example.com/a"]},
                            {"sources": ["https://example.com/b"]},
                            {"sources": ["https://example.com/c"]},
                            {"sources": ["https://example.com/d"]},
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
                            {"sources": ["https://example.com/a"]},
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
                            {"sources": ["https://example.com/a"]},
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
        assert len(results) >= 15


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

    def test_default_repair_hints_empty(self):
        r = CheckResult(name="x", level="BLOCKER", passed=True)
        assert r.repair_hints == []

    def test_custom_repair_hints(self):
        r = CheckResult(name="x", level="BLOCKER", passed=False, message="err", repair_hints=["fix A", "fix B"])
        assert r.repair_hints == ["fix A", "fix B"]

    def test_old_code_without_repair_hints_still_works(self):
        r = CheckResult(name="x", level="WARN", passed=True, message="ok")
        assert r.repair_hints == []


class TestCheckKeyInsightsCoverage:
    def test_non_exploratory_skipped(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"sections": []})
        result = check_key_insights_coverage(tmp_path, "tech_selection")
        assert result.passed
        assert "Skipped" in result.message

    def test_panoramic_with_sufficient_insights(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                        "key_insights": [
                            {"summary": "Finding A", "sources": ["https://a.com", "https://b.com"]},
                            {"summary": "Finding B", "sources": ["https://c.com", "https://d.com"]},
                        ],
                    },
                    {
                        "id": "findings",
                        "title": "Findings",
                        "content": "Content",
                        "key_insights": [
                            {"summary": "Finding C", "sources": ["https://e.com", "https://f.com"]},
                            {"summary": "Finding D", "sources": ["https://g.com", "https://h.com"]},
                        ],
                    },
                ],
            },
        )
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert result.passed

    def test_panoramic_missing_key_insights(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                    },
                ],
            },
        )
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "missing key_insights" in result.message

    def test_panoramic_insufficient_insights(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                        "key_insights": [{"summary": "Only one"}],
                    },
                ],
            },
        )
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "1 key_insights" in result.message

    def test_exploratory_with_sufficient_insights(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                        "key_insights": [
                            {"summary": "Finding A", "sources": ["https://a.com", "https://b.com"]},
                            {"summary": "Finding B", "sources": ["https://c.com", "https://d.com"]},
                        ],
                    },
                ],
            },
        )
        result = check_key_insights_coverage(tmp_path, "exploratory")
        assert result.passed

    def test_panoramic_insight_insufficient_sources(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Content",
                        "key_insights": [
                            {"summary": "Finding A", "sources": ["https://a.com"]},
                            {"summary": "Finding B", "sources": ["https://b.com", "https://c.com"]},
                        ],
                    },
                ],
            },
        )
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "key_insights[0]" in result.message
        assert "1 sources" in result.message


class TestRepairHintsArtifactExists:
    def test_missing_file_has_repair_hints(self, tmp_path):
        result = check_artifact_exists(tmp_path)
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "scope.json" in result.repair_hints[0]
        assert "collected.json" in result.repair_hints[0]
        assert "analysis.json" in result.repair_hints[0]

    def test_all_present_no_repair_hints(self, tmp_path):
        for name in ("scope.json", "collected.json", "analysis.json"):
            _write_json(tmp_path / name, {})
        result = check_artifact_exists(tmp_path)
        assert result.passed
        assert result.repair_hints == []


class TestRepairHintsUrlTraceability:
    def test_untraceable_url_has_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"claims": [{"sources": ["https://example.com/b"]}]}]},
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com/a"}],
        )
        result = check_url_traceability(tmp_path)
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "https://example.com/b" in result.repair_hints[0]
        assert "collected.json" in result.repair_hints[0]

    def test_all_traceable_no_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"claims": [{"sources": ["https://example.com/a"]}]}]},
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com/a"}],
        )
        result = check_url_traceability(tmp_path)
        assert result.passed
        assert result.repair_hints == []


class TestRepairHintsSectionCoverage:
    def test_missing_section_has_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"id": "overview"}]},
        )
        result = check_section_coverage(tmp_path, "tech_selection")
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "comparison" in result.repair_hints[0]
        assert "goal_type=tech_selection" in result.repair_hints[0]

    def test_exploratory_missing_overview_has_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"id": "findings"}, {"id": "methodology"}]},
        )
        result = check_section_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "overview" in result.repair_hints[0]

    def test_all_present_no_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"id": "overview"}, {"id": "comparison"}, {"id": "recommendation"}, {"id": "methodology"}]},
        )
        result = check_section_coverage(tmp_path, "tech_selection")
        assert result.passed
        assert result.repair_hints == []


class TestRepairHintsAnalysisSchema:
    def test_schema_failure_has_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"goal_type": "tech_selection", "sections": []},
        )
        result = check_analysis_schema(tmp_path)
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "id" in result.repair_hints[0]
        assert "title" in result.repair_hints[0]
        assert "content" in result.repair_hints[0]
        assert "summary" in result.repair_hints[0]
        assert "sources" in result.repair_hints[0]

    def test_valid_schema_no_repair_hints(self, tmp_path):
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
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_analysis_schema(tmp_path)
        assert result.passed
        assert result.repair_hints == []


class TestRepairHintsSubagentDelegation:
    def test_no_section_files_has_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview", "title": "Overview", "content": "Content"},
                    {"id": "comparison", "title": "Comparison", "content": "Content"},
                ],
            },
        )
        result = check_subagent_delegation(tmp_path)
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "2 sections" in result.repair_hints[0]
        assert "analysis_section_" in result.repair_hints[0]

    def test_with_section_files_no_repair_hints(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview", "title": "Overview", "content": "Content"},
                    {"id": "comparison", "title": "Comparison", "content": "Content"},
                ],
            },
        )
        _write_json(tmp_path / "analysis_section_overview.json", {"id": "overview"})
        _write_json(tmp_path / "analysis_section_comparison.json", {"id": "comparison"})
        result = check_subagent_delegation(tmp_path)
        assert result.passed
        assert result.repair_hints == []
