from __future__ import annotations

import json
from pathlib import Path

from scripts.artifact_checks import CheckResult
from scripts.claim_validator import ClaimValidator, _normalize_numbers, _number_found_in_source


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_result(results, name):
    return next((r for r in results if r.name == name), None)


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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_data_variance_same_value_passes(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed

    def test_data_variance_conflicting_exact_blocker(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "s1: same metric_type" in result.message
        assert "swe_bench_verified" in result.message

    def test_data_variance_range_precision_passes(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed

    def test_third_party_number_found_in_source_no_warn(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed

    def test_third_party_number_not_in_source_warns(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "WARN"
        assert "not found in source" in result.message

    def test_third_party_number_no_collected_still_warns(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed

    def test_third_party_short_source_skips_number_check(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed
        assert "too short" not in result.message
        assert "not found in source" not in result.message

    def test_third_party_sufficient_source_not_found_warns(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "WARN"
        assert "not found in source" in result.message

    def test_third_party_sufficient_source_found_passes(self, tmp_path):
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_metadata")
        assert result.passed

    def test_non_quantitative_not_skipped(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {"sections": [{"claims": [{"text": "A", "source_urls": ["https://a.com"]}]}]},
        )
        results = ClaimValidator(tmp_path, "exploratory").check()
        result = _get_result(results, "claim_metadata")
        assert not result.passed
        assert "metadata" in result.message

    def test_zero_claims_pass(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {"sections": []})
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_metadata")
        assert result.passed


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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_verified")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_metadata")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_dedup")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_dedup")
        assert not result.passed
        assert "duplicate" in result.message.lower()


class TestCheckRefMarkerValidity:
    def test_passes_when_all_markers_in_collected(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "See {{ref:https://a.com}} for details.",
                    "claims": [{"text": "C", "source_urls": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "ref_marker_validity")
        assert result.passed

    def test_blocks_when_marker_url_not_in_collected(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "See {{ref:https://b.com}} for details.",
                    "claims": [],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "ref_marker_validity")
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_warns_when_no_markers(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "No refs here.",
                    "claims": [],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "ref_marker_validity")
        assert result.passed
        assert result.level == "WARN"


class TestCheckClaimSourceRefCoverage:
    def test_passes_when_all_claim_sources_in_content(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "See {{ref:https://a.com}} for details.",
                    "claims": [{"text": "C", "source_urls": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert result.passed

    def test_blocks_when_claim_source_not_in_content(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "No ref marker for this claim's source.",
                    "claims": [{"text": "C", "source_urls": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_passes_when_shared_url_appears_once(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "See {{ref:https://a.com}} for details.",
                    "claims": [
                        {"text": "C1", "source_urls": ["https://a.com"]},
                        {"text": "C2", "source_urls": ["https://a.com"]},
                    ],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert result.passed


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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert result.passed

    def test_number_found_in_source_passes(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "the accuracy reached 95 percent in tests " + "x" * 200}]
        claims = [{"text": "Model achieves 95% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert result.passed

    def test_number_not_in_source_warns(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "the model performed well in general " + "x" * 200}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert not result.passed
        assert "not found in source" in result.message

    def test_third_party_estimate_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "no numbers here " + "x" * 200}]
        claims = [{"text": "Revenue reached $5B in 2026", "source_urls": ["https://a.com"], "evidence_type": "third_party_estimate", "confidence": "medium", "precision": "range"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert result.passed

    def test_expert_opinion_number_not_in_source_warns(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "expert analysis of the market " + "x" * 200}]
        claims = [{"text": "Adoption rate is 85% according to experts", "source_urls": ["https://a.com"], "evidence_type": "expert_opinion", "confidence": "medium", "precision": "range"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert not result.passed

    def test_short_fetched_content_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "short"}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert result.passed

    def test_no_source_urls_skipped(self, tmp_path):
        collected = [{"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "x" * 300}]
        claims = [{"text": "Model achieves 98% accuracy", "source_urls": [], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}]
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", self._make_analysis(claims))
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
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
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_relevance")
        assert not result.passed
        assert "1 claim(s)" in result.message
