"""Phase transition gate logic with implicit state detection."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from .gateway import CheckResult
from .gateway import run_all as run_gateway
from .lib.utils import ensure_dir, read_json


def detect_current_phase(workdir: Path) -> str:
    """Return current phase string based on which artifacts exist.

    Returns one of: pre_scope, post_scope, post_search, post_analysis, post_draft, post_review
    """
    if not workdir.exists():
        return "pre_scope"
    scope_present = (workdir / "scope.json").exists()
    collected_present = (workdir / "collected.json").exists()
    analysis_present = (workdir / "analysis.json").exists()
    draft_present = (workdir / "draft" / "report.md").exists()
    review_present = (workdir / "review_report.md").exists()

    if not scope_present:
        phase = "pre_scope"
    elif not collected_present:
        phase = "post_scope"
    elif not analysis_present:
        phase = "post_search"
    elif not draft_present:
        phase = "post_analysis"
    elif not review_present:
        phase = "post_draft"
    else:
        phase = "post_review"
    return phase


_VALID_TRANSITIONS = {
    "scope": "search",
    "search": "analysis",
    "draft": "review",
    "review": "final",
    "final": "cleanup",
}


def _check_scope_schema(workdir: Path) -> list[str]:
    errors = []
    try:
        scope = read_json(workdir / "scope.json")
    except Exception as e:
        return [f"Cannot read scope.json: {e}"]
    required = ["topic", "goal_type", "depth", "audience", "scope_description", "search_directions"]
    for field in required:
        if field not in scope:
            errors.append(f"scope.json missing required field: {field}")
    if scope.get("goal_type") not in (
        "exploratory",
        "panoramic_understanding",
        "tech_selection",
        "feasibility_assessment",
        "competitive_comparison",
        "academic_research",
        "fact_check",
        "background_check",
        "market_analysis",
        "other",
    ):
        errors.append(f"Invalid goal_type: {scope.get('goal_type')}")
    if scope.get("depth") not in ("quick", "standard", "deep"):
        errors.append(f"Invalid depth: {scope.get('depth')}")
    if scope.get("audience") not in ("CTO", "engineer", "researcher", "general"):
        errors.append(f"Invalid audience: {scope.get('audience')} (must be CTO, engineer, researcher, or general)")
    if not scope.get("search_directions"):
        errors.append("scope.json search_directions must be a non-empty list")
    if "report_language" in scope:
        rl = scope["report_language"]
        if not isinstance(rl, str) or not rl:
            errors.append("report_language must be a non-empty string if present")
    return errors


def _check_search_gate(workdir: Path, config: dict | None = None) -> tuple[list[str], list[str]]:
    """Returns (blockers, warnings). Blockers fail the gate, warnings are printed."""
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        collected = read_json(workdir / "collected.json")
    except Exception as e:
        return [f"Cannot read collected.json: {e}"], []
    if not collected or len(collected) < 1:
        blockers.append("collected.json must have at least 1 entry")
    from .lib.source_router import get_default_min_sources

    goal_type = _get_goal_type(workdir)
    min_src = get_default_min_sources(goal_type, config)
    if len(collected) < min_src:
        warnings.append(f"min_sources warning: {len(collected)} < {min_src} (configurable WARN)")
    scope = read_json(workdir / "scope.json")
    needed = set(scope.get("search_directions", []))
    if needed:
        covered = set()
        for entry in collected:
            for keyword in needed:
                if keyword.lower() in (entry.get("title", "") + entry.get("snippet", "")).lower():
                    covered.add(keyword)
        missing = needed - covered
        if missing:
            blockers.append(
                f"topic_coverage BLOCKER: search directions not covered: {', '.join(missing)}"
            )
    return blockers, warnings


def _get_goal_type(workdir: Path) -> str:
    try:
        scope = read_json(workdir / "scope.json")
        return cast(str, scope.get("goal_type", "other"))
    except Exception:
        return "other"


def proceeds(
    workdir: Path, from_phase: str, to_phase: str, config: dict | None = None
) -> tuple[bool, list[str]]:
    """Run gate for the given transition. Returns (passed, error_messages)."""
    ensure_dir(workdir)
    current = detect_current_phase(workdir)
    expected_from = f"post_{from_phase}"
    # final→cleanup has no artifact marker; skip phase match
    if from_phase != "final" and current != expected_from:
        return False, [
            f"Phase mismatch: current={current}, expected={expected_from} for --from {from_phase}"
        ]

    expected_to = _VALID_TRANSITIONS.get(from_phase)
    if expected_to != to_phase:
        return False, [
            f"Invalid transition: --from {from_phase} expects --to {expected_to}, got {to_phase}"
        ]

    errors = []

    if from_phase == "scope":
        errors.extend(_check_scope_schema(workdir))

    elif from_phase == "search":
        search_blockers, search_warnings = _check_search_gate(workdir, config)
        errors.extend(search_blockers)
        for w in search_warnings:
            print(f"  [WARN] {w}", file=sys.stderr)

    elif from_phase == "draft":
        try:
            analysis = read_json(workdir / "analysis.json")
        except Exception as e:
            errors.append(f"Cannot read analysis.json: {e}")
        else:
            if "topic" not in analysis or "goal_type" not in analysis:
                errors.append("analysis.json missing topic or goal_type")
            if not analysis.get("sections"):
                errors.append("analysis.json sections is empty")
        if not (workdir / "draft" / "report.md").exists():
            errors.append("draft/report.md does not exist")

    elif from_phase == "review":
        gateway_results = run_gateway(workdir, _get_goal_type(workdir))
        blockers = [r for r in gateway_results if r.level == "BLOCKER" and not r.passed]
        for b in blockers:
            errors.append(f"[BLOCKER] {b.name}: {b.message}")

    elif from_phase == "final":
        pass

    return len(errors) == 0, errors


def get_gateway_results(workdir: Path) -> list[CheckResult]:
    return run_gateway(workdir, _get_goal_type(workdir))
