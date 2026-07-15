"""Tests for trust_boundary module (ADR 0053)."""

from __future__ import annotations

import json

import pytest

from scripts.trust_boundary import ValidationResult, validate_section_output


def _valid_section_json() -> str:
    return json.dumps({
        "id": "overview",
        "title": "Overview",
        "content": "Some content with {{ref:https://example.com/a}}.",
        "depth_strategy": "overview",
        "key_insights": [
            {"summary": "Key finding", "sources": ["https://example.com/a"]}
        ],
        "tensions": [],
        "claims": [
            {
                "summary": "Test claim",
                "sources": ["https://example.com/a"],
                "evidence_type": "official_data",
                "confidence": "high",
                "precision": "exact",
                "source_metadata": {"test_conditions": "N/A", "test_date": "2026-Q1", "source_type": "official_report"},
            }
        ],
    })


def _collected_urls() -> set[str]:
    return {"https://example.com/a", "https://example.com/b"}


class TestValidOutput:
    def test_valid_section_passes(self):
        result = validate_section_output(_valid_section_json(), _collected_urls())
        assert result.passed is True
        assert result.errors == []

    def test_valid_section_no_key_insights_or_tensions(self):
        data = {
            "id": "overview",
            "title": "Overview",
            "content": "Content.",
            "depth_strategy": "overview",
            "claims": [
                {
                    "summary": "Claim",
                    "sources": ["https://example.com/a"],
                    "evidence_type": "official_data",
                    "confidence": "high",
                    "precision": "exact",
                }
            ],
        }
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is True


class TestStructuralValidation:
    def test_invalid_json(self):
        result = validate_section_output("not json {{{", _collected_urls())
        assert result.passed is False
        assert result.errors[0].error == "invalid_json"

    def test_bom_stripped_before_parse(self):
        raw = '\ufeff' + _valid_section_json()
        result = validate_section_output(raw, _collected_urls())
        assert result.passed is True

    def test_missing_required_field_id(self):
        data = json.loads(_valid_section_json())
        del data["id"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.path == "id" for e in result.errors)

    def test_missing_required_field_title(self):
        data = json.loads(_valid_section_json())
        del data["title"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.path == "title" for e in result.errors)

    def test_missing_required_field_content(self):
        data = json.loads(_valid_section_json())
        del data["content"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.path == "content" for e in result.errors)

    def test_claims_as_string_array(self):
        data = json.loads(_valid_section_json())
        data["claims"] = ["claim as string", "another string"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("claims" in e.path for e in result.errors)

    def test_key_insights_as_string_array(self):
        data = json.loads(_valid_section_json())
        data["key_insights"] = ["insight as string"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("key_insights" in e.path for e in result.errors)

    def test_tensions_as_string_array(self):
        data = json.loads(_valid_section_json())
        data["tensions"] = ["tension as string"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("tensions" in e.path for e in result.errors)

    def test_empty_sources_in_claim(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["sources"] = []
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("sources" in e.path for e in result.errors)

    def test_invalid_evidence_type(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["evidence_type"] = "quantitative"
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("evidence_type" in e.path for e in result.errors)

    def test_invalid_confidence(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["confidence"] = "very_high"
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("confidence" in e.path for e in result.errors)

    def test_invalid_precision(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["precision"] = "approximate"
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any("precision" in e.path for e in result.errors)

    def test_invalid_depth_strategy(self):
        data = json.loads(_valid_section_json())
        data["depth_strategy"] = "shallow"
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.path == "depth_strategy" for e in result.errors)


class TestSemanticValidation:
    def test_url_not_in_collected(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["sources"] = ["https://evil.com/fake"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.error == "url_not_in_collected" for e in result.errors)

    def test_ref_marker_url_not_in_collected(self):
        data = json.loads(_valid_section_json())
        data["content"] = "See {{ref:https://evil.com/fake}}."
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.error == "url_not_in_collected" for e in result.errors)

    def test_key_insight_url_not_in_collected(self):
        data = json.loads(_valid_section_json())
        data["key_insights"][0]["sources"] = ["https://evil.com/fake"]
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        assert any(e.error == "url_not_in_collected" for e in result.errors)

    def test_empty_collected_urls_skips_semantic(self):
        result = validate_section_output(_valid_section_json(), set())
        assert result.passed is True


class TestValidationReportFormat:
    def test_report_json_structure(self):
        data = json.loads(_valid_section_json())
        data["claims"][0]["evidence_type"] = "quantitative"
        result = validate_section_output(json.dumps(data), _collected_urls())
        assert result.passed is False
        report = json.loads(result.report_json)
        assert "validation_errors" in report
        assert "retry_count" in report
        assert "max_retries" in report
        assert len(report["validation_errors"]) > 0
        err = report["validation_errors"][0]
        assert "path" in err
        assert "error" in err
        assert "expected" in err
        assert "actual" in err

    def test_passed_result_has_empty_report(self):
        result = validate_section_output(_valid_section_json(), _collected_urls())
        assert result.passed is True
        assert result.report_json == ""
