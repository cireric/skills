from __future__ import annotations

from pathlib import Path

from scripts.lib.check_types import CheckResult
from scripts.artifact_checks import (
    _count_words,
    _has_concrete_name,
    _has_valid_number,
    check_content_concreteness,
)


class TestCountWords:
    def test_pure_english(self, tmp_path):
        assert _count_words("This is a test") == 4

    def test_pure_chinese_segments(self, tmp_path):
        assert _count_words("性能优秀 功能强大") == 2

    def test_mixed(self, tmp_path):
        assert _count_words("This is 微服务架构 test") == 4

    def test_empty_string(self, tmp_path):
        assert _count_words("") == 0

    def test_cjk_punctuation_only(self, tmp_path):
        assert _count_words("，。！？") == 0


class TestVaguePhraseDetection:
    def test_no_vague_phrases_pass(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Kubernetes handles 5000 nodes. Docker is widely used.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed

    def test_density_exceeds_threshold_warns(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "market_analysis",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "性能良好。值得关注。较为突出。比较突出。相对较好。较为成熟。相当不错。比较强大。较为完善。比较稳定。比较丰富。100 nodes.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "market_analysis")
        assert not result.passed
        assert result.level == "WARN"
        assert "vague" in result.message.lower()

    def test_density_below_threshold_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Kubernetes handles 5000 nodes and Docker is fairly well supported in production environments with extensive monitoring and strong ecosystem.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed


class TestNumberAbsence:
    def test_tech_selection_without_numbers_warn(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Kubernetes is a container orchestration platform with strong ecosystem support.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "no valid numbers" in result.message.lower()

    def test_with_numbers_pass(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Kubernetes handles 5000 nodes per cluster. Docker is widely used.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed

    def test_short_section_skip(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Short.",
                        "claims": [],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed

    def test_year_exclusion(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Released in 2024.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "no valid numbers" in result.message.lower()

    def test_version_exclusion(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Version v2.0 released.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "no valid numbers" in result.message.lower()


class TestNameAbsence:
    def test_no_concrete_names_warn_strict(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "性能良好。值得关注。较为突出。5000 nodes. 性能良好。值得关注。较为突出。",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "no concrete names" in result.message.lower()

    def test_no_concrete_names_warn_others(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "market_analysis",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "性能良好。值得关注。较为突出。5000 nodes. 性能良好。值得关注。较为突出。性能良好。值得关注。较为突出。",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "market_analysis")
        assert not result.passed
        assert result.level == "WARN"
        assert "no concrete names" in result.message.lower()

    def test_english_name_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "Kubernetes handles 5000 nodes. Docker is quite capable and very well supported in production environments with extensive monitoring and strong ecosystem.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed

    def test_backtick_name_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "`my_service` handles 5000 nodes.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed

    def test_cjk_term_passes(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "微服务架构 handles 5000 nodes.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    }
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert result.passed


class TestMultipleIssues:
    def test_multiple_sections_different_issues(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "Overview",
                        "content": "性能良好。值得关注。较为突出。",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Comparison",
                        "content": "Kubernetes handles 5000 nodes.",
                        "claims": [{"summary": "Claim", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        result = check_content_concreteness(tmp_path, "tech_selection")
        assert not result.passed
        assert result.level == "WARN"
        assert "overview" in result.message.lower()


class TestHasValidNumber:
    def test_year_excluded(self):
        assert not _has_valid_number("Released in 2024")

    def test_version_excluded(self):
        assert not _has_valid_number("Version v2.0")

    def test_list_item_excluded(self):
        assert not _has_valid_number("1. First item")

    def test_valid_number_found(self):
        assert _has_valid_number("Handles 5000 nodes")

    def test_decimal_number(self):
        assert _has_valid_number("Latency is 12.5")


class TestHasConcreteName:
    def test_english_proper_noun(self):
        assert _has_concrete_name("It is great. Kubernetes is great.")

    def test_backtick_identifier(self):
        assert _has_concrete_name("Use `my_service` for this.")

    def test_cjk_technical_term(self):
        assert _has_concrete_name("微服务架构 is great.")

    def test_stop_word_filtered(self):
        assert not _has_concrete_name("的")

    def test_no_name(self):
        assert not _has_concrete_name("it is good.")
