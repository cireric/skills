import pytest
from pathlib import Path

from intent_research.verify import (
    _normalize_numbers,
    _number_found_in_source,
    _is_indirect_source,
    _compute_source_verification,
    verify_claims,
)
from intent_research.lib.utils import write_json, normalize_url, build_collected_by_url


class TestNormalizeNumbers:
    def test_plain_integer(self):
        assert "42" in _normalize_numbers("42 items")

    def test_comma_separated(self):
        assert "1000" in _normalize_numbers("1,000 items")

    def test_percentage(self):
        assert "98" in _normalize_numbers("98%")

    def test_with_unit(self):
        assert "200" in _normalize_numbers("200ms")

    def test_range_percentage(self):
        nums = _normalize_numbers("45-48%")
        assert "45" in nums
        assert "48" in nums

    def test_billion(self):
        nums = _normalize_numbers("$1.5B")
        assert "1500000000" in nums

    def test_no_numbers(self):
        assert _normalize_numbers("qualitative claim") == set()


class TestNumberFoundInSource:
    def test_number_present(self):
        assert _number_found_in_source("revenue is $1.5B", "revenue reached $1.5B") == "source_confirmed"

    def test_number_absent(self):
        assert _number_found_in_source("revenue is $2B", "revenue reached $1.5B") == "source_absent"

    def test_qualitative_claim_confirmed(self):
        assert _number_found_in_source("X is good", "X is good") == "source_confirmed"


