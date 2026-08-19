import pytest
from pathlib import Path

from intent_research.reporter import (
    _resolve_ref_markers,
    _render_references,
    _render_verification_summary,
    _render_dq_summary,
    sections_to_markdown,
    generate_report,
    build_front_matter,
)
from intent_research.lib.utils import write_json, normalize_url


class TestResolveRefMarkers:
    def test_single_ref(self):
        ref_map = {}
        result = _resolve_ref_markers("see {{ref:http://a.com}}", ref_map)
        assert "[1]" in result
        assert normalize_url("http://a.com") in ref_map

    def test_duplicate_ref_same_number(self):
        ref_map = {}
        result = _resolve_ref_markers("see {{ref:http://a.com}} and {{ref:http://a.com}}", ref_map)
        assert result.count("[1]") == 2
        assert len(ref_map) == 1

    def test_multiple_refs(self):
        ref_map = {}
        result = _resolve_ref_markers("{{ref:http://a.com}} {{ref:http://b.com}}", ref_map)
        assert "[1]" in result
        assert "[2]" in result


class TestRenderReferences:
    def test_with_tier_labels(self):
        ref_map = {normalize_url("http://arxiv.org/paper"): 1}
        collected = [{"url": "http://arxiv.org/paper", "title": "Paper", "source_tier": 1}]
        result = _render_references(ref_map, collected)
        assert "Tier 1" in result
        assert "[1]" in result

    def test_empty_ref_map(self):
        result = _render_references({}, [])
        assert result == ""


class TestRenderVerificationSummary:
    def test_with_verification_data(self):
        analysis = {"sections": [{"claims": [
            {"source_verification": "source_confirmed"},
            {"source_verification": "source_indirect"},
            {"source_verification": "source_absent"},
        ]}]}
        result = _render_verification_summary(analysis)
        assert "Confirmed" in result
        assert "Indirect" in result
        assert "Absent" in result

    def test_no_claims(self):
        analysis = {"sections": [{"claims": []}]}
        result = _render_verification_summary(analysis)
        assert result == ""


class TestRenderDQSummary:
    def test_answered_and_unanswered(self):
        scope = {"decision_questions": [
            {"id": "dq1", "question": "What is X?"},
            {"id": "dq2", "question": "How does Y work?"},
        ]}
        analysis = {"sections": [{"decision_questions_answered": ["dq1"]}]}
        result = _render_dq_summary(scope, analysis)
        assert "\u2713" in result
        assert "\u2717" in result

    def test_no_decision_questions(self):
        result = _render_dq_summary({}, {"sections": []})
        assert result == ""


class TestBuildFrontMatter:
    def test_basic(self):
        result = build_front_matter("Test Topic", "tech_selection", "test scope", 5)
        assert "topic: Test Topic" in result
        assert "goal_type: tech_selection" in result
        assert "source_count: 5" in result
        assert "verification_required: true" in result


class TestSectionsToMarkdown:
    def test_basic_section(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [{
                "id": "s1",
                "title": "Section One",
                "content": "Some text {{ref:http://a.com}}",
                "claims": [{
                    "summary": "X is 98%",
                    "sources": ["http://a.com"],
                    "source_verification": "source_confirmed",
                }],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        result = sections_to_markdown(analysis, collected)
        assert "## Section One" in result
        assert "[1]" in result

    def test_absent_marker(self):
        analysis = {
            "goal_type": "fact_check",
            "sections": [{
                "id": "s1",
                "title": "S1",
                "content": "",
                "claims": [{
                    "summary": "X is 95%",
                    "sources": ["http://a.com"],
                    "source_verification": "source_absent",
                }],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 2}]
        result = sections_to_markdown(analysis, collected)
        assert "\u2020" in result

    def test_indirect_marker(self):
        analysis = {
            "goal_type": "fact_check",
            "sections": [{
                "id": "s1",
                "title": "S1",
                "content": "",
                "claims": [{
                    "summary": "X is 95%",
                    "sources": ["http://a.com"],
                    "source_verification": "source_indirect",
                }],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 3}]
        result = sections_to_markdown(analysis, collected)
        assert "\u2021" in result


class TestGenerateReport:
    def test_full_report(self, tmp_path):
        scope = {
            "topic": "Test",
            "goal_type": "tech_selection",
            "scope_description": "test scope",
            "audience": "engineers",
            "report_language": "en",
            "decision_questions": [{"id": "dq1", "question": "What is X?"}],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        analysis = {
            "topic": "Test",
            "goal_type": "tech_selection",
            "sections": [{
                "id": "s1",
                "title": "Section One",
                "content": "X is good {{ref:http://a.com}}",
                "claims": [{
                    "summary": "X is 98%",
                    "sources": ["http://a.com"],
                    "evidence_type": "official_data",
                    "precision": "exact",
                    "source_verification": "source_confirmed",
                }],
                "decision_questions_answered": ["dq1"],
                "key_insights": [],
                "tensions": [],
            }],
        }
        write_json(scope, tmp_path / "scope.json")
        write_json(analysis, tmp_path / "analysis.json")
        write_json(collected, tmp_path / "collected.json")

        result = generate_report(tmp_path / "analysis.json", tmp_path / "scope.json")
        assert "---" in result
        assert "## Section One" in result
        assert "verification_required: true" in result


class TestReporterEdgeCases:
    def test_zh_language_labels(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [{
                "id": "s1",
                "title": "测试节",
                "content": "内容 {{ref:http://a.com}}",
                "claims": [{
                    "summary": "X 是 98%",
                    "sources": ["http://a.com"],
                    "source_verification": "source_confirmed",
                }],
                "key_insights": [{"summary": "核心发现", "sources": ["http://a.com"]}],
                "tensions": [{"summary": "张力描述", "sources": ["http://a.com"]}],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        result = sections_to_markdown(analysis, collected, lang="zh")
        assert "参考文献" in result
        assert "核心发现" in result
        assert "张力" in result

    def test_order_field_sorting(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [
                {"id": "s2", "title": "Second", "content": "", "claims": [], "order": 2},
                {"id": "s1", "title": "First", "content": "", "claims": [], "order": 1},
            ],
        }
        result = sections_to_markdown(analysis, [], lang="en")
        first_pos = result.index("## First")
        second_pos = result.index("## Second")
        assert first_pos < second_pos

    def test_key_insights_with_source_refs(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [{
                "id": "s1",
                "title": "S1",
                "content": "text {{ref:http://a.com}}",
                "claims": [],
                "key_insights": [{"summary": "Important finding", "sources": ["http://a.com"]}],
                "tensions": [],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        result = sections_to_markdown(analysis, collected, lang="en")
        assert "Important finding" in result
        assert "[1]" in result

    def test_tensions_rendered(self):
        analysis = {
            "goal_type": "tech_selection",
            "sections": [{
                "id": "s1",
                "title": "S1",
                "content": "text {{ref:http://a.com}}",
                "claims": [],
                "key_insights": [],
                "tensions": [{"summary": "Conflicting data", "sources": ["http://a.com"]}],
            }],
        }
        collected = [{"url": "http://a.com", "title": "A", "source_tier": 1}]
        result = sections_to_markdown(analysis, collected, lang="en")
        assert "Conflicting data" in result

    def test_no_sections(self):
        analysis = {"goal_type": "tech_selection", "sections": []}
        result = sections_to_markdown(analysis, [], lang="en")
        assert isinstance(result, str)
