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

    def test_missing_depth_optional(self):
        data = _scope()
        del data["depth"]
        errors = validate_scope(data)
        assert not any(e.field == "depth" for e in errors)

    def test_missing_audience_optional(self):
        data = _scope()
        del data["audience"]
        errors = validate_scope(data)
        assert not any(e.field == "audience" for e in errors)

    def test_missing_both_depth_and_audience_optional(self):
        data = _scope()
        del data["depth"]
        del data["audience"]
        errors = validate_scope(data)
        assert not any(e.field in ("depth", "audience") for e in errors)


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


class TestValidateAnalysisDepthStrategy:
    def test_valid_depth_strategy(self):
        for ds in ("overview", "deep_dive", "comparison", "methodology"):
            sec = {"id": "s1", "title": "S", "content": "C", "depth_strategy": ds}
            errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
            assert not any("depth_strategy" in e.field for e in errors), f"depth_strategy={ds} should be valid"

    def test_invalid_depth_strategy(self):
        sec = {"id": "s1", "title": "S", "content": "C", "depth_strategy": "shallow"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("depth_strategy" in e.field and "invalid" in e.message for e in errors)

    def test_depth_strategy_not_str(self):
        sec = {"id": "s1", "title": "S", "content": "C", "depth_strategy": 42}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("depth_strategy" in e.field and "expected str" in e.message for e in errors)

    def test_depth_strategy_optional(self):
        sec = {"id": "s1", "title": "S", "content": "C"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert not any("depth_strategy" in e.field for e in errors)


class TestValidateAnalysisKeyInsights:
    def test_valid_key_insights(self):
        sec = {
            "id": "s1", "title": "S", "content": "C",
            "key_insights": [
                {"text": "Finding A", "source_urls": ["https://a.com"]},
                {"text": "Finding B"},
            ],
        }
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert not any("key_insights" in e.field for e in errors)

    def test_key_insights_not_list(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": "bad"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights" in e.field and "expected list" in e.message for e in errors)

    def test_key_insight_not_dict(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": ["not a dict"]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights[0]" in e.field and "expected dict" in e.message for e in errors)

    def test_key_insight_missing_text(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": [{"source_urls": ["https://a.com"]}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights[0].text" in e.field and "missing" in e.message for e in errors)

    def test_key_insight_text_not_str(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": [{"text": 42}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights[0].text" in e.field and "expected str" in e.message for e in errors)

    def test_key_insight_source_urls_not_list(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": [{"text": "T", "source_urls": "bad"}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights[0].source_urls" in e.field and "expected list" in e.message for e in errors)

    def test_key_insight_source_urls_non_str(self):
        sec = {"id": "s1", "title": "S", "content": "C", "key_insights": [{"text": "T", "source_urls": [42]}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("key_insights[0].source_urls" in e.field and "only strings" in e.message for e in errors)

    def test_key_insights_optional(self):
        sec = {"id": "s1", "title": "S", "content": "C"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert not any("key_insights" in e.field for e in errors)


class TestValidateAnalysisTensions:
    def test_valid_tensions(self):
        sec = {
            "id": "s1", "title": "S", "content": "C",
            "tensions": [
                {"description": "Source A says X, Source B says Y", "sources": ["https://a.com", "https://b.com"]},
            ],
        }
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert not any("tensions" in e.field for e in errors)

    def test_tensions_not_list(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": "bad"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions" in e.field and "expected list" in e.message for e in errors)

    def test_tension_not_dict(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": ["not a dict"]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions[0]" in e.field and "expected dict" in e.message for e in errors)

    def test_tension_missing_description(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": [{"sources": ["https://a.com"]}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions[0].description" in e.field and "missing" in e.message for e in errors)

    def test_tension_description_not_str(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": [{"description": 42}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions[0].description" in e.field and "expected str" in e.message for e in errors)

    def test_tension_sources_not_list(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": [{"description": "T", "sources": "bad"}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions[0].sources" in e.field and "expected list" in e.message for e in errors)

    def test_tension_sources_non_str(self):
        sec = {"id": "s1", "title": "S", "content": "C", "tensions": [{"description": "T", "sources": [42]}]}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert any("tensions[0].sources" in e.field and "only strings" in e.message for e in errors)

    def test_tensions_optional(self):
        sec = {"id": "s1", "title": "S", "content": "C"}
        errors = validate_analysis({"topic": "T", "goal_type": "other", "sections": [sec]})
        assert not any("tensions" in e.field for e in errors)


class TestValidateCollectedSourceFile:
    def test_collected_source_file_valid(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "source_file": "sources/abc123.md"}]
        errors = validate_collected(data)
        assert not any("source_file" in e.field for e in errors)

    def test_collected_source_file_empty_string(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "source_file": ""}]
        errors = validate_collected(data)
        assert any("source_file" in e.field for e in errors)

    def test_collected_source_file_not_str(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "source_file": 123}]
        errors = validate_collected(data)
        assert any("source_file" in e.field for e in errors)

    def test_collected_source_file_optional(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s"}]
        errors = validate_collected(data)
        assert not any("source_file" in e.field for e in errors)


class TestValidateCollectedVendorAffiliationNull:
    def test_collected_vendor_affiliation_null(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "vendor_affiliation": None}]
        errors = validate_collected(data)
        assert not any("vendor_affiliation" in e.field for e in errors)

    def test_collected_vendor_affiliation_empty_string(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "vendor_affiliation": ""}]
        errors = validate_collected(data)
        assert any("vendor_affiliation" in e.field for e in errors)

    def test_collected_vendor_affiliation_valid_string(self):
        data = [{"url": "https://example.com", "title": "Test", "snippet": "s", "vendor_affiliation": "Anthropic"}]
        errors = validate_collected(data)
        assert not any("vendor_affiliation" in e.field for e in errors)
