"""Tests for trust boundary integration in proceed.py (ADR 0053)."""

from __future__ import annotations

import json

import pytest

from pathlib import Path

from scripts.proceed import _preprocess_cjk_quotes, _validate_section_files, mark_section_incomplete, is_section_incomplete


class TestCjkQuotePreprocessing:
    def test_fullwidth_double_quotes_replaced(self):
        raw = '{"content": "DeepSeek称\u201c我们的模型达到72.6%\u201d"}'
        result = _preprocess_cjk_quotes(raw)
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert "'" in result

    def test_no_fullwidth_quotes_unchanged(self):
        raw = '{"content": "normal text"}'
        assert _preprocess_cjk_quotes(raw) == raw

    def test_mixed_quotes(self):
        raw = '他称\u201c达到\u201d后说\u201c超过\u201d'
        result = _preprocess_cjk_quotes(raw)
        assert result == "他称'达到'后说'超过'"

    def test_empty_string(self):
        assert _preprocess_cjk_quotes("") == ""


class TestValidateSectionFiles:
    def test_valid_section_files_pass(self, tmp_path):
        collected = tmp_path / "collected.json"
        collected.write_text(json.dumps([
            {"url": "https://example.com/a", "title": "A", "snippet": "a"}
        ]), encoding="utf-8")

        section = tmp_path / "analysis_section_overview.json"
        section.write_text(json.dumps({
            "id": "overview",
            "title": "Overview",
            "content": "Text {{ref:https://example.com/a}}.",
            "depth_strategy": "overview",
            "key_insights": [{"summary": "K", "sources": ["https://example.com/a"]}],
            "tensions": [],
            "claims": [{"summary": "C", "sources": ["https://example.com/a"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}],
        }), encoding="utf-8")

        errors = _validate_section_files(tmp_path)
        assert errors == []

    def test_invalid_section_file_blocks(self, tmp_path):
        collected = tmp_path / "collected.json"
        collected.write_text(json.dumps([
            {"url": "https://example.com/a", "title": "A", "snippet": "a"}
        ]), encoding="utf-8")

        section = tmp_path / "analysis_section_bad.json"
        section.write_text(json.dumps({
            "id": "bad",
            "title": "Bad",
            "content": "Text.",
            "claims": ["string not object"],
        }), encoding="utf-8")

        errors = _validate_section_files(tmp_path)
        assert len(errors) > 0
        assert any("trust_boundary" in e for e in errors)


class TestMarkSectionIncomplete:
    def test_marks_section_as_incomplete(self, tmp_path):
        section = tmp_path / "analysis_section_overview.json"
        section.write_text(json.dumps({
            "id": "overview",
            "title": "Overview",
            "content": "Some content.",
        }), encoding="utf-8")
        mark_section_incomplete(section)
        data = json.loads(section.read_text(encoding="utf-8"))
        assert data["status"] == "incomplete"

    def test_preserves_existing_content(self, tmp_path):
        section = tmp_path / "analysis_section_overview.json"
        original = {"id": "overview", "title": "Overview", "content": "Content.", "claims": [{"summary": "X", "sources": ["https://a.com"]}]}
        section.write_text(json.dumps(original), encoding="utf-8")
        mark_section_incomplete(section)
        data = json.loads(section.read_text(encoding="utf-8"))
        assert data["id"] == "overview"
        assert data["content"] == "Content."
        assert data["status"] == "incomplete"

    def test_invalid_json_noop(self, tmp_path):
        section = tmp_path / "analysis_section_bad.json"
        section.write_text("not json", encoding="utf-8")
        mark_section_incomplete(section)
        assert section.read_text(encoding="utf-8") == "not json"


class TestIsSectionIncomplete:
    def test_incomplete_section_detected(self, tmp_path):
        section = tmp_path / "analysis_section_overview.json"
        section.write_text(json.dumps({"id": "overview", "status": "incomplete"}), encoding="utf-8")
        assert is_section_incomplete(section) is True

    def test_normal_section_not_incomplete(self, tmp_path):
        section = tmp_path / "analysis_section_overview.json"
        section.write_text(json.dumps({"id": "overview", "title": "Overview"}), encoding="utf-8")
        assert is_section_incomplete(section) is False

    def test_missing_file_not_incomplete(self, tmp_path):
        section = tmp_path / "nonexistent.json"
        assert is_section_incomplete(section) is False

    def test_invalid_json_not_incomplete(self, tmp_path):
        section = tmp_path / "analysis_section_bad.json"
        section.write_text("not json", encoding="utf-8")
        assert is_section_incomplete(section) is False


class TestIncompleteSectionSkipsTrustBoundary:
    def test_incomplete_section_not_validated(self, tmp_path):
        collected = tmp_path / "collected.json"
        collected.write_text(json.dumps([
            {"url": "https://example.com/a", "title": "A", "snippet": "a"}
        ]), encoding="utf-8")

        section = tmp_path / "analysis_section_bad.json"
        section.write_text(json.dumps({
            "id": "bad",
            "title": "Bad",
            "content": "Text.",
            "status": "incomplete",
            "claims": ["string not object"],
        }), encoding="utf-8")

        errors = _validate_section_files(tmp_path)
        assert errors == []

    def test_no_section_files_passes(self, tmp_path):
        collected = tmp_path / "collected.json"
        collected.write_text(json.dumps([]), encoding="utf-8")
        errors = _validate_section_files(tmp_path)
        assert errors == []

    def test_url_mismatch_blocks(self, tmp_path):
        collected = tmp_path / "collected.json"
        collected.write_text(json.dumps([
            {"url": "https://example.com/a", "title": "A", "snippet": "a"}
        ]), encoding="utf-8")

        section = tmp_path / "analysis_section_overview.json"
        section.write_text(json.dumps({
            "id": "overview",
            "title": "Overview",
            "content": "Text.",
            "depth_strategy": "overview",
            "claims": [{"summary": "C", "sources": ["https://evil.com/fake"], "evidence_type": "official_data", "confidence": "high", "precision": "exact"}],
        }), encoding="utf-8")

        errors = _validate_section_files(tmp_path)
        assert len(errors) > 0
