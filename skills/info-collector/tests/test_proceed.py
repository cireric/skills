from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.exceptions import ArtifactError
from scripts.proceed import (
    _check_scope_schema,
    _sanitize_sections,
    write_phase_state,
    detect_current_phase,
    get_gateway_results,
    proceeds,
)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_scope(workdir, goal_type="tech_selection", depth="standard", report_language=None, search_directions=None):
    data = {
        "topic": "Test",
        "goal_type": goal_type,
        "depth": depth,
        "audience": "engineer",
        "scope_description": "Test scope",
        "search_directions": search_directions if search_directions is not None else ["AI", "ML"],
    }
    if report_language is not None:
        data["report_language"] = report_language
    _write_json(workdir / "scope.json", data)


def _make_completed_search_plan(workdir, directions=None):
    if directions is None:
        scope = json.loads((workdir / "scope.json").read_text(encoding="utf-8"))
        directions = scope.get("search_directions", ["AI", "ML"])
    tasks = [{"direction": d, "tier": 4, "status": "completed", "collected_count": 1} for d in directions]
    _write_json(workdir / "search_plan.json", {"tasks": tasks})


def _write_scope_and_collected(workdir):
    scope = {"topic": "t", "goal_type": "exploratory", "depth": "quick", "audience": "engineer", "scope_description": "d", "search_directions": ["d1"]}
    _write_json(workdir / "scope.json", scope)
    _write_json(workdir / "collected.json", [{"url": "https://example.com", "title": "x", "snippet": "d1", "source_tier": 4, "fetched_content": "x" * 500}])
    _make_completed_search_plan(workdir, directions=["d1"])


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
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML", "fetched_content": "x" * 300},
            ],
        )
        _make_completed_search_plan(tmp_path)
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
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                        "claims": [{"text": "C1", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration {{ref:https://a.com}}.",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility {{ref:https://a.com}}.",
                        "claims": [{"text": "C3", "source_urls": ["https://a.com"]}],
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
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok, errors

    def test_analysis_to_review_gate_blocks_untraceable_urls(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                        "claims": [{"text": "C1", "source_urls": ["https://fabricated.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"text": "C3", "source_urls": ["https://a.com"]}],
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
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok
        assert any("url_traceability" in e for e in errors)

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
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "overview",
                        "title": "O",
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently {{ref:https://a.com}}.",
                        "claims": [{"text": "C1", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration {{ref:https://a.com}}.",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility {{ref:https://a.com}}.",
                        "claims": [{"text": "C3", "source_urls": ["https://a.com"], "verified": True}],
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
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok, errors


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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "C",
                        "claims": [{"text": "C2", "source_urls": ["https://example.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "C",
                        "claims": [{"text": "C3", "source_urls": ["https://example.com"]}],
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
        from scripts.artifact_checks import CheckResult

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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"]}],
                    },
                    {
                        "id": "details",
                        "title": "Details",
                        "content": "D",
                        "claims": [{"text": "C2", "source_urls": ["https://example.com"]}],
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

    def test_sources_mapped_to_source_urls_in_claims(self):
        raw = {
            "topic": "T", "goal_type": "exploratory",
            "sections": [{"id": "s1", "title": "S1", "content": "C", "claims": [{"text": "claim1", "sources": ["https://a.com"]}]}],
        }
        result = _sanitize_sections(raw)
        claim = result["sections"][0]["claims"][0]
        assert "sources" not in claim
        assert claim["source_urls"] == ["https://a.com"]

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
            "sections": [{"id": "s1", "title": "S1", "content": "C", "claims": [{"text": "c1", "source_urls": ["https://a.com"], "relevance_score": 0.9}]}],
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
                    "claims": [{"text": "c1", "source_urls": ["https://a.com"], "verified": True}],
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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"], "verified": True}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "C2", "source_urls": ["https://example.com"], "verified": True}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"text": "C3", "source_urls": ["https://example.com"], "verified": True}],
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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"], "verified": False}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "C2", "source_urls": ["https://example.com"], "verified": False}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"text": "C3", "source_urls": ["https://example.com"], "verified": False}],
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
        assert not ok
        assert any("claim_verified" in e for e in errors)


class TestGateFinalOnlyBlocksBlocker:
    """BUG-1 fix: _gate_final only blocks on BLOCKER-level failures, not WARN."""

    def test_warn_does_not_block_final_to_cleanup(self, tmp_path, monkeypatch):
        report = "---\ntopic: T\ngoal_type: exploratory\ndate: 2026-06-26\nquality: draft\n---\n## Overview\nContent with cite [&#91;1&#93;](#refs).\n\n## References\n- **[1]** Title — [URL](https://a.com)\n"
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)
        ok, errors = proceeds(tmp_path, "final", "cleanup")
        assert ok, f"WARN-only failures should not block: {errors}"

    def test_blocker_blocks_final_to_cleanup(self, tmp_path, monkeypatch):
        report = "No front matter, no references."
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)
        ok, errors = proceeds(tmp_path, "final", "cleanup")
        assert not ok
        assert any("report_front_matter" in e for e in errors)

class TestSearchPlanStatus:
    def test_search_plan_includes_status_field(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI trends"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {"4": {"sources": [{"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"}]}},
            "routes": {"exploratory": {"entry_tier": 4, "path": [4]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in plan["tasks"]:
            assert "status" in task
            assert task["status"] == "pending"
            assert "collected_count" in task
            assert task["collected_count"] == 0


class TestIntegrationMediumComplexity:
    def test_state_file_survives_review_self_loop(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        config = {
            "sources": {"4": {"sources": [{"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"}]}},
            "routes": {"exploratory": {"entry_tier": 4, "path": [4]}},
        }
        scope = {"topic": "t", "goal_type": "exploratory", "depth": "quick", "audience": "engineer", "scope_description": "d", "search_directions": ["d1"]}
        _write_json(workdir / "scope.json", scope)
        proceeds(workdir, "scope", "search", config)
        assert detect_current_phase(workdir) == "post_search"
        collected = [{"url": "https://example.com", "title": "d1 info", "snippet": "d1", "source_tier": 4, "fetched_content": "x" * 500}]
        _write_json(workdir / "collected.json", collected)
        _make_completed_search_plan(workdir, directions=["d1"])
        proceeds(workdir, "search", "analysis")
        assert detect_current_phase(workdir) == "post_analysis"
        analysis = {"topic": "t", "goal_type": "exploratory", "sections": [
            {"id": "overview", "title": "Overview", "content": "test", "claims": []},
            {"id": "findings", "title": "Findings", "content": "test findings", "claims": []}
        ]}
        _write_json(workdir / "analysis.json", analysis)
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
                        "claims": [{"text": "C1", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"]}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
                        "claims": [{"text": "C3", "source_urls": ["https://a.com"]}],
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

    def test_section_coverage_blocker_caught(self, tmp_path):
        self._make_passing_analysis(tmp_path)
        analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
        analysis["sections"] = [analysis["sections"][0]]
        _write_json(tmp_path / "analysis.json", analysis)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok
        assert any("section_coverage" in e for e in errors)

    def test_content_concreteness_blocker_caught(self, tmp_path):
        self._make_passing_analysis(tmp_path)
        analysis = json.loads((tmp_path / "analysis.json").read_text(encoding="utf-8"))
        analysis["sections"][0]["content"] = "Some vague text without numbers or names."
        analysis["sections"][0]["claims"] = [{"text": "vague claim", "source_urls": ["https://a.com"]}]
        _write_json(tmp_path / "analysis.json", analysis)
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert not ok
        assert any("content_concreteness" in e for e in errors)


class TestSearchPlanLanguageSplit:
    def test_mixed_en_zh_sources_creates_separate_tasks(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "3": {
                    "sources": [
                        {"name": "Medium", "domain": "medium.com", "site_query": "medium.com AI", "language": "en"},
                        {"name": "Zhihu", "domain": "zhihu.com", "site_query": "zhihu.com AI", "language": "zh"},
                    ]
                },
            },
            "routes": {"exploratory": {"entry_tier": 3, "path": [3]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        en_tasks = [t for t in plan["tasks"] if t["query_language"] == "en"]
        zh_tasks = [t for t in plan["tasks"] if t["query_language"] == "zh"]
        assert len(en_tasks) == 1
        assert len(zh_tasks) == 1
        assert en_tasks[0]["site_queries"] == ["medium.com AI"]
        assert zh_tasks[0]["site_queries"] == ["zhihu.com AI"]

    def test_en_only_sources_creates_only_en_task(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "3": {
                    "sources": [
                        {"name": "Medium", "domain": "medium.com", "site_query": "medium.com AI"},
                        {"name": "Dev.to", "domain": "dev.to", "site_query": "dev.to AI"},
                    ]
                },
            },
            "routes": {"exploratory": {"entry_tier": 3, "path": [3]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        assert len(plan["tasks"]) == 1
        assert plan["tasks"][0]["query_language"] == "en"
        assert len(plan["tasks"][0]["site_queries"]) == 2

    def test_zh_only_sources_creates_only_zh_task(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "3": {
                    "sources": [
                        {"name": "Zhihu", "domain": "zhihu.com", "site_query": "zhihu.com AI", "language": "zh"},
                        {"name": "CSDN", "domain": "csdn.net", "site_query": "csdn.net AI", "language": "zh"},
                    ]
                },
            },
            "routes": {"exploratory": {"entry_tier": 3, "path": [3]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        assert len(plan["tasks"]) == 1
        assert plan["tasks"][0]["query_language"] == "zh"
        assert len(plan["tasks"][0]["site_queries"]) == 2

    def test_fetch_hints_per_language_group(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "academic_research", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "1": {
                    "sources": [
                        {"name": "arXiv", "domain": "arxiv.org", "site_query": "arxiv.org AI", "language": "en"},
                        {"name": "CNKI", "domain": "cnki.net", "site_query": "cnki.net AI", "language": "zh"},
                    ]
                },
            },
            "routes": {"academic_research": {"entry_tier": 1, "path": [1]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        en_task = next(t for t in plan["tasks"] if t["query_language"] == "en")
        zh_task = next(t for t in plan["tasks"] if t["query_language"] == "zh")
        assert "fetch_hints" in en_task
        assert "full paper" in en_task["fetch_hints"].lower()
        assert zh_task.get("fetch_hints", "") == ""

    def test_multiple_directions_doubles_tasks(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI", "ML"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "3": {
                    "sources": [
                        {"name": "Medium", "domain": "medium.com", "site_query": "medium.com", "language": "en"},
                        {"name": "Zhihu", "domain": "zhihu.com", "site_query": "zhihu.com", "language": "zh"},
                    ]
                },
            },
            "routes": {"exploratory": {"entry_tier": 3, "path": [3]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        assert len(plan["tasks"]) == 4
        en_tasks = [t for t in plan["tasks"] if t["query_language"] == "en"]
        zh_tasks = [t for t in plan["tasks"] if t["query_language"] == "zh"]
        assert len(en_tasks) == 2
        assert len(zh_tasks) == 2

    def test_no_is_chinese_tier_logic(self, tmp_path):
        workdir = tmp_path / ".workdir"
        workdir.mkdir()
        scope = {
            "topic": "t", "goal_type": "exploratory", "depth": "quick",
            "audience": "engineer", "scope_description": "d",
            "search_directions": ["AI"],
        }
        _write_json(workdir / "scope.json", scope)
        config = {
            "sources": {
                "3": {
                    "sources": [
                        {"name": "SomeCN", "domain": "example.com.cn", "site_query": "example.com.cn AI", "language": "en"},
                    ]
                },
            },
            "routes": {"exploratory": {"entry_tier": 3, "path": [3]}},
        }
        proceeds(workdir, "scope", "search", config)
        plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        assert len(plan["tasks"]) == 1
        assert plan["tasks"][0]["query_language"] == "en"


class TestGateReviewOnlyChecksReviewItems:
    """L3: _gate_review only checks claim_verified and claim_source_relevance."""

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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"], "verified": True}],
                    },
                ],
            },
        )
        _write_json(tmp_path / "review_report.md", {})
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert not any("section_coverage" in e for e in errors)

    def test_review_gate_blocks_on_unverified_claims(self, tmp_path):
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
                        "claims": [{"text": "C1", "source_urls": ["https://example.com"], "verified": False}],
                    },
                ],
            },
        )
        _write_json(tmp_path / "review_report.md", {})
        _write_json(tmp_path / "pipeline_state.json", {"current_phase": "post_review"})
        ok, errors = proceeds(tmp_path, "review", "review")
        assert not ok
        assert any("claim_verified" in e for e in errors)
