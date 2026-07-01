from __future__ import annotations

from scripts.lib.exceptions import ValidationError
from scripts.lib.schemas import (
    validate_scope,
    validate_analysis,
    validate_collected,
)


def _scope(**overrides) -> dict:
    base = {
        "topic": "test topic",
        "goal_type": "tech_selection",
        "depth": "standard",
        "audience": "engineer",
        "scope_description": "test desc",
        "search_directions": ["AI", "ML"],
    }
    base.update(overrides)
    return base


class TestValidationError:
    def test_fields(self):
        e = ValidationError("topic", "missing")
        assert e.field == "topic"
        assert e.message == "missing"

    def test_equality(self):
        a = ValidationError("f", "m")
        b = ValidationError("f", "m")
        assert a == b


class TestValidateScopeValid:
    def test_minimal_valid(self):
        errors = validate_scope(_scope())
        assert errors == []

    def test_with_report_language(self):
        errors = validate_scope(_scope(report_language="zh"))
        assert errors == []

    def test_all_goal_types(self):
        for gt in ("exploratory", "panoramic_understanding", "tech_selection",
                    "feasibility_assessment", "competitive_comparison", "academic_research",
                    "fact_check", "background_check", "market_analysis", "other"):
            errors = validate_scope(_scope(goal_type=gt))
            assert not errors, f"goal_type={gt} should be valid"

    def test_all_depths(self):
        for d in ("quick", "standard", "deep"):
            errors = validate_scope(_scope(depth=d))
            assert not errors, f"depth={d} should be valid"

    def test_all_audiences(self):
        for a in ("CTO", "engineer", "researcher", "general"):
            errors = validate_scope(_scope(audience=a))
            assert not errors, f"audience={a} should be valid"


class TestValidateScopeMissingFields:
    def test_missing_topic(self):
        data = _scope()
        del data["topic"]
        errors = validate_scope(data)
        assert any(e.field == "topic" and "missing" in e.message for e in errors)

    def test_missing_goal_type(self):
        data = _scope()
        del data["goal_type"]
        errors = validate_scope(data)
        assert any(e.field == "goal_type" for e in errors)

    def test_missing_depth(self):
        data = _scope()
        del data["depth"]
        errors = validate_scope(data)
        assert any(e.field == "depth" for e in errors)

    def test_missing_audience(self):
        data = _scope()
        del data["audience"]
        errors = validate_scope(data)
        assert any(e.field == "audience" for e in errors)

    def test_missing_search_directions(self):
        data = _scope()
        del data["search_directions"]
        errors = validate_scope(data)
        assert any(e.field == "search_directions" for e in errors)


class TestValidateScopeTypeErrors:
    def test_topic_not_str(self):
        errors = validate_scope(_scope(topic=123))
        assert any(e.field == "topic" and "expected str" in e.message for e in errors)

    def test_goal_type_not_str(self):
        errors = validate_scope(_scope(goal_type=42))
        assert any(e.field == "goal_type" and "expected str" in e.message for e in errors)

    def test_depth_not_str(self):
        errors = validate_scope(_scope(depth=3))
        assert any(e.field == "depth" and "expected str" in e.message for e in errors)

    def test_audience_not_str(self):
        errors = validate_scope(_scope(audience=True))
        assert any(e.field == "audience" and "expected str" in e.message for e in errors)

    def test_search_directions_not_list(self):
        errors = validate_scope(_scope(search_directions="AI"))
        assert any(e.field == "search_directions" and "expected list" in e.message for e in errors)

    def test_search_directions_non_str_items(self):
        errors = validate_scope(_scope(search_directions=[1, 2]))
        assert any(e.field == "search_directions" and "only strings" in e.message for e in errors)


class TestValidateScopeEnumErrors:
    def test_invalid_goal_type(self):
        errors = validate_scope(_scope(goal_type="invalid"))
        assert any(e.field == "goal_type" and "Invalid" in e.message for e in errors)

    def test_invalid_depth(self):
        errors = validate_scope(_scope(depth="shallow"))
        assert any(e.field == "depth" and "Invalid" in e.message for e in errors)

    def test_invalid_audience(self):
        errors = validate_scope(_scope(audience="manager"))
        assert any(e.field == "audience" and "Invalid" in e.message for e in errors)


class TestValidateScopeEdgeCases:
    def test_empty_search_directions(self):
        errors = validate_scope(_scope(search_directions=[]))
        assert any(e.field == "search_directions" and "non-empty" in e.message for e in errors)

    def test_report_language_empty_str(self):
        errors = validate_scope(_scope(report_language=""))
        assert any(e.field == "report_language" for e in errors)

    def test_report_language_not_str(self):
        errors = validate_scope(_scope(report_language=123))
        assert any(e.field == "report_language" for e in errors)

    def test_no_report_language_is_ok(self):
        errors = validate_scope(_scope())
        assert not any(e.field == "report_language" for e in errors)


