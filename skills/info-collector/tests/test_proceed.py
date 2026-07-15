from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.exceptions import ArtifactError
from scripts.lib.utils import compute_url_hash
from scripts.lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_PIPELINE_STATE,
    ARTIFACT_REVIEW_REPORT,
    ARTIFACT_SCOPE,
)
from scripts.proceed import (
    _check_scope_schema,
    _check_review_report_exists,
    _fill_scope_defaults,
    _gate_analysis,
    check_report,
    _repair_json_text,
    _read_json_with_repair,
    _sanitize_sections,
    write_phase_state,
    detect_current_phase,
    get_gateway_results,
    proceeds,
)


def _write_scope_and_collected(workdir):
    scope = {"topic": "t", "goal_type": "exploratory", "depth": "quick", "audience": "engineer", "scope_description": "d", "search_directions": ["d1"]}
    _write_json(workdir / "scope.json", scope)
    url = "https://example.com"
    h = compute_url_hash(url)
    sources_dir = workdir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    (sources_dir / f"{h}.md").write_text("test content", encoding="utf-8")
    _write_json(workdir / "collected.json", [{"url": url, "title": "x", "snippet": "d1", "source_tier": 4, "fetched_content": "x" * 500, "source_file": f"sources/{h}.md"}])


class TestDetectCurrentPhase:
    def test_pre_scope(self, tmp_path):
        assert detect_current_phase(tmp_path / "nonexistent") == "pre_scope"

    def test_post_scope(self, tmp_path):
        _make_scope(tmp_path)
        assert detect_current_phase(tmp_path) == "post_scope"

    def test_post_search(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        assert detect_current_phase(tmp_path) == "post_search"

    def test_post_analysis(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        assert detect_current_phase(tmp_path) == "post_analysis"

    def test_post_review(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(tmp_path / "review_report.md", {})
        assert detect_current_phase(tmp_path) == "post_review"


class TestProceeds:
    def test_valid_scope_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_missing_fields(self, tmp_path):
        _write_json(tmp_path / "scope.json", {"topic": "T"})
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        error_text = "; ".join(errors)
        assert "goal_type" in error_text

    def test_scope_gate_with_valid_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language="zh")
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_with_empty_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language="")
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "report_language" in errors[0]

    def test_scope_gate_without_report_language(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors

    def test_scope_gate_with_non_string_report_language(self, tmp_path):
        _make_scope(tmp_path, report_language=123)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "report_language" in errors[0]

    def test_scope_gate_invalid_phase(self, tmp_path):
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok
        assert "Phase mismatch" in errors[0]

    def test_search_gate_passes(self, tmp_path):
        _make_scope(tmp_path, goal_type="exploratory", depth="quick")
        entries = []
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        for i, tier in enumerate([4, 3, 2]):
            url = f"https://s{i}.example.com"
            h = compute_url_hash(url)
            entry = {"url": url, "title": f"Source {i}", "snippet": f"About topic {i}", "fetched_content": "x" * 300, "source_tier": tier, "source_file": f"sources/{h}.md", "direction": ["ai", "ml"][i % 2]}
            (sources_dir / f"{h}.md").write_text("x" * 2100, encoding="utf-8")
            entries.append(entry)
        _write_json(tmp_path / "collected.json", entries)
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_search_gate_empty_collected(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_analysis_to_review_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "O",
                    "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                    "claims": [{"summary": "C1", "sources": ["https://a.com"]}],
                },
                {
                    "id": "comparison",
                    "title": "Cmp",
                    "content": "Docker runs 10000 containers per host with Kubernetes orchestration {{ref:https://a.com}}.",
                    "claims": [{"summary": "C2", "sources": ["https://a.com"]}],
                },
                {
                    "id": "recommendation",
                    "title": "Rec",
                    "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility {{ref:https://a.com}}.",
                    "claims": [{"summary": "C3", "sources": ["https://a.com"]}],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "M",
                    "claims": [],
                },
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok, errors

    def test_analysis_to_review_gate_blocks_untraceable_urls(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "O",
                    "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                    "claims": [{"summary": "C1", "sources": ["https://fabricated.com"]}],
                },
                {
                    "id": "comparison",
                    "title": "Cmp",
                    "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                    "claims": [{"summary": "C2", "sources": ["https://a.com"]}],
                },
                {
                    "id": "recommendation",
                    "title": "Rec",
                    "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                    "claims": [{"summary": "C3", "sources": ["https://a.com"]}],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "M",
                    "claims": [],
                },
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok
        assert any("url_traceability" in e or "trust_boundary" in e for e in errors)

    def test_analysis_to_review_gate_blocks_empty_sections(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {"topic": "T", "goal_type": "tech_selection", "sections": []},
        )
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok

    def test_invalid_transition(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "final")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_review_gate_invokes_gateway(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "O",
                    "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                    "claims": [{"summary": "C1", "sources": ["https://a.com"]}],
                },
                {
                    "id": "comparison",
                    "title": "Cmp",
                    "content": "Docker runs 10000 containers per host with Kubernetes orchestration {{ref:https://a.com}}.",
                    "claims": [{"summary": "C2", "sources": ["https://a.com"]}],
                },
                {
                    "id": "recommendation",
                    "title": "Rec",
                    "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility {{ref:https://a.com}}.",
                    "claims": [{"summary": "C3", "sources": ["https://a.com"], "verified": True}],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "M",
                    "claims": [],
                },
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)
        _write_json(tmp_path / "review_report.md", {})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok, errors


class TestScopeDefaultsAutoFill:
    def test_missing_depth_filled_with_standard(self, tmp_path):
        scope = {"topic": "t", "goal_type": "exploratory", "scope_description": "d", "search_directions": ["AI"]}
        _write_json(tmp_path / "scope.json", scope)
        _fill_scope_defaults(tmp_path)
        result = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
        assert result["depth"] == "standard"
        assert result["audience"] == "general"

    def test_missing_audience_filled_with_general(self, tmp_path):
        scope = {"topic": "t", "goal_type": "exploratory", "depth": "quick", "scope_description": "d", "search_directions": ["AI"]}
        _write_json(tmp_path / "scope.json", scope)
        _fill_scope_defaults(tmp_path)
        result = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
        assert result["depth"] == "quick"
        assert result["audience"] == "general"

    def test_both_missing_filled(self, tmp_path):
        scope = {"topic": "t", "goal_type": "exploratory", "scope_description": "d", "search_directions": ["AI"]}
        _write_json(tmp_path / "scope.json", scope)
        _fill_scope_defaults(tmp_path)
        result = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
        assert result["depth"] == "standard"
        assert result["audience"] == "general"

    def test_existing_values_not_overwritten(self, tmp_path):
        scope = {"topic": "t", "goal_type": "exploratory", "depth": "deep", "audience": "CTO", "scope_description": "d", "search_directions": ["AI"]}
        _write_json(tmp_path / "scope.json", scope)
        _fill_scope_defaults(tmp_path)
        result = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
        assert result["depth"] == "deep"
        assert result["audience"] == "CTO"

    def test_scope_gate_auto_fills_and_passes(self, tmp_path):
        scope = {"topic": "t", "goal_type": "exploratory", "scope_description": "d", "search_directions": ["AI"]}
        _write_json(tmp_path / "scope.json", scope)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors
        result = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
        assert result["depth"] == "standard"
        assert result["audience"] == "general"


class TestGetGatewayResults:
    def test_returns_list_of_check_results(self, tmp_path):
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com", "title": "T", "snippet": "S"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "C",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"summary": "C2", "sources": ["https://example.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"summary": "C3", "sources": ["https://example.com"]}],
                    },
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        results = get_gateway_results(tmp_path)
        assert isinstance(results, list)
        assert len(results) >= 1
        from scripts.lib.check_types import CheckResult

        assert all(isinstance(r, CheckResult) for r in results)

    def test_passes_correct_goal_type(self, tmp_path):
        _make_scope(tmp_path, goal_type="exploratory")
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com", "title": "T", "snippet": "S"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "exploratory",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "C",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                    {
                        "id": "details",
                        "title": "Details",
                        "content": "D",
                        "claims": [{"summary": "C2", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        results = get_gateway_results(tmp_path)
        section_coverage = next((r for r in results if r.name == "section_coverage"), None)
        assert section_coverage is not None
        assert section_coverage.passed is True


class TestSanitizeSections:
    """_sanitize_sections cleans subagent output before schema validation."""

    def test_section_id_mapped_to_id(self):
        raw = {"topic": "T", "goal_type": "exploratory", "sections": [{"section_id": "s1", "title": "S1", "content": "C"}]}
        result = _sanitize_sections(raw)
        assert "section_id" not in result["sections"][0]
        assert result["sections"][0]["id"] == "s1"

    def test_source_urls_mapped_to_sources_in_claims(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C", "claims": [{"summary": "claim1", "source_urls": ["https://a.com"]}]}],
        }
        result = _sanitize_sections(raw)
        claim = result["sections"][0]["claims"][0]
        assert "source_urls" not in claim
        assert claim["sources"] == ["https://a.com"]

    def test_non_schema_fields_removed_from_section(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C", "word_count": 500, "language": "en"}],
        }
        result = _sanitize_sections(raw)
        assert "word_count" not in result["sections"][0]
        assert "language" not in result["sections"][0]

    def test_non_schema_fields_removed_from_claim(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C", "claims": [{"summary": "c1", "sources": ["https://a.com"], "relevance_score": 0.9}]}],
        }
        result = _sanitize_sections(raw)
        assert "relevance_score" not in result["sections"][0]["claims"][0]

    def test_missing_claims_defaults_to_empty_list(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C"}],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"] == []

    def test_valid_input_passes_through_unchanged(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {
                    "id": "s1", "title": "S1", "content": "C",
                    "claims": [{"summary": "c1", "sources": ["https://a.com"], "verified": True}],
                },
            ],
        }
        result = _sanitize_sections(raw)
        assert result == raw

    def test_input_not_mutated(self):
        original = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"section_id": "s1", "title": "S1", "content": "C", "word_count": 500}],
        }
        _sanitize_sections(original)
        assert "section_id" in original["sections"][0]
        assert "word_count" in original["sections"][0]

    def test_top_level_keys_preserved(self):
        raw = {"topic": "T", "goal_type": "exploratory", "custom_key": "keep", "sections": []}
        result = _sanitize_sections(raw)
        assert result["topic"] == "T"
        assert result["goal_type"] == "exploratory"
        assert result["custom_key"] == "keep"

    def test_evidence_type_safe_alias_mapped(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [
                     {"summary": "c1", "sources": ["https://a.com"], "evidence_type": "blog"},
                     {"summary": "c2", "sources": ["https://b.com"], "evidence_type": "opinion"},
                 ]},
            ],
        }
        result = _sanitize_sections(raw)
        claims = result["sections"][0]["claims"]
        assert claims[0]["evidence_type"] == "third_party_estimate"
        assert claims[1]["evidence_type"] == "expert_opinion"

    def test_invalid_evidence_type_downgraded_to_qualitative_trend(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [{"summary": "c1", "sources": ["https://a.com"], "evidence_type": "mystery"}]},
            ],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"][0]["evidence_type"] == "qualitative_trend"

    def test_key_insights_string_array_raises(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C",
                          "key_insights": ["just a string"]}],
        }
        with pytest.raises(ValueError) as exc:
            _sanitize_sections(raw)
        assert "key_insights[0]" in str(exc.value)
        assert "summary" in str(exc.value)

    def test_tensions_string_array_raises(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C",
                          "tensions": ["disagreement as string"]}],
        }
        with pytest.raises(ValueError) as exc:
            _sanitize_sections(raw)
        assert "tensions[0]" in str(exc.value)

    def test_source_type_alias_mapped(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [{"summary": "c1", "sources": ["https://a.com"],
                             "source_metadata": {"source_type": "independent_benchmark"}}]},
            ],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"][0]["source_metadata"]["source_type"] == "independent_test"

    def test_source_type_invalid_downgraded_to_survey(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [{"summary": "c1", "sources": ["https://a.com"],
                             "source_metadata": {"source_type": "garbage"}}]},
            ],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"][0]["source_metadata"]["source_type"] == "survey"

    def test_source_type_valid_unchanged(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [{"summary": "c1", "sources": ["https://a.com"],
                             "source_metadata": {"source_type": "vendor_benchmark"}}]},
            ],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"][0]["source_metadata"]["source_type"] == "vendor_benchmark"

    def test_evidence_type_independent_test_alias(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [
                {"id": "s1", "title": "S1", "content": "C",
                 "claims": [{"summary": "c1", "sources": ["https://a.com"],
                             "evidence_type": "independent_test"}]},
            ],
        }
        result = _sanitize_sections(raw)
        assert result["sections"][0]["claims"][0]["evidence_type"] == "independent_benchmark"


