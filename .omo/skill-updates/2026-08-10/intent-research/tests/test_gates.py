import pytest
from pathlib import Path

from scripts.gates import (
    check_scope,
    check_collected,
    check_source_sufficiency,
    check_precision_rules,
    check_ref_markers,
    run_all_checks,
)
from scripts.lib.utils import write_json, normalize_url


class TestCheckScope:
    def test_valid_scope(self):
        scope = {"topic": "Test", "goal_type": "tech_selection", "scope_description": "test"}
        results = check_scope(scope)
        assert all(r.level == "PASS" for r in results)

    def test_missing_topic(self):
        scope = {"goal_type": "tech_selection"}
        results = check_scope(scope)
        assert any(r.name == "scope_topic" and r.level == "BLOCKER" for r in results)

    def test_invalid_goal_type(self):
        scope = {"topic": "Test", "goal_type": "invalid"}
        results = check_scope(scope)
        assert any(r.name == "scope_goal_type" and r.level == "BLOCKER" for r in results)

    def test_all_valid_goal_types(self):
        for gt in ["exploratory", "panoramic_understanding", "tech_selection",
                    "feasibility_assessment", "competitive_comparison", "academic_research",
                    "fact_check", "background_check", "market_analysis", "other"]:
            scope = {"topic": "Test", "goal_type": gt}
            results = check_scope(scope)
            assert all(r.level == "PASS" for r in results), f"goal_type={gt} failed"

    def test_cjk_requires_english_title(self):
        scope = {"topic": "测试主题", "goal_type": "tech_selection", "scope_description": "test"}
        results = check_scope(scope)
        assert any(r.name == "scope_english_title" and r.level == "BLOCKER" for r in results)

    def test_cjk_with_english_title(self):
        scope = {"topic": "测试", "goal_type": "tech_selection", "scope_description": "test", "english_title": "Test"}
        results = check_scope(scope)
        assert all(r.level == "PASS" for r in results)

    def test_korean_requires_english_title(self):
        scope = {"topic": "테스트", "goal_type": "tech_selection"}
        results = check_scope(scope)
        assert any(r.name == "scope_english_title" and r.level == "BLOCKER" for r in results)

    def test_accented_european_no_english_title_required(self):
        scope = {"topic": "Überblick", "goal_type": "tech_selection"}
        results = check_scope(scope)
        assert not any(r.name == "scope_english_title" and r.level == "BLOCKER" for r in results)


class TestCheckCollected:
    def test_empty_collected(self):
        results = check_collected([], {"search_directions": ["a"]})
        assert any(r.name == "collected_empty" and r.level == "BLOCKER" for r in results)

    def test_direction_coverage_missing(self):
        collected = [{"url": "http://a.com", "direction": "a", "source_tier": 1}]
        results = check_collected(collected, {"search_directions": ["a", "b"]})
        assert any(r.name == "direction_coverage" and r.level == "WARN" for r in results)

    def test_direction_coverage_ok(self):
        collected = [
            {"url": "http://a.com", "direction": "a", "source_tier": 1},
            {"url": "http://b.com", "direction": "b", "source_tier": 2},
        ]
        results = check_collected(collected, {"search_directions": ["a", "b"]})
        assert any(r.name == "direction_coverage" and r.level == "PASS" for r in results)

    def test_missing_direction_field(self):
        collected = [{"url": "http://a.com", "source_tier": 1}]
        results = check_collected(collected, {"search_directions": []})
        assert any(r.name == "direction_tagging" and r.level == "WARN" for r in results)

    def test_other_direction_not_counted(self):
        collected = [{"url": "http://a.com", "direction": "other", "source_tier": 1}]
        results = check_collected(collected, {"search_directions": ["a"]})
        assert any(r.name == "direction_coverage" and r.level == "WARN" for r in results)


