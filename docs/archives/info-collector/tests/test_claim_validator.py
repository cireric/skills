from __future__ import annotations

from pathlib import Path

from scripts.lib.check_types import CheckResult
from scripts.claim_validator import ClaimValidator, _normalize_numbers, _number_found_in_source, _is_indirect_source, _source_text
from scripts.lib.constants import _INDIRECT_CITATION_PATTERNS


def _get_result(results, name):
    return next((r for r in results if r.name == name), None)


class TestCheckPrecisionInflation:
    def test_warn_exact_with_inappropriate_evidence(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "X",
                        "sources": ["https://a.com"],
                        "evidence_type": "third_party_estimate",
                        "precision": "exact",
                    }],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "WARN"
        assert "auto-downgraded to 'range' by sanitize" in result.message

    def test_warn_third_party_with_precise_number(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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

    def test_warn_exact_and_number_not_found_combined(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "summary": "X",
                            "sources": ["https://a.com"],
                            "evidence_type": "third_party_estimate",
                            "precision": "exact",
                        },
                        {
                            "summary": "Achieves 95%",
                            "sources": ["https://b.com"],
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
        assert result.level == "WARN"

    def test_no_issues_pass(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "Reliable data",
                        "sources": ["https://a.com"],
                        "evidence_type": "official_data",
                        "precision": "exact",
                    }],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert result.passed
        assert result.level == "WARN"

    def test_exact_with_expert_opinion_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "X",
                        "sources": ["https://a.com"],
                        "evidence_type": "expert_opinion",
                        "precision": "exact",
                    }],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "precision_inflation")
        assert not result.passed
        assert result.level == "WARN"

    def test_data_variance_same_value_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "summary": "Achieves 54% accuracy",
                            "sources": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "summary": "Also reported at 54%",
                            "sources": ["https://b.com"],
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

    def test_data_variance_conflicting_exact_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "summary": "Achieves 54% accuracy",
                            "sources": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "exact",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "summary": "Achieves 75% accuracy",
                            "sources": ["https://b.com"],
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
        assert result.level == "WARN"
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
                            "summary": "Between 54% and 75% accuracy",
                            "sources": ["https://a.com"],
                            "evidence_type": "official_data",
                            "precision": "range",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "summary": "Approximately 65% accuracy",
                            "sources": ["https://b.com"],
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
                        "summary": "Market size is $128 billion",
                        "sources": ["https://a.com"],
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
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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
                        "summary": "Achieves 98% accuracy",
                        "sources": ["https://a.com"],
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
                        {"summary": "A", "sources": ["https://a.com"]},
                        {"summary": "B", "sources": ["https://b.com"]},
                        {"summary": "C", "sources": ["https://c.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"},
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
                        "summary": "A",
                        "sources": ["https://a.com"],
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
            {"sections": [{"claims": [{"summary": "A", "sources": ["https://a.com"]}]}]},
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


class TestCheckSourceMetadata:
    def test_official_data_without_source_metadata_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "summary": "Model X achieves 95% accuracy",
                                "sources": ["https://example.com"],
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
        assert result.level == "WARN"
        assert "missing source_metadata" in result.message

    def test_independent_benchmark_without_source_metadata_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "summary": "Model Y scores 88% on benchmark",
                                "sources": ["https://example.com"],
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
        assert result.level == "WARN"
        assert "missing source_metadata" in result.message

    def test_official_data_without_test_conditions_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "summary": "Model X achieves 95% accuracy",
                                "sources": ["https://example.com"],
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
        assert result.level == "WARN"
        assert "empty source_metadata.test_conditions" in result.message

    def test_official_data_with_source_metadata_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [
                    {
                        "id": "comparison",
                        "claims": [
                            {
                                "summary": "Model X achieves 95% accuracy",
                                "sources": ["https://example.com"],
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
                                "summary": "Some estimate",
                                "sources": ["https://example.com"],
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
                    {"id": "overview", "claims": [{"summary": "Claim A", "sources": ["https://a.com"]}]},
                    {"id": "details", "claims": [{"summary": "Claim B", "sources": ["https://b.com"]}]},
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
                    {"id": "overview", "claims": [{"summary": "Same claim text", "sources": ["https://a.com"]}]},
                    {"id": "details", "claims": [{"summary": "Same claim text", "sources": ["https://b.com"]}]},
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
                    "claims": [{"summary": "C", "sources": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "ref_marker_validity")
        assert result.passed
        assert result.repair_hints == []

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
        assert len(result.repair_hints) > 0
        assert "https://b.com" in result.repair_hints[0]
        assert "collected.json" in result.repair_hints[0]

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
                    "claims": [{"summary": "C", "sources": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert result.passed
        assert result.repair_hints == []

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
                    "claims": [{"summary": "C", "sources": ["https://a.com"]}],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert not result.passed
        assert result.level == "BLOCKER"
        assert len(result.repair_hints) > 0
        assert "C" in result.repair_hints[0]
        assert "{ref:URL}" in result.repair_hints[0]

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
                        {"summary": "C1", "sources": ["https://a.com"]},
                        {"summary": "C2", "sources": ["https://a.com"]},
                    ],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "claim_source_ref_coverage")
        assert result.passed


class TestCheckMetricTypeHomogeneity:
    def test_mixed_metric_types_is_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [
                        {
                            "summary": "A",
                            "sources": ["https://a.com"],
                            "evidence_type": "official_data",
                            "metric_type": "swe_bench_verified",
                        },
                        {
                            "summary": "B",
                            "sources": ["https://b.com"],
                            "evidence_type": "independent_benchmark",
                            "metric_type": "swe_bench_pro",
                        },
                    ],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "metric_type_homogeneity")
        assert not result.passed
        assert result.level == "WARN"

    def test_single_metric_type_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "A",
                        "sources": ["https://a.com"],
                        "evidence_type": "official_data",
                        "metric_type": "swe_bench_verified",
                    }],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "metric_type_homogeneity")
        assert result.passed


class TestNumberNormalization:
    def test_dollar_amount_in_source(self):
        assert _number_found_in_source("revenue was $9.8 billion", "market estimated at $9.8B") == "source_confirmed"

    def test_billion_suffix_in_source(self):
        assert _number_found_in_source("revenue was 9.8 billion", "market reached $9.8B in 2026") == "source_confirmed"

    def test_percentage_range_in_source(self):
        assert _number_found_in_source("failure rate is 45-70%", "between 45% and 70% of code fails") == "source_confirmed"

    def test_comma_number_in_source(self):
        assert _number_found_in_source("surveyed 10,847 developers", "survey of 10847 developers") == "source_confirmed"

    def test_no_false_match(self):
        assert _number_found_in_source("response time 45ms", "latency was 450ms average") == "source_absent"


class TestSourceVerificationCheck:
    def test_confirmed_number_in_source(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Achieves 98% accuracy",
                "sources": ["https://a.com"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "The system achieves 98% accuracy on the benchmark", "source_tier": 1}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert result.passed
        assert "source_confirmed" in result.message

    def test_absent_number_not_in_source(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Achieves 72.2% accuracy",
                "sources": ["https://a.com"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "The system performs well on benchmarks", "source_tier": 1}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert result.passed
        assert "source_absent" in result.message

    def test_indirect_tier3_third_party(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Market grows 15%",
                "sources": ["https://a.com"],
                "evidence_type": "third_party_estimate",
                "confidence": "medium",
                "precision": "range",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "x" * 300, "source_tier": 3}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_indirect" in result.message

    def test_indirect_vendor_source_type(self, tmp_path):
        # Non-authoritative venue (tier 3) tagged vendor_benchmark still flips to indirect.
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Scores 5000 req/s",
                "sources": ["https://a.com"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
                "source_metadata": {"test_conditions": "H100", "test_date": "2026", "source_type": "vendor_benchmark"},
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "5000 req/s measured", "source_tier": 3}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_indirect" in result.message

    def test_vendor_source_type_on_authoritative_venue_not_indirect(self, tmp_path):
        # An academic paper (tier 1) mislabeled as vendor_benchmark must NOT flip
        # to indirect — authority is anchored on the venue tier, not the label.
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "V3 achieves 5000 req/s",
                "sources": ["https://ar5iv.labs.arxiv.org/html/2501.00001"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
                "source_metadata": {"test_conditions": "H100", "test_date": "2026", "source_type": "vendor_benchmark"},
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://ar5iv.labs.arxiv.org/html/2501.00001", "snippet": "",
             "fetched_content": "V3 achieves 5000 req/s", "source_tier": 1}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_indirect" not in result.message

    def test_qualitative_claim_defaults_confirmed(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Framework is widely adopted",
                "sources": ["https://a.com"],
                "evidence_type": "qualitative_trend",
                "confidence": "medium",
                "precision": "qualitative",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "x" * 300, "source_tier": 2}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_confirmed" in result.message

    def test_indirect_ratio_is_info(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [
                {
                    "summary": "Scores 72.2%",
                    "sources": ["https://a.com"],
                    "evidence_type": "third_party_estimate",
                    "confidence": "medium",
                    "precision": "range",
                },
                {
                    "summary": "据Gartner报告显示增长",
                    "sources": ["https://b.com"],
                    "evidence_type": "third_party_estimate",
                    "confidence": "medium",
                    "precision": "qualitative",
                },
            ]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "no numbers here", "source_tier": 3},
            {"url": "https://b.com", "snippet": "", "fetched_content": "x" * 300, "source_tier": 3},
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result.passed
        assert result.level == "INFO"

    def test_indirect_rule3_host_match_not_indirect(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "据Gartner报告显示增长15%",
                "sources": ["https://gartner.com/report"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://gartner.com/report", "snippet": "", "fetched_content": "growth of 15%", "source_tier": 2}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_confirmed" in result.message

    def test_indirect_rule3_host_mismatch_is_indirect(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "据Gartner报告显示增长15%",
                "sources": ["https://someblog.com/post"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://someblog.com/post", "snippet": "", "fetched_content": "Gartner says 15% growth", "source_tier": 3}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert result is not None
        assert "source_indirect" in result.message

    def test_source_verification_does_not_write_to_disk(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [{
                "summary": "Achieves 98% accuracy",
                "sources": ["https://a.com"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
            }]}],
        })
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "", "fetched_content": "98% accuracy", "source_tier": 1}
        ])
        original_mtime = (tmp_path / "analysis.json").stat().st_mtime
        import time; time.sleep(0.01)
        ClaimValidator(tmp_path, "tech_selection").check()
        new_mtime = (tmp_path / "analysis.json").stat().st_mtime
        assert original_mtime == new_mtime


class TestSourceTextWithSourceFile:
    def test_reads_from_source_file(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("Revenue was $4.5B in 2025", encoding="utf-8")
        item = {
            "source_file": "sources/abc123.md",
            "fetched_content": "Revenue was $4.5B...",
            "snippet": "Financial report",
        }
        result = _source_text(item, tmp_path)
        assert "$4.5b in 2025" in result
        assert "financial report" in result

    def test_falls_back_to_fetched_content_when_no_source_file(self, tmp_path):
        item = {
            "fetched_content": "Revenue was $4.5B",
            "snippet": "Financial report",
        }
        result = _source_text(item, tmp_path)
        assert "revenue was $4.5b" in result
        assert "financial report" in result

    def test_falls_back_when_source_file_missing_on_disk(self, tmp_path):
        item = {
            "source_file": "sources/nonexistent.md",
            "fetched_content": "Revenue was $4.5B",
            "snippet": "Financial report",
        }
        result = _source_text(item, tmp_path)
        assert "revenue was $4.5b" in result

    def test_falls_back_when_source_file_empty(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "empty.md").write_text("", encoding="utf-8")
        item = {
            "source_file": "sources/empty.md",
            "fetched_content": "Revenue was $4.5B",
            "snippet": "Financial report",
        }
        result = _source_text(item, tmp_path)
        assert "revenue was $4.5b" in result

    def test_no_workdir_uses_fetched_content(self):
        item = {
            "source_file": "sources/abc123.md",
            "fetched_content": "Revenue was $4.5B",
            "snippet": "Financial report",
        }
        result = _source_text(item)
        assert "revenue was $4.5b" in result

    def test_source_file_overrides_fetched_content(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "full.md").write_text("The exact number is 97.3% accuracy", encoding="utf-8")
        item = {
            "source_file": "sources/full.md",
            "fetched_content": "Accuracy is high...",
            "snippet": "ML benchmark",
        }
        result = _source_text(item, tmp_path)
        assert "97.3% accuracy" in result
        assert "high..." not in result


class TestVerificationWithSourceFile:
    def test_number_verified_from_source_file(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("The model achieved 97.3% accuracy on the benchmark", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "Achieves 97.3% accuracy",
                        "sources": ["https://a.com"],
                        "evidence_type": "independent_benchmark",
                        "confidence": "high",
                        "precision": "exact",
                    }],
                }],
            },
        )
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "Benchmark", "source_file": "sources/abc123.md", "source_tier": 1}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert "source_confirmed" in result.message

    def test_number_absent_when_source_file_lacks_it(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("The model performed well in general testing", encoding="utf-8")
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "claims": [{
                        "summary": "Achieves 97.3% accuracy",
                        "sources": ["https://a.com"],
                        "evidence_type": "official_data",
                        "confidence": "high",
                        "precision": "exact",
                    }],
                }],
            },
        )
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "snippet": "Report", "source_file": "sources/abc123.md", "source_tier": 1}
        ])
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "source_verification_check")
        assert "source_absent" in result.message


