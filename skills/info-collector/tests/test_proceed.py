from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.exceptions import ArtifactError
from scripts.proceed import (
    _check_scope_schema,
    _check_search_gate,
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

    def test_post_draft(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        assert detect_current_phase(tmp_path) == "post_draft"

    def test_post_review(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com"}])
        _write_json(tmp_path / "analysis.json", {"topic": "T", "goal_type": "t", "sections": []})
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
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
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI"},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_search_gate_empty_collected(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_search_gate_topic_coverage(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://x.com", "title": "Unrelated", "snippet": "Something else"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok

    def test_search_gate_no_false_positive_substring(self, tmp_path):
        _make_scope(tmp_path, search_directions=["artificial intelligence"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://x.com", "title": "Training RAIN models", "snippet": "About ML"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok
        assert "artificial intelligence" in errors[0].lower()

    def test_search_gate_word_boundary_match(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://x.com", "title": "AI advances in 2026", "snippet": "About AI and ML"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_draft_gate_passes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [{"id": "overview", "title": "O", "content": "C"}],
            },
        )
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        ok, errors = proceeds(tmp_path, "draft", "review")
        assert ok, errors

    def test_draft_gate_missing_draft(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "T",
                "goal_type": "tech_selection",
                "sections": [{"id": "overview", "title": "O", "content": "C"}],
            },
        )
        ok, errors = proceeds(tmp_path, "draft", "review")
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
                        "content": "Kubernetes 1.28 handles 5000 nodes efficiently.",
                        "claims": [{"text": "C1", "source_urls": ["https://a.com"], "verified": True}],
                    },
                    {
                        "id": "comparison",
                        "title": "Cmp",
                        "content": "Docker runs 10000 containers per host with Kubernetes orchestration.",
                        "claims": [{"text": "C2", "source_urls": ["https://a.com"], "verified": True}],
                    },
                    {
                        "id": "recommendation",
                        "title": "Rec",
                        "content": "We recommend Kubernetes for its 5000 node scalability and Docker compatibility.",
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
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "report.md").write_text("# Draft")
        _write_json(tmp_path / "review_report.md", {})
        ok, errors = proceeds(tmp_path, "review", "final")
        assert ok, errors


class TestPerDirectionMinSources:
    """ADR 0010: depth drives per-direction min sources as a WARN gate."""

    def test_depth_quick_passes_with_1_source_per_direction(self, tmp_path):
        """quick depth, 1 source per direction = meets threshold of 1, no WARN."""
        _make_scope(tmp_path, depth="quick", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI"},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML"},
            ],
        )
        from scripts.proceed import _check_search_gate
        blockers, warnings = _check_search_gate(tmp_path)
        # No per-direction WARN since quick requires 1 per direction
        assert not any("per_direction_min_sources" in w for w in warnings)
        # No BLOCKERs either
        assert not blockers
        # proceeds() also passes
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_depth_standard_warns_with_insufficient_sources(self, tmp_path):
        """standard depth with 1 source per direction = below threshold of 3, WARN."""
        _make_scope(tmp_path, depth="standard", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI"},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML"},
            ],
        )
        from scripts.proceed import _check_search_gate
        blockers, warnings = _check_search_gate(tmp_path)
        # Both directions have 1 source, standard requires 3
        per_dir_warns = [w for w in warnings if "per_direction_min_sources" in w]
        assert len(per_dir_warns) == 2  # one per direction
        assert "has 1 sources, depth='standard' requires 3" in per_dir_warns[0]
        # WARN only, not a BLOCKER
        assert not blockers
        # proceeds() still passes (WARN does not block)
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_depth_deep_warns_with_insufficient_sources(self, tmp_path):
        """deep depth with insufficient sources per direction, WARN produced."""
        _make_scope(tmp_path, depth="deep", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI"},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML"},
            ],
        )
        from scripts.proceed import _check_search_gate
        blockers, warnings = _check_search_gate(tmp_path)
        per_dir_warns = [w for w in warnings if "per_direction_min_sources" in w]
        assert len(per_dir_warns) == 2
        assert "has 1 sources, depth='deep' requires 5" in per_dir_warns[0]
        assert not blockers


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
        from scripts.gateway import CheckResult

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

    def test_search_gate_chinese_topic_coverage(self, tmp_path):
        """Chinese search directions should match via jieba tokenization."""
        _make_scope(tmp_path, search_directions=["主流agentic coding框架对比"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "主流agentic coding框架对比", "snippet": "关于框架对比"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors

    def test_search_gate_chinese_topic_coverage_missing(self, tmp_path):
        """Chinese search directions should fail when tokens are missing."""
        _make_scope(tmp_path, search_directions=["主流agentic coding框架对比"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "Unrelated", "snippet": "Something else"},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert not ok
        assert "主流agentic coding框架对比" in errors[0]


class TestTierCoverage:
    """ADR 0007: tier_coverage WARN when route tiers have no sources."""

    def test_all_tiers_covered_no_warn(self, tmp_path):
        """When collected.json has sources from all route tiers, no tier_coverage warning."""
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI", "snippet": "About AI", "source_tier": 2},
                {"url": "https://b.com", "title": "ML", "snippet": "About ML", "source_tier": 1},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok, errors
        # No tier_coverage warning in output
        assert not any("tier_coverage" in e for e in errors)

    def test_missing_tier_produces_warn(self, tmp_path):
        """When a route tier has no sources, tier_coverage WARN is produced."""
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI ML", "snippet": "About AI and ML", "source_tier": 4},
                {"url": "https://b.com", "title": "More AI", "snippet": "About ML too", "source_tier": 4},
            ],
        )
        ok, errors = proceeds(tmp_path, "search", "analysis")
        assert ok  # WARN does not block
        # Should have tier_coverage warning about missing tier 2 and tier 1
        from scripts.proceed import _check_search_gate
        blockers, warnings = _check_search_gate(tmp_path)
        assert any("tier_coverage" in w for w in warnings)


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

    def test_check_search_gate_handles_artifact_error(self, tmp_path, monkeypatch):
        """_check_search_gate catches ArtifactError, returns blocker tuple."""
        def _raise_read_json(*args, **kwargs):
            raise ArtifactError(str(tmp_path / "collected.json"), "file not found")

        monkeypatch.setattr("scripts.proceed.read_json", _raise_read_json)
        blockers, warnings = _check_search_gate(tmp_path)
        assert len(blockers) == 1
        assert "Cannot read collected.json" in blockers[0]
        assert len(warnings) == 0
