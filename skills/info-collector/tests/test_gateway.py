from __future__ import annotations

import json
from pathlib import Path

from scripts.gateway import (
    CheckResult,
    check_analysis_schema,
    check_artifact_exists,
    check_claim_metadata,
    check_precision_inflation,
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

    def test_non_quantitative_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"claims": [{"text": "A", "source_urls": ["https://a.com"]}]}]},
        )
        result = check_claim_metadata(tmp_path, "exploratory")
        assert result.passed
        assert "Skipped" in result.message

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