class TestRefMarkerSuggestion:
    def test_suggestion_in_message_when_prefix_match(self, tmp_path):
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com/long-path-name/article", "snippet": "A", "fetched_content": "content"}],
        )
        _write_json(
            tmp_path / "analysis.json",
            {
                "sections": [{
                    "id": "s1",
                    "content": "See {{ref:https://example.com/long-path-name/arti}} for details.",
                    "claims": [],
                }],
            },
        )
        results = ClaimValidator(tmp_path, "tech_selection").check()
        result = _get_result(results, "ref_marker_validity")
        assert not result.passed
        assert "did you mean" in result.message


class TestIndirectCitationChinese:
    def test_ju_baogao_pattern(self):
        claim = {"summary": "据Gartner报告显示，2026年AI市场将达$5000亿", "sources": ["https://reuters.com/article"]}
        collected_by_url = {}
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_genju_yanjiu_pattern(self):
        claim = {"summary": "根据McKinsey研究指出，75%企业已采用AI", "sources": ["https://mckinsey.com/report"]}
        collected_by_url = {}
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_no_indirect_pattern(self):
        claim = {"summary": "PyTorch 2.0 achieved 97.3% accuracy", "sources": ["https://pytorch.org/blog"]}
        collected_by_url = {}
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_jucheng_pattern(self):
        claim = {"summary": "据称SWE-bench达到45%", "sources": ["https://example.com"]}
        collected_by_url = {}
        result = _is_indirect_source(claim, collected_by_url)
        assert isinstance(result, bool)

    def test_indirect_patterns_match_chinese(self):
        pattern1 = _INDIRECT_CITATION_PATTERNS[0]
        assert pattern1.search("据Gartner报告显示")
        assert pattern1.search("据McKinsey研究发现")

    def test_indirect_patterns_no_match_english(self):
        pattern1 = _INDIRECT_CITATION_PATTERNS[0]
        assert not pattern1.search("According to Gartner report")

    def test_english_indirect_pattern(self):
        pattern3 = _INDIRECT_CITATION_PATTERNS[2]
        assert pattern3.search("according to Gartner")
        assert pattern3.search("reported by McKinsey")

    def test_tier3_indirect_source(self):
        claim = {
            "summary": "AI市场将增长50%",
            "sources": ["https://blog.example.com/post"],
            "evidence_type": "official_data",
        }
        from scripts.lib.utils import normalize_url
        norm_url = normalize_url("https://blog.example.com/post")
        collected_by_url = {norm_url: {"source_tier": 3}}
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_tier1_not_indirect_by_tier(self):
        claim = {
            "summary": "AI市场将增长50%",
            "sources": ["https://arxiv.org/paper"],
            "evidence_type": "official_data",
        }
        collected_by_url = {"arxiv.org/paper": {"source_tier": 1}}
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_vendor_source_with_exact_precision(self):
        claim = {
            "summary": "Our product achieves 99.9% uptime",
            "sources": ["https://vendor.com/blog"],
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected_by_url = {}
        assert _is_indirect_source(claim, collected_by_url) is True


class TestEntityNumberConflict:
    def test_same_entity_same_number_pass(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [
                {"summary": "Python has 45% share", "sources": ["https://a.com"]},
                {"summary": "Python has 45% share again", "sources": ["https://b.com"]},
            ]}],
        })
        results = ClaimValidator(tmp_path, "tech_selection").check()
        r = _get_result(results, "entity_number_conflict")
        assert r.passed

    def test_same_entity_different_number_warn(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [
                {"summary": "Python has 45% share", "sources": ["https://a.com"]},
                {"summary": "Python has 52% share", "sources": ["https://b.com"]},
            ]}],
        })
        results = ClaimValidator(tmp_path, "tech_selection").check()
        r = _get_result(results, "entity_number_conflict")
        assert not r.passed
        assert "Python" in r.message

    def test_different_entities_pass(self, tmp_path):
        _write_json(tmp_path / "analysis.json", {
            "sections": [{"id": "s1", "claims": [
                {"summary": "Python has 45% share", "sources": ["https://a.com"]},
                {"summary": "Java has 52% share", "sources": ["https://b.com"]},
            ]}],
        })
        results = ClaimValidator(tmp_path, "tech_selection").check()
        r = _get_result(results, "entity_number_conflict")
        assert r.passed


