from __future__ import annotations

import json
from pathlib import Path

from scripts.gateway import (
    CheckResult,
    _normalize_numbers,
    _number_found_in_source,
    check_analysis_schema,
    check_artifact_exists,
    check_claim_dedup,
    check_claim_metadata,
    check_claim_verified,
    check_methodology_depth,
    check_metric_type_homogeneity,
    check_precision_inflation,
    check_quality_heuristics,
    check_recommendation_structure,
    check_section_coverage,
    check_source_metadata,
    check_source_tier_balance,
    check_claim_source_relevance,
    check_fetched_content_depth,
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
        """Exploratory goal_types should pass with overview + any other section."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{"id": "overview"}, {"id": "findings"}],
            },
        )
        result = check_section_coverage(tmp_path, "panoramic_understanding")
        assert result.passed

    def test_panoramic_understanding_missing_overview_fails(self, tmp_path):
        """Exploratory goal_types should fail when overview is missing."""
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
        """Exploratory goal_types should fail when only overview is present."""
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
        content = "word " * 200  # well over 150 words, but no Markdown table
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
        """Tier 1+2 > 30% → passes."""
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
        """All Tier 3-4 → WARN with message about low Tier 1+2 ratio."""
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
        """Non-quantitative goal type → skip."""
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
        """No collected items → skip."""
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
        assert len(results) >= 14  # final count: all checks including claim_dedup


class TestCheckPrecisionInflation:
    def test_blocker_exact_with_inappropriate_evidence(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "X",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "exact",
                    }],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "exact" in result.message

    def test_warn_third_party_with_precise_number(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "", "fetched_content": "x" * 300}],
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "WARN"

    def test_blocker_and_warn_combined(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "text": "X",
                            "source_urls": ["https://a.com"],
                            "evidence_type": "third_party_estimate",
                            "precision": "exact",
                        },
                        {
                            "text": "Achieves 95%",
                            "source_urls": ["https://b.com"],
                            "evidence_type": "third_party_estimate",
                            "precision": "range",
                        },
                    ],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_no_issues_pass(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Reliable data",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "official_data",
                        "precision": "exact",
                    }],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed

    def test_exact_with_expert_opinion_blocked(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "X",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "expert_opinion",
                        "precision": "exact",
                    }],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_data_variance_same_value_passes(self, tmp_path):
        """Same metric_type, same exact value → passes."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "text": "Achieves 54% accuracy",
                            "source_urls": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "text": "Also reported at 54%",
                            "source_urls": ["https://b.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                    ],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed

    def test_data_variance_conflicting_exact_blocker(self, tmp_path):
        """Same metric_type, conflicting exact values → BLOCKER."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "text": "Achieves 54% accuracy",
                            "source_urls": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "text": "Achieves 75% accuracy",
                            "source_urls": ["https://b.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                    ],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "s1: same metric_type" in result.message
        assert "swe_bench_verified" in result.message

    def test_data_variance_range_precision_passes(self, tmp_path):
        """Same metric_type, conflicting values but precision=range → passes."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "text": "Between 54% and 75% accuracy",
                            "source_urls": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "range",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "text": "Approximately 65% accuracy",
                            "source_urls": ["https://b.com"],
                            "evidence_type": "official_data",
                            "precision": "range",
                            "metric_type": "swe_bench_verified",
                        },
                    ],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed

    def test_third_party_number_found_in_source_no_warn(self, tmp_path):
        """third_party_estimate with precise number that EXISTS in source → no WARN."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Market size is $128 billion",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "Global market $128 billion", "fetched_content": "According to recent reports the global AI coding market reached $128 billion dollars in twenty twenty six according to recent reports the global AI coding market continues to expand rapidly this represents substantial growth year over year as more companies adopt AI"}],
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed

    def test_third_party_number_not_in_source_warns(self, tmp_path):
        """third_party_estimate with precise number NOT in source → WARN."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "About AI tools", "fetched_content": "This report covers various aspects and metrics of artificial intelligence tools and their adoption across different industries the analysis focuses on qualitative discussion and general trends rather than specific numerical benchmarks this report covers various aspects and metrics of artificial intelligence tools"}],
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "WARN"
        assert "not found in source" in result.message

    def test_third_party_number_no_collected_still_warns(self, tmp_path):
        """third_party_estimate with precise number, no collected.json → no warning (ADR 0018 auto-fix handles it)."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed

    def test_third_party_short_source_skips_number_check(self, tmp_path):
        """third_party_estimate with precise number, empty/short fetched_content → no warning (ADR 0018 auto-fix handles it)."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "", "fetched_content": ""}],
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed
        assert "too short" not in result.message
        assert "not found in source" not in result.message

    def test_third_party_sufficient_source_not_found_warns(self, tmp_path):
        """third_party_estimate with precise number, sufficient source but number absent → existing WARN."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "", "fetched_content": "A" * 250}],
        )
        result = check_precision_inflation(tmp_path)
        assert not result.passed
        assert result.level == "WARN"
        assert "not found in source" in result.message

    def test_third_party_sufficient_source_found_passes(self, tmp_path):
        """third_party_estimate with precise number, sufficient source and number present → PASS."""
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "text": "Achieves 98% accuracy",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "range",
                    }],
                }],
            },
        )
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "", "fetched_content": "A" * 200 + " 98% accuracy reported"}],
        )
        result = check_precision_inflation(tmp_path)
        assert result.passed


class TestCheckClaimMetadata:
    def test_quantitative_missing_metadata_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "claims": [
                        {"text": "A", "source_urls": ["https://a.com"]},
                        {"text": "B", "source_urls": ["https://b.com"]},
                        {"text": "C", "source_urls": ["https://c.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"},
                    ],
                }],
            },
        )
        result = check_claim_metadata(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"

    def test_quantitative_all_metadata_pass(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "claims": [{
                        "text": "A",
                        "source_urls": ["https://a.com"],
                        "evidence_type": "official_data",
                        "confidence": "high",
                        "precision": "exact",
                    }],
                }],
            },
        )
        result = check_claim_metadata(tmp_path, "tech_selection")
        assert result.passed

    def test_non_quantitative_not_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"claims": [{"text": "A", "source_urls": ["https://a.com"]}]}]},
        )
        result = check_claim_metadata(tmp_path, "exploratory")
        assert not result.passed
        assert "metadata" in result.message

    def test_zero_claims_pass(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"sections": []})
        result = check_claim_metadata(tmp_path, "tech_selection")
        assert result.passed


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


class TestCheckClaimVerified:
    def test_claim_verified_all_pass(self, tmp_path):
        (tmp_path / "review_report.md").write_text("# Review", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {"text": "Claim one", "source_urls": ["https://a.com"], "verified": True},
                            {"text": "Claim two", "source_urls": ["https://b.com"], "verified": True},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert result.passed

    def test_claim_verified_missing_fails(self, tmp_path):
        (tmp_path / "review_report.md").write_text("# Review", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {"text": "Claim one", "source_urls": ["https://a.com"], "verified": True},
                            {"text": "Claim two missing verified", "source_urls": ["https://b.com"]},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert result.passed

    def test_claim_verified_false_fails(self, tmp_path):
        (tmp_path / "review_report.md").write_text("# Review", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {"text": "Claim one", "source_urls": ["https://a.com"], "verified": True},
                            {"text": "Claim two is false", "source_urls": ["https://b.com"], "verified": False},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "Claim in section 'comparison' not verified" in result.message

    def test_claim_verified_unverifiable_warns(self, tmp_path):
        (tmp_path / "review_report.md").write_text("# Review", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {"text": "Claim one", "source_urls": ["https://a.com"], "verified": True},
                            {"text": "Claim two unverifiable", "source_urls": ["https://b.com"], "verified": "unverifiable"},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert result.passed
        assert result.level == "WARN"
        assert "unverifiable" in result.message

    def test_claim_verified_skipped_before_review(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {"text": "Claim one", "source_urls": ["https://a.com"]},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert result.passed

    def test_low_verified_ratio_warns(self, tmp_path):
        (tmp_path / "review_report.md").write_text("# Review", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {"text": "Verified 1", "source_urls": ["https://a.com"], "verified": True},
                            {"text": "Not verified 1", "source_urls": ["https://b.com"]},
                            {"text": "Not verified 2", "source_urls": ["https://c.com"]},
                            {"text": "Not verified 3", "source_urls": ["https://d.com"]},
                            {"text": "Not verified 4", "source_urls": ["https://e.com"]},
                        ],
                    }
                ],
            },
        )
        result = check_claim_verified(tmp_path)
        assert result.passed
        assert "claim_verified ratio" in result.message
        assert "20%" in result.message
        assert "degraded" in result.message


class TestCheckSourceMetadata:
    def test_official_data_without_source_metadata_blocker(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "text": "Model X achieves 95% accuracy",
                                "source_urls": ["https://example.com"],
                                "evidence_type": "official_data",
                            },
                        ],
                    }
                ],
            },
        )
        result = check_source_metadata(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "requires source_metadata" in result.message

    def test_independent_benchmark_without_source_metadata_blocker(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "text": "Model Y scores 88% on benchmark",
                                "source_urls": ["https://example.com"],
                                "evidence_type": "independent_benchmark",
                            },
                        ],
                    }
                ],
            },
        )
        result = check_source_metadata(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "requires source_metadata" in result.message

    def test_official_data_without_test_conditions_blocker(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "text": "Model X achieves 95% accuracy",
                                "source_urls": ["https://example.com"],
                                "evidence_type": "official_data",
                                "source_metadata": {
                                    "test_date": "2026-Q1",
                                    "source_type": "official_docs",
                                },
                            },
                        ],
                    }
                ],
            },
        )
        result = check_source_metadata(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "test_conditions" in result.message

    def test_official_data_with_source_metadata_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "text": "Model X achieves 95% accuracy",
                                "source_urls": ["https://example.com"],
                                "evidence_type": "official_data",
                                "source_metadata": {
                                    "test_conditions": "A100-80GB, CUDA 12.1",
                                    "test_date": "2026-Q1",
                                    "source_type": "official_docs",
                                },
                            },
                        ],
                    }
                ],
            },
        )
        result = check_source_metadata(tmp_path)
        assert result.passed

    def test_third_party_estimate_not_affected(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "overview",
                        "claims": [
                            {
                                "text": "Some estimate",
                                "source_urls": ["https://example.com"],
                                "evidence_type": "third_party_estimate",
                            },
                        ],
                    }
                ],
            },
        )
        result = check_source_metadata(tmp_path)
        assert result.passed


class TestCheckClaimDedup:
    def test_no_duplicates_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview", "claims": [{"text": "Claim A", "source_urls": ["https://a.com"]}]},
                    {"id": "details", "claims": [{"text": "Claim B", "source_urls": ["https://b.com"]}]},
                ],
            },
        )
        result = check_claim_dedup(tmp_path)
        assert result.passed

    def test_duplicate_claims_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {"id": "overview", "claims": [{"text": "Same claim text", "source_urls": ["https://a.com"]}]},
                    {"id": "details", "claims": [{"text": "Same claim text", "source_urls": ["https://b.com"]}]},
                ],
            },
        )
        result = check_claim_dedup(tmp_path)
        assert not result.passed
        assert "duplicate" in result.message.lower()


class TestNumberNormalization:
    def test_dollar_amount_in_source(self):
        assert _number_found_in_source("revenue was $9.8 billion", "market estimated at $9.8B")

    def test_billion_suffix_in_source(self):
        assert _number_found_in_source("revenue was 9.8 billion", "market reached $9.8B in 2026")

    def test_percentage_range_in_source(self):
        assert _number_found_in_source("failure rate is 45-70%", "between 45% and 70% of code fails")

    def test_comma_number_in_source(self):
        assert _number_found_in_source("surveyed 10,847 developers", "survey of 10847 developers")

    def test_no_false_match(self):
        assert not _number_found_in_source("response time 45ms", "latency was 450ms average")


class TestCheckFetchedContentDepth:
    def test_all_entries_have_substantial_content(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "B", "snippet": "s", "fetched_content": "y" * 300},
            ],
        )
        result = check_fetched_content_depth(tmp_path)
        assert result.passed
        assert result.level == "WARN"

    def test_empty_fetched_content_warns(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "B", "snippet": "s"},
            ],
        )
        result = check_fetched_content_depth(tmp_path)
        assert not result.passed
        assert "no fetched_content" in result.message

    def test_stub_fetched_content_warns(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "short"},
                {"url": "https://b.com", "title": "B", "snippet": "s", "fetched_content": "y" * 300},
            ],
        )
        result = check_fetched_content_depth(tmp_path)
        assert not result.passed
        assert "snippets" in result.message

    def test_majority_stub_blocks(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s"},
                {"url": "https://b.com", "title": "B", "snippet": "s"},
                {"url": "https://c.com", "title": "C", "snippet": "s", "fetched_content": "ok" * 100},
            ],
        )
        result = check_fetched_content_depth(tmp_path)
        assert result.level == "BLOCKER"

    def test_missing_collected_warns(self, tmp_path):
        result = check_fetched_content_depth(tmp_path)
        assert result.level == "WARN"

    def test_empty_collected_warns(self, tmp_path):
        _write_json(tmp_path / "collected.json", [])
        result = check_fetched_content_depth(tmp_path)
        assert result.level == "WARN"


class TestCheckClaimSourceRelevance:
    def _make_collected(self, entries):
        return entries

    def _make_analysis(self, claims):
        return {
            "topic": "test",
            "goal_type": "panoramic_understanding",
            "audience": "engineer",
            "sections": [
                {"id": "s1", "title": "S1", "content": "c", "claims": claims}
            ],
        }

    def test_no_numbers_in_claim_passes(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "about coding", "fetched_content": "x" * 300}]
        claims = [{"text": "AI is widely used", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "qualitative"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert result.passed

    def test_number_found_in_source_passes(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "the accuracy reached 95 percent in tests " + "x" * 200}]
        claims = [{"text": "Model achieves 95% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert result.passed

    def test_number_not_in_source_warns(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "the model performed well in general " + "x" * 200}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert not result.passed
        assert "not found in source" in result.message

    def test_third_party_estimate_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "no numbers here " + "x" * 200}]
        claims = [{"text": "Revenue reached $5B in 2026", "source_urls": ["https://a.com"], "evidence_type": "third_party_estimate", "confidence": "medium", "precision": "range"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert result.passed

    def test_expert_opinion_number_not_in_source_warns(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "expert analysis of the market " + "x" * 200}]
        claims = [{"text": "Adoption rate is 85% according to experts", "source_urls": ["https://a.com"], "evidence_type": "expert_opinion", "confidence": "medium", "precision": "range"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert not result.passed

    def test_short_fetched_content_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "short"}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert result.passed

    def test_no_source_urls_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "x" * 300}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": [], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert result.passed

    def test_multiple_claims_mixed_results(self, tmp_path):
        collected = [
            {"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "accuracy was 95 percent " + "x" * 200},
            {"url": "https://b.com", "title": "B", "snippet": "s", "fetched_content": "no relevant data " + "x" * 200},
        ]
        claims = [
            {"text": "Model achieves 95% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"},
            {"text": "Revenue reached 98 billion dollars", "source_urls": ["https://b.com"], "evidence_type": "official_data", "confidence": "high", "precision": "range"},
        ]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        result = check_claim_source_relevance(tmp_path)
        assert not result.passed
        assert "1 claim(s)" in result.message