class TestCheckSourceSufficiency:
    def test_no_tier12(self):
        collected = [
            {"url": "http://a.com", "source_tier": 3},
            {"url": "http://b.com", "source_tier": 4},
        ]
        scope = {"decision_questions": [{"id": "dq1", "question": "What is X?"}]}
        results = check_source_sufficiency(collected, scope)
        assert any(r.name == "source_sufficiency" and r.level == "WARN" for r in results)

    def test_per_dq_coverage_pass(self):
        collected = [
            {"url": "http://a.com", "source_tier": 1},
            {"url": "http://b.com", "source_tier": 3},
        ]
        scope = {"decision_questions": [{"id": "dq1", "question": "What is X?"}]}
        analysis = {"sections": [{
            "id": "s1",
            "decision_questions_answered": ["dq1"],
            "claims": [{"sources": ["http://a.com"]}],
        }]}
        results = check_source_sufficiency(collected, scope, analysis)
        assert any(r.name == "source_sufficiency" and r.level == "PASS" for r in results)

    def test_per_dq_coverage_dq_lacks_tier12(self):
        collected = [
            {"url": "http://a.com", "source_tier": 1},
            {"url": "http://b.com", "source_tier": 3},
        ]
        scope = {"decision_questions": [
            {"id": "dq1", "question": "What is X?"},
            {"id": "dq2", "question": "What is Y?"},
        ]}
        analysis = {"sections": [{
            "id": "s1",
            "decision_questions_answered": ["dq1"],
            "claims": [{"sources": ["http://a.com"]}],
        }]}
        results = check_source_sufficiency(collected, scope, analysis)
        assert any(r.name == "source_sufficiency" and r.level == "WARN" for r in results)
        warn = [r for r in results if r.name == "source_sufficiency" and r.level == "WARN"][0]
        assert "dq2" in warn.message.lower() or "Y" in warn.message

    def test_no_decision_questions(self):
        results = check_source_sufficiency([], {"decision_questions": []})
        assert any(r.name == "source_sufficiency" and r.level == "PASS" for r in results)

    def test_low_tier12_ratio(self):
        collected = [
            {"url": "http://a.com", "source_tier": 3},
            {"url": "http://b.com", "source_tier": 3},
            {"url": "http://c.com", "source_tier": 3},
            {"url": "http://d.com", "source_tier": 4},
            {"url": "http://e.com", "source_tier": 4},
        ]
        scope = {"decision_questions": [{"id": "dq1", "question": "What?"}]}
        results = check_source_sufficiency(collected, scope)
        assert any(r.name == "source_sufficiency" and r.level == "WARN" for r in results)