class TestIsIndirectSource:
    def test_low_tier_official_data(self):
        claim = {
            "summary": "X has 90% accuracy",
            "sources": ["http://medium.com/article"],
            "evidence_type": "official_data",
        }
        collected_by_url = {
            normalize_url("http://medium.com/article"): {"source_tier": 3}
        }
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_high_tier_official_data(self):
        claim = {
            "summary": "X has 90% accuracy",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {"source_tier": 1}
        }
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_vendor_benchmark_exact(self):
        claim = {
            "summary": "X is 10x faster",
            "sources": ["http://medium.com/vendor"],
            "evidence_type": "independent_benchmark",
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected_by_url = {
            normalize_url("http://medium.com/vendor"): {"source_tier": 3}
        }
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_vendor_benchmark_tier2_source_not_indirect(self):
        claim = {
            "summary": "X is 10x faster",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "independent_benchmark",
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {"source_tier": 1}
        }
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_vendor_benchmark_mixed_sources_indirect(self):
        claim = {
            "summary": "X is 10x faster",
            "sources": ["http://arxiv.org/paper", "http://medium.com/vendor"],
            "evidence_type": "independent_benchmark",
            "precision": "exact",
            "source_metadata": {"source_type": "vendor_benchmark"},
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {"source_tier": 1},
            normalize_url("http://medium.com/vendor"): {"source_tier": 3},
        }
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_citation_entity_mismatch(self):
        claim = {
            "summary": "according to OpenAI, GPT-4 achieves 90%",
            "sources": ["http://medium.com/analysis"],
        }
        collected_by_url = {
            normalize_url("http://medium.com/analysis"): {"source_tier": 3}
        }
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_citation_entity_matches_host(self):
        claim = {
            "summary": "according to OpenAI, GPT-4 achieves 90%",
            "sources": ["http://openai.com/blog"],
        }
        collected_by_url = {
            normalize_url("http://openai.com/blog"): {"source_tier": 2}
        }
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_citation_short_entity_no_false_positive(self):
        claim = {
            "summary": "according to AI, models are improving",
            "sources": ["http://ai.com/research"],
        }
        collected_by_url = {
            normalize_url("http://ai.com/research"): {"source_tier": 3}
        }
        assert _is_indirect_source(claim, collected_by_url) is False

    def test_citation_entity_substring_no_false_match(self):
        claim = {
            "summary": "according to AI, models are improving",
            "sources": ["http://sailai.com/research"],
        }
        collected_by_url = {
            normalize_url("http://sailai.com/research"): {"source_tier": 3}
        }
        assert _is_indirect_source(claim, collected_by_url) is True

    def test_no_indirect_signals(self):
        claim = {
            "summary": "X is 90% accurate",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "independent_benchmark",
            "precision": "range",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {"source_tier": 1}
        }
        assert _is_indirect_source(claim, collected_by_url) is False


class TestComputeSourceVerification:
    def test_confirmed_number(self):
        claim = {
            "summary": "accuracy is 98%",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {
                "source_tier": 1,
                "fetched_content": "the accuracy is 98%",
                "snippet": "",
            }
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_confirmed"

    def test_absent_number(self):
        claim = {
            "summary": "accuracy is 95%",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {
                "source_tier": 1,
                "fetched_content": "the accuracy is 98%",
                "snippet": "",
            }
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_absent"

    def test_indirect_priority_over_confirmed(self):
        claim = {
            "summary": "accuracy is 98%",
            "sources": ["http://medium.com/article"],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        collected_by_url = {
            normalize_url("http://medium.com/article"): {
                "source_tier": 3,
                "fetched_content": "accuracy is 98%",
                "snippet": "",
            }
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_indirect"

    def test_qualitative_confirmed(self):
        claim = {
            "summary": "X is widely adopted",
            "sources": ["http://github.com/repo"],
            "evidence_type": "qualitative_trend",
            "precision": "qualitative",
        }
        collected_by_url = {
            normalize_url("http://github.com/repo"): {
                "source_tier": 2,
                "fetched_content": "X is widely adopted",
                "snippet": "",
            }
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_confirmed"


class TestVerifyClaims:
    def test_verify_writes_back(self, tmp_path):
        collected = [
            {
                "url": "http://arxiv.org/paper",
                "source_tier": 1,
                "fetched_content": "accuracy is 98%",
                "snippet": "",
            }
        ]
        analysis = {
            "sections": [{
                "id": "s1",
                "claims": [{
                    "summary": "accuracy is 98%",
                    "sources": ["http://arxiv.org/paper"],
                    "evidence_type": "official_data",
                    "precision": "exact",
                }],
            }]
        }
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")

        result = verify_claims(tmp_path)
        assert result["total"] == 1
        assert result["source_confirmed"] == 1

    def test_verify_missing_files(self, tmp_path):
        result = verify_claims(tmp_path)
        assert "error" in result

    def test_verify_with_source_file(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("accuracy is 98%", encoding="utf-8")

        collected = [
            {
                "url": "http://arxiv.org/paper",
                "source_tier": 1,
                "source_file": "sources/abc123.md",
                "snippet": "",
            }
        ]
        analysis = {
            "sections": [{
                "id": "s1",
                "claims": [{
                    "summary": "accuracy is 98%",
                    "sources": ["http://arxiv.org/paper"],
                    "evidence_type": "official_data",
                    "precision": "exact",
                }],
            }]
        }
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")

        result = verify_claims(tmp_path)
        assert result["source_confirmed"] == 1


class TestVerifyEdgeCases:
    def test_multi_source_confirmed_plus_absent(self):
        claim = {
            "summary": "accuracy is 98%",
            "sources": ["http://arxiv.org/paper", "http://other.com/page"],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {
                "source_tier": 1,
                "fetched_content": "accuracy is 98%",
                "snippet": "",
            },
            normalize_url("http://other.com/page"): {
                "source_tier": 2,
                "fetched_content": "no relevant data here",
                "snippet": "",
            },
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_confirmed"

    def test_source_file_preferred_over_fetched_content(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("accuracy is 99%", encoding="utf-8")

        collected = [{
            "url": "http://arxiv.org/paper",
            "source_tier": 1,
            "source_file": "sources/abc123.md",
            "fetched_content": "accuracy is 98%",
            "snippet": "",
        }]
        analysis = {"sections": [{"id": "s1", "claims": [{
            "summary": "accuracy is 99%",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
            "precision": "exact",
        }]}]}
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")

        result = verify_claims(tmp_path)
        assert result["source_confirmed"] == 1

    def test_cjk_number_in_claim(self):
        claim = {
            "summary": "准确率达到 98%",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        collected_by_url = {
            normalize_url("http://arxiv.org/paper"): {
                "source_tier": 1,
                "fetched_content": "准确率达到 98%",
                "snippet": "",
            }
        }
        result = _compute_source_verification(claim, collected_by_url, Path("/nonexistent"))
        assert result == "source_confirmed"

    def test_no_sources_in_claim(self):
        claim = {
            "summary": "accuracy is 98%",
            "sources": [],
            "evidence_type": "official_data",
            "precision": "exact",
        }
        result = _compute_source_verification(claim, {}, Path("/nonexistent"))
        assert result == "source_absent"

    def test_empty_source_file_falls_back(self, tmp_path):
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("", encoding="utf-8")

        collected = [{
            "url": "http://arxiv.org/paper",
            "source_tier": 1,
            "source_file": "sources/abc123.md",
            "fetched_content": "accuracy is 98%",
            "snippet": "",
        }]
        analysis = {"sections": [{"id": "s1", "claims": [{
            "summary": "accuracy is 98%",
            "sources": ["http://arxiv.org/paper"],
            "evidence_type": "official_data",
            "precision": "exact",
        }]}]}
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")

        result = verify_claims(tmp_path)
        assert result["source_confirmed"] == 1