class TestRepairJsonText:
    """_repair_json_text escapes unescaped quotes inside JSON string values."""

    def test_valid_json_unchanged(self):
        raw = '{"topic": "T", "goal_type": "exploratory"}'
        assert _repair_json_text(raw) == raw

    def test_unescaped_quotes_in_content_escaped(self):
        raw = '{"content": "He said "hello" to me"}'
        repaired = _repair_json_text(raw)
        data = json.loads(repaired)
        assert data["content"] == 'He said "hello" to me'

    def test_already_escaped_quotes_preserved(self):
        raw = '{"content": "He said \\"hello\\" to me"}'
        repaired = _repair_json_text(raw)
        assert repaired == raw
        data = json.loads(repaired)
        assert data["content"] == 'He said "hello" to me'

    def test_markdown_with_bold_quotes(self):
        raw = '{"content": "The term "machine learning" was coined in 1959"}'
        repaired = _repair_json_text(raw)
        data = json.loads(repaired)
        assert '"machine learning"' in data["content"]

    def test_multiple_unescaped_quotes(self):
        raw = '{"content": "A "big" deal and a "small" one"}'
        repaired = _repair_json_text(raw)
        data = json.loads(repaired)
        assert data["content"] == 'A "big" deal and a "small" one'

    def test_structural_chars_not_mangled(self):
        raw = '{"a": "x", "b": ["y", "z"]}'
        repaired = _repair_json_text(raw)
        data = json.loads(repaired)
        assert data == {"a": "x", "b": ["y", "z"]}

    def test_empty_string_value(self):
        raw = '{"content": ""}'
        repaired = _repair_json_text(raw)
        data = json.loads(repaired)
        assert data["content"] == ""

    def test_read_json_with_repair_valid_file(self, tmp_path):
        path = tmp_path / "test.json"
        _write_json(path, {"topic": "T"})
        data, err = _read_json_with_repair(path)
        assert err is None
        assert data["topic"] == "T"

    def test_read_json_with_repair_fixes_unescaped_quotes(self, tmp_path):
        path = tmp_path / "analysis.json"
        raw = '{"topic": "T", "goal_type": "exploratory", "sections": [{"id": "s1", "title": "Overview of "AI" trends", "content": "C", "claims": []}]}'
        path.write_text(raw, encoding="utf-8")
        data, err = _read_json_with_repair(path)
        assert err is None
        assert data["sections"][0]["title"] == 'Overview of "AI" trends'

    def test_read_json_with_repair_non_json_error(self, tmp_path):
        path = tmp_path / "missing.json"
        data, err = _read_json_with_repair(path)
        assert data is None
        assert err is not None

    def test_read_json_with_repair_unfixable_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{{{", encoding="utf-8")
        data, err = _read_json_with_repair(path)
        assert data is None
        assert "repair" in err.lower()


class TestPipelineStateFile:
    def test_state_file_overrides_artifact_detection(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        assert detect_current_phase(tmp_path) == "post_review"

    def test_state_file_fallback_to_artifacts(self, tmp_path):
        _make_scope(tmp_path)
        assert not (tmp_path / "pipeline_state.json").exists()
        assert detect_current_phase(tmp_path) == "post_scope"

    def test_state_file_corrupt_falls_back(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        (tmp_path / "pipeline_state.json").write_text("{invalid json", encoding="utf-8")
        assert detect_current_phase(tmp_path) == "post_search"

    def test_write_phase_state(self, tmp_path):
        write_phase_state(tmp_path, "post_review")
        state = json.loads((tmp_path / "pipeline_state.json").read_text(encoding="utf-8"))
        assert state == {"current_phase": "post_review"}

    def test_proceeds_writes_state(self, tmp_path):
        _make_scope(tmp_path)
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert ok, errors
        state = json.loads((tmp_path / "pipeline_state.json").read_text(encoding="utf-8"))
        assert state == {"current_phase": "post_search"}


class TestReviewSelfLoop:
    def test_review_to_review_allowed(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"], "verified": True}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"summary": "C2", "sources": ["https://example.com"], "verified": True}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"summary": "C3", "sources": ["https://example.com"], "verified": True}],
                    },
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        _write_json(tmp_path / "review_report.md", {})
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok, errors

    def test_review_to_review_runs_gateway(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"], "verified": False}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"summary": "C2", "sources": ["https://example.com"], "verified": False}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"summary": "C3", "sources": ["https://example.com"], "verified": False}],
                    },
                    {
                        "id": "methodology",
                        "title": "Methodology",
                        "content": "M",
                        "claims": [],
                    },
                ],
            },
        )
        _write_json(tmp_path / "review_report.md", {})
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok


class TestGateFinalOnlyBlocksBlocker:
    """check_report only blocks on BLOCKER-level failures, not WARN."""

    def test_warn_does_not_block_final(self, tmp_path, monkeypatch):
        report = "---\ntopic: T\ngoal_type: exploratory\ndate: 2026-06-26\nreview_status: draft\n---\n## Overview\nContent with cite [&#91;1&#93;](#refs).\n\n## References\n- [1] [Title](https://a.com)\n"
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)
        errors = check_report(tmp_path)
        assert errors == [], f"WARN-only failures should not block: {errors}"

    def test_blocker_blocks_final(self, tmp_path, monkeypatch):
        """F1/F2/9 are BLOCKER — missing front matter blocks the final gate."""
        report = "No front matter, no references."
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)
        errors = check_report(tmp_path)
        assert errors, "BLOCKER report checks should block: front matter is missing"
        assert any("report_front_matter" in e for e in errors)


