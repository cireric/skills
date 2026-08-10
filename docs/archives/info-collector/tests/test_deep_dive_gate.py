"""Tests for deep_dive_gate module (ADR 0064)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.deep_dive_gate import (
    DeepDiveGate,
    determine_convergence,
    generate_deep_dive_plan,
    identify_deep_dive_targets,
)
from scripts.lib.constants import ARTIFACT_ANALYSIS, ARTIFACT_COLLECTED, ARTIFACT_DEEP_DIVE_PLAN, ARTIFACT_SCOPE
from scripts.lib.exceptions import ArtifactError
from scripts.lib.utils import read_json, write_json


def _make_minimal_analysis(workdir: Path, claims=None, tensions=None, single_section=False):
    if single_section:
        sections = [{
            "id": "overview",
            "title": "Overview",
            "content": "Test content with {{ref:https://example.com}}",
            "claims": claims or [],
            "tensions": tensions or [],
        }]
    else:
        sections = [{
            "id": "overview",
            "title": "Overview",
            "content": "Test content with {{ref:https://example.com}}",
            "claims": claims or [],
            "tensions": tensions or [],
        }, {
            "id": "details",
            "title": "Details",
            "content": "More content with {{ref:https://example.com}}",
            "claims": [],
            "tensions": [],
        }]
    _write_json(workdir / ARTIFACT_ANALYSIS, {
        "topic": "Test",
        "goal_type": "exploratory",
        "sections": sections,
    })
    for sec in sections:
        _write_json(workdir / f"analysis_section_{sec['id']}.json", sec)


def _make_minimal_collected(workdir: Path, entries=None):
    _write_json(workdir / ARTIFACT_COLLECTED, entries or [
        {"url": "https://example.com", "title": "Example", "snippet": "test", "source_tier": 2},
    ])


def _make_minimal_scope(workdir: Path, depth="deep"):
    _write_json(workdir / ARTIFACT_SCOPE, {
        "topic": "Test",
        "goal_type": "exploratory",
        "depth": depth,
        "audience": "engineer",
        "scope_description": "Test",
        "search_directions": ["AI"],
    })


def _write_deep_dive_plan(workdir: Path, plan: dict):
    _write_json(workdir / ARTIFACT_DEEP_DIVE_PLAN, plan)


class TestDeepDiveGatePlanExists:

    def test_blocker_when_plan_missing(self, tmp_path):
        gate = DeepDiveGate(tmp_path)
        result = gate._check_plan_exists()
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_pass_when_plan_exists(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3, "targets": []})
        gate = DeepDiveGate(tmp_path)
        result = gate._check_plan_exists()
        assert result.passed

    def test_blocker_when_plan_missing_targets(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3})
        gate = DeepDiveGate(tmp_path)
        result = gate._check_plan_exists()
        assert not result.passed


class TestDeepDiveGateTargetCompletion:

    def test_blocker_when_pending_targets(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "pending", "trigger_reason": "source_absent", "round_created": 1}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_target_completion()
        assert not result.passed
        assert "dd_1" in result.message

    def test_pass_when_all_completed(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_target_completion()
        assert result.passed

    def test_pass_when_skipped_with_reason(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "skipped", "trigger_reason": "source_absent", "round_created": 1, "skip_reason": "No sources available"}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_target_completion()
        assert result.passed

    def test_blocker_when_skipped_without_reason(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "skipped", "trigger_reason": "source_absent", "round_created": 1}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_target_completion()
        assert not result.passed
        assert "skip_reason" in result.message.lower() or "skipped" in result.message.lower()


class TestDeepDiveGateSourceDepth:

    def test_blocker_when_insufficient_new_sources(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com"]}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_source_depth()
        assert not result.passed
        assert "dd_1" in result.message

    def test_pass_when_sufficient_sources(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_source_depth()
        assert result.passed

    def test_skipped_targets_not_checked(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "skipped", "trigger_reason": "source_absent", "round_created": 1, "skip_reason": "N/A", "new_sources": []}],
        })
        gate = DeepDiveGate(tmp_path)
        result = gate._check_source_depth()
        assert result.passed


class TestDeepDiveGateVerification:

    def test_blocker_when_source_absent_in_targeted_section(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "section_id": "overview", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
        })
        _make_minimal_analysis(tmp_path, claims=[{
            "summary": "Test claim",
            "sources": ["https://example.com"],
            "source_verification": "source_absent",
        }])
        gate = DeepDiveGate(tmp_path)
        result = gate._check_verification()
        assert not result.passed

    def test_pass_when_source_absent_only_in_non_targeted_section(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "section_id": "details", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
        })
        _make_minimal_analysis(tmp_path, claims=[{
            "summary": "Test claim",
            "sources": ["https://example.com"],
            "source_verification": "source_absent",
        }])
        gate = DeepDiveGate(tmp_path)
        result = gate._check_verification()
        assert result.passed

    def test_pass_when_no_source_absent(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
        })
        _make_minimal_analysis(tmp_path, claims=[{
            "summary": "Test claim",
            "sources": ["https://example.com"],
            "source_verification": "source_confirmed",
        }])
        gate = DeepDiveGate(tmp_path)
        result = gate._check_verification()
        assert result.passed


class TestDeepDiveGateConvergenceDeclared:

    def test_warn_when_convergence_none(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3, "targets": [], "convergence": None})
        gate = DeepDiveGate(tmp_path)
        result = gate._check_convergence_declared()
        assert result.level == "WARN"
        assert result.passed

    def test_pass_when_convergence_set(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3, "targets": [], "convergence": {"type": "natural", "reason": "test"}})
        gate = DeepDiveGate(tmp_path)
        result = gate._check_convergence_declared()
        assert result.passed


class TestDeepDiveGateRoundBudget:

    def test_info_shows_round(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 2, "max_rounds": 3, "targets": []})
        gate = DeepDiveGate(tmp_path)
        result = gate._check_round_budget()
        assert result.level == "INFO"
        assert "2/3" in result.message


class TestIdentifyDeepDiveTargets:

    def test_identifies_source_absent_claims(self, tmp_path):
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Claim 1", "sources": ["https://a.com"], "source_verification": "source_absent"},
            {"summary": "Claim 2", "sources": ["https://b.com"], "source_verification": "source_confirmed"},
        ])
        targets = identify_deep_dive_targets(tmp_path)
        source_absent_targets = [t for t in targets if t["trigger_reason"] == "source_absent"]
        assert len(source_absent_targets) >= 1

    def test_identifies_source_indirect_ratio(self, tmp_path):
        claims = [
            {"summary": f"Claim {i}", "sources": ["https://a.com"], "source_verification": "source_indirect"}
            for i in range(4)
        ] + [
            {"summary": "Claim ok", "sources": ["https://b.com"], "source_verification": "source_confirmed"},
        ]
        _make_minimal_analysis(tmp_path, claims=claims)
        targets = identify_deep_dive_targets(tmp_path)
        indirect_targets = [t for t in targets if t["trigger_reason"] == "source_indirect"]
        assert len(indirect_targets) >= 1

    def test_identifies_single_source_claims(self, tmp_path):
        claims = [
            {"summary": f"Claim {i}", "sources": ["https://a.com"], "source_verification": "source_confirmed"}
            for i in range(4)
        ] + [
            {"summary": "Multi source", "sources": ["https://a.com", "https://b.com"], "source_verification": "source_confirmed"},
        ]
        _make_minimal_analysis(tmp_path, claims=claims)
        targets = identify_deep_dive_targets(tmp_path)
        single_targets = [t for t in targets if t["trigger_reason"] == "single_source"]
        assert len(single_targets) >= 1

    def test_identifies_unresolved_tensions(self, tmp_path):
        _make_minimal_analysis(tmp_path, tensions=[
            {"summary": "Unresolved tension", "sources": ["https://a.com"], "resolved": False},
        ])
        targets = identify_deep_dive_targets(tmp_path)
        tension_targets = [t for t in targets if t["trigger_reason"] == "tension_unresolved"]
        assert len(tension_targets) >= 1

    def test_groups_tensions_by_section(self, tmp_path):
        _make_minimal_analysis(tmp_path, tensions=[
            {"summary": "Tension 1", "sources": ["https://a.com"], "resolved": False},
            {"summary": "Tension 2", "sources": ["https://b.com"], "resolved": False},
            {"summary": "Tension 3", "sources": ["https://c.com"], "resolved": False},
        ])
        targets = identify_deep_dive_targets(tmp_path)
        tension_targets = [t for t in targets if t["trigger_reason"] == "tension_unresolved"]
        assert len(tension_targets) == 1
        assert "Tension 1" in tension_targets[0]["claim_summary"]
        assert "Tension 2" in tension_targets[0]["claim_summary"]

    def test_returns_empty_when_no_triggers(self, tmp_path):
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good claim", "sources": ["https://a.com", "https://b.com"], "source_verification": "source_confirmed"},
        ])
        targets = identify_deep_dive_targets(tmp_path)
        assert targets == []

    def test_returns_empty_when_analysis_missing(self, tmp_path):
        targets = identify_deep_dive_targets(tmp_path)
        assert targets == []


class TestDetermineConvergence:

    def test_hard_when_round_exceeds_max(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 3, "max_rounds": 3, "targets": [], "convergence": None})
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://a.com", "https://b.com"], "source_verification": "source_confirmed"},
        ])
        result = determine_convergence(tmp_path)
        assert result is not None
        assert result["type"] == "hard"

    def test_natural_when_all_triggers_resolved(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3, "targets": [], "convergence": None})
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://a.com", "https://b.com"], "source_verification": "source_confirmed"},
        ])
        result = determine_convergence(tmp_path)
        assert result is not None
        assert result["type"] == "natural"

    def test_none_when_triggers_remain(self, tmp_path):
        _write_deep_dive_plan(tmp_path, {"round": 1, "max_rounds": 3, "targets": [], "convergence": None})
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Absent", "sources": ["https://a.com"], "source_verification": "source_absent"},
            {"summary": "Absent2", "sources": ["https://b.com"], "source_verification": "source_absent"},
        ])
        result = determine_convergence(tmp_path)
        assert result is None

    def test_hard_when_plan_missing(self, tmp_path):
        result = determine_convergence(tmp_path)
        assert result is not None
        assert result["type"] == "hard"


class TestGenerateDeepDivePlan:

    def test_generates_valid_plan(self, tmp_path):
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Absent claim", "sources": ["https://a.com"], "source_verification": "source_absent"},
            {"summary": "Absent claim 2", "sources": ["https://b.com"], "source_verification": "source_absent"},
        ])
        plan = generate_deep_dive_plan(tmp_path)
        assert plan["round"] == 1
        assert plan["max_rounds"] == 3
        assert len(plan["targets"]) >= 1
        assert plan["convergence"] is None

    def test_plan_file_written(self, tmp_path):
        _make_minimal_analysis(tmp_path, claims=[])
        generate_deep_dive_plan(tmp_path)
        assert (tmp_path / ARTIFACT_DEEP_DIVE_PLAN).exists()

    def test_merges_with_existing_plan(self, tmp_path):
        existing = {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
            "convergence": None,
        }
        _write_deep_dive_plan(tmp_path, existing)
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Absent claim", "sources": ["https://a.com"], "source_verification": "source_absent"},
            {"summary": "Absent claim 2", "sources": ["https://b.com"], "source_verification": "source_absent"},
        ])
        plan = generate_deep_dive_plan(tmp_path, round_num=2)
        assert plan["round"] == 2
        assert len(plan["targets"]) >= 2  # existing + new

    def test_no_targets_when_analysis_clean(self, tmp_path):
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://a.com", "https://b.com"], "source_verification": "source_confirmed"},
        ])
        plan = generate_deep_dive_plan(tmp_path)
        assert len(plan["targets"]) == 0


class TestDeepDiveProceed:

    def test_analysis_to_deep_dive_transition(self, tmp_path):
        from scripts.proceed import proceeds
        _make_minimal_scope(tmp_path, depth="deep")
        _make_minimal_collected(tmp_path)
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://example.com"], "source_verification": "source_confirmed"},
        ])
        ok, errors = proceeds(tmp_path, "analysis", "deep_dive")
        assert ok, errors

    def test_deep_dive_to_search_with_pending_targets(self, tmp_path):
        from scripts.proceed import proceeds, write_phase_state
        write_phase_state(tmp_path, "post_deep_dive")
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "pending", "trigger_reason": "source_absent", "round_created": 1}],
            "convergence": None,
        })
        ok, errors = proceeds(tmp_path, "deep_dive", "search")
        assert ok, errors

    def test_deep_dive_to_search_blocked_when_all_completed(self, tmp_path):
        from scripts.proceed import proceeds, write_phase_state
        write_phase_state(tmp_path, "post_deep_dive")
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
            "convergence": None,
        })
        ok, errors = proceeds(tmp_path, "deep_dive", "search")
        assert not ok

    def test_deep_dive_to_review_when_all_complete(self, tmp_path):
        from scripts.proceed import proceeds, write_phase_state
        write_phase_state(tmp_path, "post_deep_dive")
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
            "convergence": {"type": "natural", "reason": "all triggers resolved"},
        })
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://example.com"], "source_verification": "source_confirmed"},
        ])
        ok, errors = proceeds(tmp_path, "deep_dive", "review")
        assert ok, errors

    def test_deep_dive_to_review_blocked_when_source_absent(self, tmp_path):
        from scripts.proceed import proceeds, write_phase_state
        write_phase_state(tmp_path, "post_deep_dive")
        _write_deep_dive_plan(tmp_path, {
            "round": 1, "max_rounds": 3,
            "targets": [{"id": "dd_1", "status": "completed", "trigger_reason": "source_absent", "round_created": 1, "new_sources": ["https://a.com", "https://b.com", "https://c.com"]}],
            "convergence": {"type": "natural", "reason": "all triggers resolved"},
        })
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Still absent", "sources": ["https://example.com"], "source_verification": "source_absent"},
        ])
        ok, errors = proceeds(tmp_path, "deep_dive", "review")
        assert not ok

    def test_analysis_to_review_still_works_for_standard(self, tmp_path):
        from scripts.proceed import proceeds
        _make_minimal_scope(tmp_path, depth="standard")
        _make_minimal_collected(tmp_path)
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://example.com"], "source_verification": "source_confirmed"},
        ])
        ok, errors = proceeds(tmp_path, "analysis", "review")
        assert ok, errors

    def test_analysis_to_deep_dive_requires_post_analysis_phase(self, tmp_path):
        from scripts.proceed import proceeds
        ok, errors = proceeds(tmp_path, "analysis", "deep_dive")
        assert not ok  # no artifacts → phase mismatch

    def test_analysis_to_deep_dive_blocked_when_depth_not_deep(self, tmp_path):
        from scripts.proceed import proceeds, write_phase_state
        _make_minimal_scope(tmp_path, depth="standard")
        _make_minimal_collected(tmp_path)
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Good", "sources": ["https://example.com"], "source_verification": "source_confirmed"},
        ])
        write_phase_state(tmp_path, "post_analysis")
        ok, errors = proceeds(tmp_path, "analysis", "deep_dive")
        assert not ok
        assert any("depth" in e.lower() for e in errors)


class TestDeepDiveSchemaIntegration:

    def test_generated_plan_passes_schema(self, tmp_path):
        from scripts.lib.schemas import validate_deep_dive_plan
        _make_minimal_analysis(tmp_path, claims=[
            {"summary": "Absent claim", "sources": ["https://a.com"], "source_verification": "source_absent"},
            {"summary": "Absent claim 2", "sources": ["https://b.com"], "source_verification": "source_absent"},
        ])
        plan = generate_deep_dive_plan(tmp_path)
        errors = validate_deep_dive_plan(plan)
        assert errors == [], [f"{e.field}: {e.message}" for e in errors]