class TestValidateScopeEnglishTitle:
    def test_cjk_topic_without_english_title_errors(self):
        errors = validate_scope(_scope(topic="智能体编程"))
        assert any(e.field == "english_title" and "required" in e.message for e in errors)

    def test_cjk_topic_with_english_title_passes(self):
        errors = validate_scope(_scope(topic="智能体编程", english_title="agentic coding"))
        assert not any(e.field == "english_title" for e in errors)

    def test_ascii_topic_without_english_title_ok(self):
        errors = validate_scope(_scope(topic="agentic coding"))
        assert not any(e.field == "english_title" for e in errors)

    def test_ascii_topic_with_english_title_ok(self):
        errors = validate_scope(_scope(topic="agentic coding", english_title="agentic coding"))
        assert not any(e.field == "english_title" for e in errors)

    def test_english_title_empty_str(self):
        errors = validate_scope(_scope(topic="智能体编程", english_title=""))
        assert any(e.field == "english_title" for e in errors)

    def test_english_title_not_str(self):
        errors = validate_scope(_scope(topic="智能体编程", english_title=123))
        assert any(e.field == "english_title" for e in errors)

    def test_mixed_ascii_and_cjk_topic_requires_english_title(self):
        errors = validate_scope(_scope(topic="2026 AI 趋势"))
        assert any(e.field == "english_title" and "required" in e.message for e in errors)

    def test_accented_latin_without_english_title_errors(self):
        errors = validate_scope(_scope(topic="développement"))
        assert any(e.field == "english_title" and "required" in e.message for e in errors)


def _analysis(**overrides) -> dict:
    base = {
        "topic": "test",
        "goal_type": "tech_selection",
        "sections": [
            {
                "id": "overview",
                "title": "Overview",
                "content": "Some content",
                "claims": [
                    {
                        "text": "AI is big",
                        "source_urls": ["https://a.com"],
                    }
                ],
            }
        ],
    }
    base.update(overrides)
    return base


class TestValidateAnalysisValid:
    def test_minimal_valid(self):
        errors = validate_analysis(_analysis())
        assert errors == []

    def test_section_without_claims(self):
        data = _analysis(sections=[{"id": "overview", "title": "Overview", "content": "text"}])
        errors = validate_analysis(data)
        assert errors == []

    def test_multiple_sections(self):
        data = _analysis(sections=[
            {"id": "overview", "title": "Overview", "content": "a"},
            {"id": "comparison", "title": "Comparison", "content": "b"},
        ])
        errors = validate_analysis(data)
        assert errors == []


class TestValidateAnalysisMissingFields:
    def test_missing_topic(self):
        data = _analysis()
        del data["topic"]
        errors = validate_analysis(data)
        assert any(e.field == "topic" and "missing" in e.message for e in errors)

    def test_missing_goal_type(self):
        data = _analysis()
        del data["goal_type"]
        errors = validate_analysis(data)
        assert any(e.field == "goal_type" for e in errors)

    def test_missing_sections(self):
        data = _analysis()
        del data["sections"]
        errors = validate_analysis(data)
        assert any(e.field == "sections" for e in errors)


class TestValidateAnalysisSectionsErrors:
    def test_empty_sections(self):
        errors = validate_analysis(_analysis(sections=[]))
        assert any(e.field == "sections" and "non-empty" in e.message for e in errors)

    def test_sections_not_list(self):
        errors = validate_analysis(_analysis(sections="bad"))
        assert any(e.field == "sections" and "expected list" in e.message for e in errors)

    def test_section_not_dict(self):
        errors = validate_analysis(_analysis(sections=["not a dict"]))
        assert any("sections[0]" in e.field and "expected dict" in e.message for e in errors)

    def test_section_missing_id(self):
        errors = validate_analysis(_analysis(sections=[{"title": "T", "content": "C"}]))
        assert any("sections[0].id" in e.field for e in errors)

    def test_section_missing_title(self):
        errors = validate_analysis(_analysis(sections=[{"id": "ov", "content": "C"}]))
        assert any("sections[0].title" in e.field for e in errors)

    def test_section_missing_content(self):
        errors = validate_analysis(_analysis(sections=[{"id": "ov", "title": "T"}]))
        assert any("sections[0].content" in e.field for e in errors)


class TestValidateAnalysisClaimErrors:
    def test_claim_missing_text(self):
        sec = {"id": "ov", "title": "T", "content": "C", "claims": [{"source_urls": ["https://a.com"]}]}
        errors = validate_analysis(_analysis(sections=[sec]))
        assert any("text" in e.field and "missing" in e.message for e in errors)

    def test_claim_missing_source_urls(self):
        sec = {"id": "ov", "title": "T", "content": "C", "claims": [{"text": "claim"}]}
        errors = validate_analysis(_analysis(sections=[sec]))
        assert any("source_urls" in e.field for e in errors)

    def test_claim_empty_source_urls(self):
        sec = {"id": "ov", "title": "T", "content": "C", "claims": [{"text": "claim", "source_urls": []}]}
        errors = validate_analysis(_analysis(sections=[sec]))
        assert any("source_urls" in e.field and "empty" in e.message for e in errors)

    def test_claim_invalid_metric_type(self):
        sec = {"id": "ov", "title": "T", "content": "C", "claims": [{"text": "c", "source_urls": ["https://a.com"], "metric_type": "invalid"}]}
        errors = validate_analysis(_analysis(sections=[sec]))
        assert any("metric_type" in e.field and "invalid" in e.message for e in errors)

    def test_claim_not_dict(self):
        sec = {"id": "ov", "title": "T", "content": "C", "claims": ["not a dict"]}
        errors = validate_analysis(_analysis(sections=[sec]))
        assert any("claims[0]" in e.field and "expected dict" in e.message for e in errors)

    def test_topic_not_str(self):
        errors = validate_analysis(_analysis(topic=123))
        assert any(e.field == "topic" and "expected str" in e.message for e in errors)