class TestCleanupTransitionRejected:
    def test_cleanup_transition_rejected(self, tmp_path):
        """Phase 4 (cleanup) has been removed; final→cleanup should be rejected."""
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_final"})
        ok, errors = proceeds(tmp_path, "final", "cleanup")
        assert not ok
        assert "Invalid transition" in errors[0]


class TestIntegrationMediumComplexity:
    def test_state_file_survives_review_self_loop(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        config = {
            "sources": {
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
            },
            "routes": {"exploratory": {"entry_tier": 4, "path": [4, 3, 2]}},
        }
        scope = {"topic": "t", "goal_type": "exploratory", "depth": "quick", "audience": "engineer", "scope_description": "d", "search_directions": ["d1"]}
        _write_json(workdir / "scope.json", scope)
        proceeds(workdir, "scope", "search", config)
        assert detect_current_phase(workdir) == "post_search"
        collected = []
        for i, tier in enumerate([4, 3, 2]):
            url = f"https://example.com/{i}"
            h = compute_url_hash(url)
            sources_dir = workdir / "sources"
            sources_dir.mkdir(parents=True, exist_ok=True)
            (sources_dir / f"{h}.md").write_text("x" * 2100, encoding="utf-8")
            collected.append({"url": url, "title": f"d1 info {i}", "snippet": "d1", "source_tier": tier, "fetched_content": "x" * 500, "source_file": f"sources/{h}.md", "direction": "d1"})
        _write_json(workdir / "collected.json", collected)

        proceeds(workdir, "search", "analysis")
        assert detect_current_phase(workdir) == "post_analysis"
        analysis = {"topic": "t", "goal_type": "exploratory", "sections": [
            {"id": "overview", "title": "Overview", "content": "test", "claims": []},
            {"id": "findings", "title": "Findings", "content": "test findings", "claims": []}
        ]}
        _write_json(workdir / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(workdir / f"analysis_section_{sec['id']}.json", sec)
        proceeds(workdir, "analysis", "review")
        assert detect_current_phase(workdir) == "post_review"
        (workdir / "review_report.md").write_text("## Overall Verdict\n**pass_with_issues**\n", encoding="utf-8")
        write_phase_state(workdir, "post_review")
        passed, errors = proceeds(workdir, "review", "review")
        assert passed
        passed, errors = proceeds(workdir, "review", "final")
        assert passed


class TestProceedArtifactErrorHandling:
    """ArtifactError from read_json is caught gracefully by narrowed handlers."""

    def test_check_scope_schema_handles_artifact_error(self, tmp_path, monkeypatch):
        """_check_scope_schema catches ArtifactError, returns error message."""
        def _raise_read_json(*args, **kwargs):
            raise ArtifactError(str(tmp_path / "scope.json"), "file not found")

        monkeypatch.setattr("scripts.proceed.read_json", _raise_read_json)
        errors = _check_scope_schema(tmp_path)
        assert len(errors) == 1
        assert "Cannot read scope.json" in errors[0]


class TestGateAnalysisChecksAllBlockers:
    """L2: _gate_analysis checks all analysis-phase BLOCKERs, not just url_traceability."""

    def _make_passing_analysis(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "O",
                    "content": "Kubernetes 1.28 handles 5000 nodes efficiently.",
                    "claims": [{"summary": "C1", "sources": ["https://a.com"]}],
                },
                {
                    "id": "comparison",
                    "title": "Cmp",
                    "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                    "claims": [{"summary": "C2", "sources": ["https://a.com"]}],
                },
                {
                    "id": "recommendation",
                    "title": "Rec",
                    "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                    "claims": [{"summary": "C3", "sources": ["https://a.com"]}],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "M",
                    "claims": [],
                },
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)

    def test_section_coverage_blocker_caught(self, tmp_path):
        self._make_passing_analysis(tmp_path)
        analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
        analysis["sections"] = [analysis["sections"][0]]
        _write_json(tmp_path / "analysis.json", analysis)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok
        assert any("section_coverage" in e for e in errors)

    def test_content_concreteness_no_longer_blocks(self, tmp_path):
        """content_concreteness is WARN after gate philosophy shift — does not block."""
        self._make_passing_analysis(tmp_path)
        analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
        for sec in analysis["sections"]:
            if sec.get("claims"):
                sec["content"] = "Some vague text without numbers or names. {{ref:https://a.com}}"
                sec["claims"] = [{"summary": "vague claim", "sources": ["https://a.com"]}]
        _write_json(tmp_path / "analysis.json", analysis)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok, "content_concreteness WARN should not block"
        assert not any("content_concreteness" in e for e in errors)


class TestGateReviewOnlyChecksReviewItems:
    """L3: _gate_review blocks on review_report_exists BLOCKER, advisory on other checks."""

    def test_review_gate_ignores_section_coverage_issues(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"], "verified": True}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok
        assert not any("section_coverage" in e for e in errors)

    def test_review_gate_passes_with_unverified_claims(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"], "verified": False}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok


class TestGateReviewNoLongerBlocks:
    def test_review_gate_passes_with_unverified_claims(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"], "verified": False}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok

    def test_review_gate_always_passes(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok
        assert errors == []

    def test_review_to_final_blocks_without_review_report(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert not ok
        assert any("review_report_exists" in e for e in errors)

    def test_review_to_final_passes_with_review_report(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok


class TestSourceVerificationWriteBack:
    def test_analysis_gate_writes_source_verification(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [
            {"url": "https://a.com", "title": "A", "snippet": "s", "fetched_content": "98% accuracy", "source_tier": 1}
        ])
        analysis = {
            "topic": "T",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "O",
                    "content": "Achieves 98% {{ref:https://a.com}}.",
                    "claims": [{"summary": "98% accuracy", "sources": ["https://a.com"], "evidence_type": "official_data", "confidence": "high", "precision": "exact", "source_metadata": {"test_conditions": "Lab environment", "source_type": "independent_test"}}],
                },
                {
                    "id": "comparison",
                    "title": "Cmp",
                    "content": "Cmp content.",
                    "claims": [],
                },
                {
                    "id": "recommendation",
                    "title": "Rec",
                    "content": "Rec content.",
                    "claims": [],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "M",
                    "claims": [],
                },
            ],
        }
        _write_json(tmp_path / "analysis.json", analysis)
        for sec in analysis["sections"]:
            _write_json(tmp_path / f"analysis_section_{sec['id']}.json", sec)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok, errors
        analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
        claim = analysis["sections"][0]["claims"][0]
        assert claim.get("source_verification") == "source_confirmed"
        assert claim.get("verified") is True


class TestReviewReportExistsCheck:
    """review_report_exists gate check — BLOCKER level (review is mandatory, ADR 0028)."""

    def test_blocks_when_review_report_missing(self, tmp_path):
        result = _check_review_report_exists(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "does not exist" in result.message

    def test_blocks_when_review_report_empty(self, tmp_path):
        (tmp_path / "review_report.md").write_text("", encoding="utf-8")
        result = _check_review_report_exists(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "empty" in result.message

    def test_blocks_when_review_report_whitespace_only(self, tmp_path):
        (tmp_path / "review_report.md").write_text("   \n\n  ", encoding="utf-8")
        result = _check_review_report_exists(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "empty" in result.message

    def test_passes_when_review_report_has_content(self, tmp_path):
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        result = _check_review_report_exists(tmp_path)
        assert result.passed
        assert result.level == "BLOCKER"

    def test_passes_when_review_report_has_degraded_verdict(self, tmp_path):
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass_with_issues**\n", encoding="utf-8")
        result = _check_review_report_exists(tmp_path)
        assert result.passed

    def test_blocks_when_no_review_report_regardless_of_fallback(self, tmp_path):
        result = _check_review_report_exists(tmp_path)
        assert not result.passed
        assert "does not exist" in result.message

    def test_review_to_final_blocks_without_review_report(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert not ok
        assert any("review_report_exists" in e for e in errors)

    def test_review_to_final_passes_with_review_report(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok, errors

    def test_review_to_review_checks_review_report_exists(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert not ok
        assert any("review_report" in e.lower() for e in errors)

    def test_review_to_review_passes_with_review_report(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass_with_issues**\n", encoding="utf-8")
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok


class TestEmptyArtifactHandling:
    def test_empty_scope_json_blocks(self, tmp_path):
        _write_json(tmp_path / ARTIFACT_SCOPE, {})
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_scope"})
        ok, errors = proceeds(tmp_path, "scope", "search")
        assert not ok

    def test_empty_collected_json_blocks(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_search"})
        _write_json(tmp_path / ARTIFACT_COLLECTED, [])
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_empty_analysis_json_blocks(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_search"})
        _write_json(tmp_path / ARTIFACT_ANALYSIS, {})
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok

    def test_empty_review_report_blocks(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / ARTIFACT_REVIEW_REPORT).write_text("", encoding="utf-8")
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert not ok
        assert any("review_report_exists" in e for e in errors)


class TestInvalidPhaseTransitions:
    def test_scope_to_final(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_scope"})
        ok, errors = proceeds(tmp_path, "scope", "final")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_search_to_scope_backward(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_search"})
        ok, errors = proceeds(tmp_path, "search", "scope")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_analysis_to_search_backward(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {"topic": "T", "goal_type": "tech_selection", "sections": []},
        )
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_analysis"})
        ok, errors = proceeds(tmp_path, "analysis", "search")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_review_to_analysis_backward(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {"topic": "T", "goal_type": "tech_selection", "sections": []},
        )
        (tmp_path / ARTIFACT_REVIEW_REPORT).write_text("review", encoding="utf-8")
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "analysis")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_final_to_review_backward(self, tmp_path):
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_final"})
        ok, errors = proceeds(tmp_path, "final", "review")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_scope_to_review_skip(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_scope"})
        ok, errors = proceeds(tmp_path, "scope", "review")
        assert not ok
        assert "Invalid transition" in errors[0]

    def test_review_self_loop_allowed(self, tmp_path):
        _write_scope_and_collected(tmp_path)
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Content.",
                        "claims": [{"summary": "C1", "sources": ["https://example.com"]}],
                    },
                ],
            },
        )
        (tmp_path / ARTIFACT_REVIEW_REPORT).write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert ok


class TestRepairHintsInOutput:
    """repair_hints appear in output when gate fails with repair_hints."""

    def test_gateway_cmd_prints_repair_hints(self, tmp_path, capsys, monkeypatch):
        from scripts.lib.check_types import CheckResult

        fake_results = [
            CheckResult("test_check", "BLOCKER", False, "something broke", repair_hints=["fix A", "fix B"]),
            CheckResult("ok_check", "BLOCKER", True, "all good"),
            CheckResult("warn_check", "WARN", False, "minor issue", repair_hints=["try X"]),
        ]
        monkeypatch.setattr("scripts.proceed.get_gateway_results", lambda w: fake_results)
        import scripts.cli as cli_mod

        import argparse
        args = argparse.Namespace(_workdir=tmp_path)
        with pytest.raises(SystemExit):
            cli_mod.cmd_gateway(args)
        captured = capsys.readouterr()
        assert "→ fix A" in captured.out
        assert "→ fix B" in captured.out
        assert "→ try X" in captured.out

    def test_gateway_cmd_no_hints_when_empty(self, tmp_path, capsys, monkeypatch):
        from scripts.lib.check_types import CheckResult

        fake_results = [
            CheckResult("test_check", "BLOCKER", False, "something broke"),
        ]
        monkeypatch.setattr("scripts.proceed.get_gateway_results", lambda w: fake_results)
        import scripts.cli as cli_mod

        import argparse
        args = argparse.Namespace(_workdir=tmp_path)
        with pytest.raises(SystemExit):
            cli_mod.cmd_gateway(args)
        captured = capsys.readouterr()
        assert "→" not in captured.out

    def test_gate_analysis_includes_repair_hints_in_errors(self, tmp_path, monkeypatch):
        from scripts.lib.check_types import CheckResult

        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "tech_selection", "sections": []})

        fake_results = [
            CheckResult("url_traceability", "BLOCKER", False, "bad urls", repair_hints=["check sources", "add missing URLs"]),
            CheckResult("section_coverage", "BLOCKER", True, "ok"),
        ]
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: fake_results)
        monkeypatch.setattr("scripts.lib.schemas.validate_analysis", lambda a: [])
        monkeypatch.setattr("scripts.claim_validator.apply_source_verification", lambda w: None)

        errors = _gate_analysis(tmp_path)
        error_text = "\n".join(errors)
        assert "→ check sources" in error_text
        assert "→ add missing URLs" in error_text

    def test_gate_analysis_no_hints_when_empty(self, tmp_path, monkeypatch):
        from scripts.lib.check_types import CheckResult

        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "tech_selection", "sections": []})

        fake_results = [
            CheckResult("url_traceability", "BLOCKER", False, "bad urls"),
        ]
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: fake_results)
        monkeypatch.setattr("scripts.lib.schemas.validate_analysis", lambda a: [])
        monkeypatch.setattr("scripts.claim_validator.apply_source_verification", lambda w: None)

        errors = _gate_analysis(tmp_path)
        assert not any("→" in e for e in errors)

    def test_gate_search_prints_repair_hints_for_blocker(self, tmp_path, capsys, monkeypatch):
        from scripts.lib.check_types import CheckResult

        fake_results = [
            CheckResult("min_sources", "BLOCKER", False, "too few", repair_hints=["add more sources"]),
            CheckResult("topic_coverage", "WARN", False, "partial", repair_hints=["search broader"]),
        ]
        monkeypatch.setattr("scripts.proceed.SearchGate", lambda w, c: type("SG", (), {"check": lambda s: fake_results})())

        from scripts.proceed import _gate_search
        blockers = _gate_search(tmp_path, None)
        captured = capsys.readouterr()
        assert "→ add more sources" in captured.err
        assert "→ search broader" in captured.err

    def test_gate_review_prints_repair_hints(self, tmp_path, capsys, monkeypatch):
        from scripts.lib.check_types import CheckResult

        fake_results = [
            CheckResult("some_check", "WARN", False, "advisory", repair_hints=["consider fixing"]),
        ]
        monkeypatch.setattr("scripts.proceed.run_gateway", lambda w, g: fake_results)
        monkeypatch.setattr("scripts.proceed._get_goal_type", lambda w: "exploratory")
        (tmp_path / "review_report.md").write_text("## Overall Verdict\n**pass**\n", encoding="utf-8")

        from scripts.proceed import _gate_review
        errors = _gate_review(tmp_path, to_phase="final")
        captured = capsys.readouterr()
        assert "→ consider fixing" in captured.err
        assert errors == []

    def testcheck_report_includes_repair_hints(self, tmp_path, monkeypatch):
        from scripts.lib.check_types import CheckResult

        report_path = tmp_path / "report.md"
        report_path.write_text("bad report", encoding="utf-8")
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        fake_results = [
            CheckResult("report_front_matter", "BLOCKER", False, "missing front matter", repair_hints=["add YAML front matter"]),
        ]
        monkeypatch.setattr("scripts.proceed.run_report_checks", lambda p: fake_results)

        from scripts.proceed import check_report
        errors = check_report(tmp_path)
        error_text = "\n".join(errors)
        assert "→ add YAML front matter" in error_text


class TestCorruptedJsonWithRepairableContent:
    def test_gate_analysis_repairs_unescaped_quotes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / ARTIFACT_PIPELINE_STATE, {"current_phase": "post_search"})
        raw = '{"topic": "AI", "goal_type": "exploratory", "sections": [{"id": "s1", "title": "Overview of "AI" trends", "content": "C", "claims": []}]}'
        (tmp_path / ARTIFACT_ANALYSIS).write_text(raw, encoding="utf-8")
        errors = _gate_analysis(tmp_path)
        assert not any("Invalid JSON" in e for e in errors)