class TestCheckPrecisionRules:
    def test_valid_claims(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X is 98%", "sources": ["http://a.com"], "evidence_type": "official_data", "precision": "exact"},
            {"summary": "Y is about 50%", "sources": ["http://b.com"], "evidence_type": "expert_opinion", "precision": "qualitative"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "PASS" for r in results)

    def test_precision_inflation(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X is 90%", "sources": ["http://a.com"], "evidence_type": "expert_opinion", "precision": "exact"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "BLOCKER" for r in results)

    def test_third_party_estimate_exact_blocked(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X is 90%", "sources": [], "evidence_type": "third_party_estimate", "precision": "exact"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "BLOCKER" for r in results)

    def test_invalid_evidence_type(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X", "sources": [], "evidence_type": "vendor_claim", "precision": "qualitative"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "BLOCKER" for r in results)

    def test_invalid_precision(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X", "sources": [], "evidence_type": "official_data", "precision": "approximate"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "BLOCKER" for r in results)


class TestCheckRefMarkers:
    def test_valid_refs(self):
        analysis = {"sections": [{"id": "s1", "content": "see {{ref:http://a.com}}"}]}
        collected_urls = {normalize_url("http://a.com")}
        results = check_ref_markers(analysis, collected_urls)
        assert any(r.name == "ref_marker_validity" and r.level == "PASS" for r in results)

    def test_missing_ref(self):
        analysis = {"sections": [{"id": "s1", "content": "see {{ref:http://missing.com}}"}]}
        collected_urls = {normalize_url("http://a.com")}
        results = check_ref_markers(analysis, collected_urls)
        assert any(r.name == "ref_marker_validity" and r.level == "BLOCKER" for r in results)

    def test_no_refs_in_content(self):
        analysis = {"sections": [{"id": "s1", "content": "plain text"}]}
        collected_urls = {normalize_url("http://a.com")}
        results = check_ref_markers(analysis, collected_urls)
        assert any(r.name == "ref_marker_validity" and r.level == "PASS" for r in results)


class TestRunAllChecks:
    def test_empty_workdir(self, tmp_path):
        results = run_all_checks(tmp_path)
        assert len(results) == 0

    def test_full_pipeline_pass(self, tmp_path):
        scope = {
            "topic": "Test", "goal_type": "tech_selection",
            "scope_description": "test", "search_directions": ["a"],
            "decision_questions": [{"id": "dq1", "question": "What is a?"}],
        }
        collected = [{"url": "http://a.com", "source_tier": 1, "direction": "a", "title": "A"}]
        analysis = {"sections": [{"id": "s1", "title": "S1", "content": "see {{ref:http://a.com}}", "claims": [
            {"summary": "a is good", "sources": ["http://a.com"], "evidence_type": "official_data", "precision": "exact"}
        ], "key_insights": [], "tensions": []}]}
        write_json(scope, tmp_path / "scope.json")
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")
        results = run_all_checks(tmp_path)
        blocker_names = [r.name for r in results if r.level == "BLOCKER"]
        assert not blocker_names, f"Unexpected blockers: {blocker_names}"

    def test_cjk_scope_no_english_title(self, tmp_path):
        scope = {"topic": "测试", "goal_type": "tech_selection", "scope_description": "test"}
        write_json(scope, tmp_path / "scope.json")
        results = run_all_checks(tmp_path)
        assert any(r.name == "scope_english_title" and r.level == "BLOCKER" for r in results)


class TestCheckScopeEdgeCases:
    def test_scope_description_missing_not_blocker(self):
        scope = {"topic": "Test", "goal_type": "tech_selection"}
        results = check_scope(scope)
        assert not any(r.level == "BLOCKER" for r in results)

    def test_empty_topic_string(self):
        scope = {"topic": "", "goal_type": "tech_selection"}
        results = check_scope(scope)
        assert any(r.name == "scope_topic" and r.level == "BLOCKER" for r in results)

    def test_japanese_requires_english_title(self):
        scope = {"topic": "テスト", "goal_type": "tech_selection"}
        results = check_scope(scope)
        assert any(r.name == "scope_english_title" and r.level == "BLOCKER" for r in results)


class TestCheckCollectedEdgeCases:
    def test_no_search_directions_no_direction_check(self):
        collected = [{"url": "http://a.com", "source_tier": 1}]
        results = check_collected(collected, {"search_directions": []})
        assert not any(r.name == "direction_coverage" for r in results)

    def test_all_other_direction(self):
        collected = [
            {"url": "http://a.com", "direction": "other", "source_tier": 1},
            {"url": "http://b.com", "direction": "other", "source_tier": 2},
        ]
        results = check_collected(collected, {"search_directions": ["a"]})
        assert any(r.name == "direction_coverage" and r.level == "WARN" for r in results)


class TestCheckSourceSufficiencyEdgeCases:
    def test_missing_source_tier_treated_as_low(self):
        collected = [{"url": "http://a.com"}]
        scope = {"decision_questions": [{"id": "dq1", "question": "What?"}]}
        results = check_source_sufficiency(collected, scope)
        assert any(r.name == "source_sufficiency" and r.level == "WARN" for r in results)

    def test_analysis_no_sections(self):
        collected = [{"url": "http://a.com", "source_tier": 1}]
        scope = {"decision_questions": [{"id": "dq1", "question": "What?"}]}
        analysis = {"sections": []}
        results = check_source_sufficiency(collected, scope, analysis)
        assert any(r.name == "source_sufficiency" and r.level == "WARN" for r in results)


class TestCheckPrecisionRulesEdgeCases:
    def test_no_claims_pass(self):
        analysis = {"sections": [{"id": "s1", "claims": []}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "PASS" for r in results)

    def test_no_sections(self):
        analysis = {"sections": []}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "PASS" for r in results)

    def test_qualitative_trend_exact_blocked(self):
        analysis = {"sections": [{"id": "s1", "claims": [
            {"summary": "X", "sources": [], "evidence_type": "qualitative_trend", "precision": "exact"},
        ]}]}
        results = check_precision_rules(analysis)
        assert any(r.name == "precision_rules" and r.level == "BLOCKER" for r in results)


class TestRunAllChecksEdgeCases:
    def test_only_collected_no_analysis(self, tmp_path):
        scope = {"topic": "Test", "goal_type": "tech_selection", "search_directions": ["a"]}
        collected = [{"url": "http://a.com", "source_tier": 1, "direction": "a"}]
        write_json(scope, tmp_path / "scope.json")
        write_json(collected, tmp_path / "collected.json")
        results = run_all_checks(tmp_path)
        assert not any(r.level == "BLOCKER" for r in results)

    def test_only_scope(self, tmp_path):
        scope = {"topic": "Test", "goal_type": "tech_selection"}
        write_json(scope, tmp_path / "scope.json")
        results = run_all_checks(tmp_path)
        assert all(r.level == "PASS" for r in results)

    def test_source_sufficiency_sees_analysis(self, tmp_path):
        scope = {
            "topic": "Test", "goal_type": "tech_selection",
            "search_directions": ["a"],
            "decision_questions": [{"id": "dq1", "question": "What is a?"}],
        }
        collected = [{"url": "http://a.com", "source_tier": 1, "direction": "a"}]
        analysis = {"sections": [{"id": "s1", "title": "S1", "content": "see {{ref:http://a.com}}", "claims": [
            {"summary": "a is good", "sources": ["http://a.com"], "evidence_type": "official_data", "precision": "exact"}
        ], "key_insights": [], "tensions": [], "decision_questions_answered": ["dq1"]}]}
        write_json(scope, tmp_path / "scope.json")
        write_json(collected, tmp_path / "collected.json")
        write_json(analysis, tmp_path / "analysis.json")
        results = run_all_checks(tmp_path)
        assert any(r.name == "source_sufficiency" and r.level == "PASS" for r in results)