class TestValidateCollectedValid:
    def test_valid_entries(self):
        data = [
            {"url": "https://a.com", "title": "A", "snippet": "snip", "source_tier": 1},
            {"url": "https://b.com", "title": "B", "snippet": "snip"},
        ]
        errors = validate_collected(data)
        assert errors == []

    def test_empty_list(self):
        errors = validate_collected([])
        assert errors == []


class TestValidateCollectedErrors:
    def test_not_list(self):
        errors = validate_collected("not a list")  # type: ignore[arg-type]
        assert any(e.field == "collected" and "expected list" in e.message for e in errors)

    def test_entry_not_dict(self):
        errors = validate_collected(["not a dict"])
        assert any("entry[0]" in e.field and "expected dict" in e.message for e in errors)

    def test_missing_url(self):
        errors = validate_collected([{"title": "T", "snippet": "S"}])
        assert any("url" in e.field and "missing" in e.message for e in errors)

    def test_missing_title(self):
        errors = validate_collected([{"url": "https://a.com", "snippet": "S"}])
        assert any("title" in e.field and "missing" in e.message for e in errors)

    def test_missing_snippet(self):
        errors = validate_collected([{"url": "https://a.com", "title": "T"}])
        assert any("snippet" in e.field and "missing" in e.message for e in errors)

    def test_url_not_str(self):
        errors = validate_collected([{"url": 123, "title": "T", "snippet": "S"}])
        assert any("url" in e.field and "expected str" in e.message for e in errors)

    def test_source_tier_not_int(self):
        errors = validate_collected([{"url": "https://a.com", "title": "T", "snippet": "S", "source_tier": "1"}])
        assert any("source_tier" in e.field and "expected int" in e.message for e in errors)

    def test_source_tier_optional(self):
        errors = validate_collected([{"url": "https://a.com", "title": "T", "snippet": "S"}])
        assert not any("source_tier" in e.field for e in errors)


class TestValidateCollectedCoveredDirections:
    def test_valid_covered_directions(self):
        data = [
            {"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": ["AI", "ML"]},
            {"url": "https://b.com", "title": "B", "snippet": "S", "covered_directions": ["security"]},
        ]
        errors = validate_collected(data)
        assert errors == []

    def test_max_three_items(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": ["a", "b", "c"]}]
        errors = validate_collected(data)
        assert errors == []

    def test_more_than_three_items_fails(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": ["a", "b", "c", "d"]}]
        errors = validate_collected(data)
        assert any("covered_directions" in e.field and "at most 3" in e.message for e in errors)

    def test_non_list_fails(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": "AI"}]
        errors = validate_collected(data)
        assert any("covered_directions" in e.field and "expected list" in e.message for e in errors)

    def test_non_string_item_fails(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": ["AI", 42]}]
        errors = validate_collected(data)
        assert any("covered_directions[1]" in e.field and "non-empty string" in e.message for e in errors)

    def test_empty_string_fails(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S", "covered_directions": ["AI", ""]}]
        errors = validate_collected(data)
        assert any("covered_directions[1]" in e.field and "non-empty string" in e.message for e in errors)

    def test_without_covered_directions_passes(self):
        data = [{"url": "https://a.com", "title": "A", "snippet": "S"}]
        errors = validate_collected(data)
        assert not any("covered_directions" in e.field for e in errors)


class TestClaimSourceVerification:
    def test_source_verification_valid_value(self):
        claim = {"text": "T", "source_urls": ["https://a.com"], "source_verification": "source_confirmed"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [{"id": "s1", "title": "S", "content": "C", "claims": [claim]}]})
        assert not any("source_verification" in e.field for e in errors)

    def test_source_verification_invalid_value(self):
        claim = {"text": "T", "source_urls": ["https://a.com"], "source_verification": "invalid_value"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [{"id": "s1", "title": "S", "content": "C", "claims": [claim]}]})
        assert any("source_verification" in e.field for e in errors)

    def test_source_verification_optional(self):
        claim = {"text": "T", "source_urls": ["https://a.com"]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [{"id": "s1", "title": "S", "content": "C", "claims": [claim]}]})
        assert not any("source_verification" in e.field for e in errors)