class TestIsIndirectSourceUnit:
    def test_tier3_third_party_indirect(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "Market grows 15%", "sources": ["https://a.com"], "evidence_type": "third_party_estimate", "precision": "range"}
        collected = {normalize_url("https://a.com"): {"source_tier": 3}}
        assert _is_indirect_source(claim, collected) is True

    def test_tier3_official_data_indirect(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "$4.5B revenue", "sources": ["https://a.com"], "evidence_type": "official_data", "precision": "exact"}
        collected = {normalize_url("https://a.com"): {"source_tier": 3}}
        assert _is_indirect_source(claim, collected) is True

    def test_tier2_not_indirect(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "97.3% accuracy", "sources": ["https://a.com"], "evidence_type": "official_data", "precision": "exact"}
        collected = {normalize_url("https://a.com"): {"source_tier": 2}}
        assert _is_indirect_source(claim, collected) is False

    def test_vendor_source_type_exact_indirect(self):
        # Non-authoritative venue (tier 3) tagged vendor_benchmark still flips.
        from scripts.lib.utils import normalize_url
        claim = {
            "summary": "75% adoption",
            "sources": ["https://a.com"],
            "evidence_type": "official_data",
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected = {normalize_url("https://a.com"): {"source_tier": 3}}
        assert _is_indirect_source(claim, collected) is True

    def test_vendor_source_type_on_authoritative_venue_not_indirect(self):
        # An authoritative venue (tier 2) mislabeled vendor_benchmark must NOT
        # flip — authority is anchored on venue tier, not the agent label.
        from scripts.lib.utils import normalize_url
        claim = {
            "summary": "75% adoption",
            "sources": ["https://a.com"],
            "evidence_type": "official_data",
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected = {normalize_url("https://a.com"): {"source_tier": 2}}
        assert _is_indirect_source(claim, collected) is False

    def test_vendor_source_type_qualitative_not_indirect(self):
        from scripts.lib.utils import normalize_url
        claim = {
            "summary": "Widely adopted",
            "sources": ["https://a.com"],
            "evidence_type": "official_data",
            "precision": "qualitative",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected = {normalize_url("https://a.com"): {"source_tier": 2}}
        assert _is_indirect_source(claim, collected) is False

    def test_chinese_indirect_citation_host_mismatch(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "据Gartner报告显示增长15%", "sources": ["https://someblog.com/post"], "evidence_type": "official_data", "precision": "exact"}
        collected = {normalize_url("https://someblog.com/post"): {"source_tier": 3}}
        assert _is_indirect_source(claim, collected) is True

    def test_english_indirect_citation(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "According to Gartner, growth is 15%", "sources": ["https://someblog.com/post"], "evidence_type": "official_data", "precision": "exact"}
        collected = {normalize_url("https://someblog.com/post"): {"source_tier": 2}}
        assert _is_indirect_source(claim, collected) is True

    def test_indirect_citation_host_match_not_indirect(self):
        from scripts.lib.utils import normalize_url
        claim = {"summary": "据Gartner报告显示增长15%", "sources": ["https://gartner.com/report"], "evidence_type": "official_data", "precision": "exact"}
        collected = {normalize_url("https://gartner.com/report"): {"source_tier": 2}}
        assert _is_indirect_source(claim, collected) is False


class TestPrimarySourceRatio:
    def _setup(self, tmp_path, depth, collected, claims):
        _make_scope(tmp_path, goal_type="tech_selection", depth=depth, search_directions=[])
        _write_json(tmp_path / "collected.json", collected)
        _write_json(tmp_path / "analysis.json", {"sections": [{"id": "s1", "claims": claims}]})

    def test_passes_when_well_diversified(self, tmp_path):
        collected = [
            {"url": "https://arxiv.org/abs/1", "snippet": "", "source_tier": 1},
            {"url": "https://github.com/x", "snippet": "", "source_tier": 2},
            {"url": "https://medium.com/p", "snippet": "", "source_tier": 3},
        ]
        claims = [
            {"summary": "A", "sources": ["https://arxiv.org/abs/1"]},
            {"summary": "B", "sources": ["https://github.com/x"]},
        ]
        self._setup(tmp_path, "standard", collected, claims)
        r = _get_result(ClaimValidator(tmp_path, "tech_selection").check(), "primary_source_ratio")
        assert r.passed

    def test_warns_low_primary_ratio(self, tmp_path):
        collected = [
            {"url": "https://reddit.com/r1", "snippet": "", "source_tier": 4},
            {"url": "https://reddit.com/r2", "snippet": "", "source_tier": 4},
        ]
        claims = [
            {"summary": "A", "sources": ["https://reddit.com/r1"]},
            {"summary": "B", "sources": ["https://reddit.com/r2"]},
        ]
        self._setup(tmp_path, "standard", collected, claims)
        r = _get_result(ClaimValidator(tmp_path, "tech_selection").check(), "primary_source_ratio")
        assert not r.passed
        assert "Tier 1/2" in r.message

    def test_warns_single_platform_dominant(self, tmp_path):
        # All claims cite the same single platform (HF-only) -> single-community bias.
        collected = [
            {"url": "https://huggingface.co/m1", "snippet": "", "source_tier": 1},
            {"url": "https://huggingface.co/m2", "snippet": "", "source_tier": 2},
        ]
        claims = [
            {"summary": "A", "sources": ["https://huggingface.co/m1"]},
            {"summary": "B", "sources": ["https://huggingface.co/m2"]},
        ]
        self._setup(tmp_path, "standard", collected, claims)
        r = _get_result(ClaimValidator(tmp_path, "tech_selection").check(), "primary_source_ratio")
        assert not r.passed
        assert "single platform" in r.message.lower()

    def test_skipped_for_quick_depth(self, tmp_path):
        collected = [{"url": "https://reddit.com/r1", "snippet": "", "source_tier": 4}]
        claims = [{"summary": "A", "sources": ["https://reddit.com/r1"]}]
        self._setup(tmp_path, "quick", collected, claims)
        r = _get_result(ClaimValidator(tmp_path, "tech_selection").check(), "primary_source_ratio")
        assert r.passed
        assert "quick" in r.message.lower()
