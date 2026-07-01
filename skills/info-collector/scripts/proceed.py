"""Phase transition gate logic with explicit state file detection."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from .lib.utils import config_path, find_project_root, ensure_dir, read_json, write_json, build_collected_url_set
from .artifact_checks import CheckResult, run_all as run_gateway
from .report_checks import run_report_checks
from .search_gate import SearchGate
from .lib.source_router import get_route, recommend_sources
from .lib.exceptions import ArtifactError
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_PIPELINE_STATE,
    ARTIFACT_REVIEW_REPORT,
    ARTIFACT_SCOPE,
    ARTIFACT_SEARCH_PLAN,
    _DEPTH_MIN_SOURCES_PER_DIRECTION,
    _NON_EXACT_EVIDENCE_TYPES,
    _VALID_TRANSITIONS_SET,
)

_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({
    "text", "source_urls", "evidence_type", "confidence",
    "precision", "metric_type", "source_metadata", "verified",
    "source_verification",
})


def _sanitize_sections(analysis: dict, collected_urls: set[str] | None = None) -> dict:
    """Clean subagent output before schema validation."""
    result = dict(analysis)
    sections = result.get("sections")
    if not isinstance(sections, list):
        return result

    cleaned_sections = []
    for section in sections:
        if not isinstance(section, dict):
            cleaned_sections.append(section)
            continue
        sec = dict(section)
        if "section_id" in sec and "id" not in sec:
            sec["id"] = sec.pop("section_id")
        if "claims" not in sec:
            sec["claims"] = []
        claims = sec.get("claims")
        if isinstance(claims, list):
            cleaned_claims = []
            for claim in claims:
                if not isinstance(claim, dict):
                    cleaned_claims.append(claim)
                    continue
                cl = dict(claim)
                if "sources" in cl and "source_urls" not in cl:
                    cl["source_urls"] = cl.pop("sources")
                # Auto-fix precision inflation: downgrade exact -> range for non-official evidence
                if (
                    cl.get("precision") == "exact"
                    and cl.get("evidence_type") in _NON_EXACT_EVIDENCE_TYPES
                ):
                    cl["precision"] = "range"
                # Auto-fix URL traceability: remove source_urls not in collected.json
                if collected_urls is not None and "source_urls" in cl:
                    valid = [u for u in cl["source_urls"] if u in collected_urls]
                    if valid:
                        cl["source_urls"] = valid
                cleaned_claims.append({k: v for k, v in cl.items() if k in _CLAIM_KEYS})
            sec["claims"] = cleaned_claims
        cleaned_sections.append({k: v for k, v in sec.items() if k in _SECTION_KEYS})
    result["sections"] = cleaned_sections
    return result


def write_phase_state(workdir: Path, phase: str) -> None:
    state_path = workdir / ARTIFACT_PIPELINE_STATE
    try:
        write_json({"current_phase": phase}, state_path)
    except OSError as e:
        print(f"Warning: failed to write phase state: {e}", file=sys.stderr)


def detect_current_phase(workdir: Path) -> str:
    """Return current phase string based on state file or artifact presence.

    Returns one of: pre_scope, post_scope, post_search, post_analysis, post_review
    """
    if not workdir.exists():
        return "pre_scope"
    state_path = workdir / ARTIFACT_PIPELINE_STATE
    if state_path.exists():
        try:
            state = read_json(state_path)
            phase = state.get("current_phase", "")
            if phase in ("pre_scope", "post_scope", "post_search", "post_analysis", "post_review"):
                return phase
        except (ArtifactError, OSError):
            pass
    scope_present = (workdir / ARTIFACT_SCOPE).exists()
    collected_present = (workdir / ARTIFACT_COLLECTED).exists()
    analysis_present = (workdir / ARTIFACT_ANALYSIS).exists()
    review_present = (workdir / ARTIFACT_REVIEW_REPORT).exists()

    if not scope_present:
        phase = "pre_scope"
    elif not collected_present:
        phase = "post_scope"
    elif not analysis_present:
        phase = "post_search"
    elif not review_present:
        phase = "post_analysis"
    else:
        phase = "post_review"
    return phase


def _check_scope_schema(workdir: Path) -> list[str]:
    try:
        scope = read_json(workdir / ARTIFACT_SCOPE)
    except ArtifactError as e:
        return [f"Cannot read scope.json: {e}"]
    from .lib.schemas import validate_scope
    return [f"scope.json {e.field}: {e.message}" for e in validate_scope(scope)]


def _get_goal_type(workdir: Path) -> str:
    try:
        scope = read_json(workdir / ARTIFACT_SCOPE)
        return cast(str, scope.get("goal_type", "other"))
    except ArtifactError:
        return "other"


def _build_fetch_hints(sources: list[dict]) -> str:
    tier_domains = [s.get("domain", "") for s in sources]
    if any("arxiv.org" in d for d in tier_domains):
        return "MUST fetch full paper content (not just abstract) using exa_web_fetch_exa; search-result snippets are insufficient for Tier 1 academic sources"
    if any("github.com" in d for d in tier_domains):
        return "Prefer fetching README, key source files, or documentation rather than just the repo listing"
    return ""


def _generate_search_plan(workdir: Path, config: dict | None = None) -> None:
    """Generate search_plan.json based on route × search_directions (ADR 0011)."""
    scope = read_json(workdir / ARTIFACT_SCOPE)
    goal_type = scope.get("goal_type", "other")
    directions = scope.get("search_directions", [])
    depth = scope.get("depth", "standard")

    route = get_route(goal_type, config)
    route_path = route.get("path", [])
    rec = recommend_sources(goal_type, config)
    recommended = rec.get("recommended_sources", {})

    min_per_direction = _DEPTH_MIN_SOURCES_PER_DIRECTION.get(depth, 3)

    tasks = []
    for direction in directions:
        for tier in route_path:
            tier_sources = recommended.get(tier, [])
            en_sources = [s for s in tier_sources if s.get("language", "en") == "en"]
            zh_sources = [s for s in tier_sources if s.get("language", "en") == "zh"]

            if en_sources:
                site_queries = [s.get("site_query", s.get("domain", "")) for s in en_sources]
                fetch_hints = _build_fetch_hints(en_sources)
                task = {
                    "direction": direction, "tier": tier, "query_language": "en",
                    "site_queries": site_queries, "fetch_hints": fetch_hints,
                    "min_sources": min_per_direction, "status": "pending", "collected_count": 0,
                }
                tasks.append(task)

            if zh_sources:
                site_queries = [s.get("site_query", s.get("domain", "")) for s in zh_sources]
                fetch_hints = _build_fetch_hints(zh_sources)
                task = {
                    "direction": direction, "tier": tier, "query_language": "zh",
                    "site_queries": site_queries, "fetch_hints": fetch_hints,
                    "min_sources": min_per_direction, "status": "pending", "collected_count": 0,
                }
                tasks.append(task)

    write_json({"goal_type": goal_type, "depth": depth, "route": route_path, "tasks": tasks}, workdir / ARTIFACT_SEARCH_PLAN)


def _find_report_path(workdir: Path) -> Path | None:
    """Find the latest .md report file in the configured output directory."""
    project_root = find_project_root()
    cfg_path = config_path()
    output_dir = project_root / "./reports/"
    if cfg_path.exists():
        try:
            with open(cfg_path, encoding="utf-8") as f:
                config = json.load(f)
            output_dir = project_root / config.get("output_dir", "./reports/")
        except (OSError, json.JSONDecodeError):
            pass
    if not output_dir.exists():
        return None
    md_files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return md_files[0] if md_files else None


def _gate_scope(workdir: Path, config: dict | None) -> list[str]:
    errors = _check_scope_schema(workdir)
    if not errors:
        _generate_search_plan(workdir, config)
    return errors


def _gate_search(workdir: Path, config: dict | None) -> list[str]:
    results = SearchGate(workdir, config).check()
    blockers = []
    for r in results:
        if r.passed:
            continue
        if r.level == "BLOCKER":
            blockers.append(r.message)
        else:
            print(f"  [WARN] {r.message}", file=sys.stderr)
    return blockers


def _gate_analysis(workdir: Path) -> list[str]:
    errors: list[str] = []
    try:
        analysis = read_json(workdir / ARTIFACT_ANALYSIS)
    except ArtifactError as e:
        errors.append(f"Cannot read analysis.json: {e}")
        return errors
    collected_urls: set[str] | None = None
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
        if isinstance(collected, list):
            collected_urls = build_collected_url_set(collected)
    except ArtifactError:
        pass
    analysis = _sanitize_sections(analysis, collected_urls=collected_urls)
    write_json(analysis, workdir / ARTIFACT_ANALYSIS)
    from .lib.schemas import validate_analysis
    schema_errors = validate_analysis(analysis)
    if schema_errors:
        errors.extend(f"analysis.json {e.field}: {e.message}" for e in schema_errors)
    else:
        gateway_results = run_gateway(workdir, _get_goal_type(workdir))
        analysis_check_names = {
            "artifact_exists", "url_traceability", "section_coverage",
            "analysis_schema", "precision_inflation", "claim_metadata",
            "content_concreteness", "quality_heuristics", "source_tier_balance",
            "source_metadata", "metric_type_homogeneity", "claim_dedup",
            "methodology_depth", "recommendation_structure",
            "ref_marker_validity", "claim_source_ref_coverage",
            "source_verification_check",
        }
        blockers = [
            r for r in gateway_results
            if r.level == "BLOCKER" and not r.passed and r.name in analysis_check_names
        ]
        errors.extend(f"[BLOCKER] {b.name}: {b.message}" for b in blockers)
    from .claim_validator import apply_source_verification
    apply_source_verification(workdir)
    return errors


def _gate_review(workdir: Path) -> list[str]:
    gateway_results = run_gateway(workdir, _get_goal_type(workdir))
    for r in gateway_results:
        if not r.passed:
            print(f"  [ADVISORY] {r.name}: {r.message}", file=sys.stderr)
    return []


def _gate_final(workdir: Path) -> list[str]:
    report_path = _find_report_path(workdir)
    if report_path is None:
        return ["No report file found in output directory for 3d verification"]
    report_results = run_report_checks(report_path)
    blockers = [r for r in report_results if r.level == "BLOCKER" and not r.passed]
    return [f"[BLOCKER] {b.name}: {b.message}" for b in blockers]


def proceeds(
    workdir: Path, from_phase: str, to_phase: str, config: dict | None = None
) -> tuple[bool, list[str]]:
    """Run gate for the given transition. Returns (passed, error_messages)."""
    ensure_dir(workdir)
    current = detect_current_phase(workdir)
    expected_from = f"post_{from_phase}"
    if from_phase != "final" and current != expected_from:
        return False, [
            f"Phase mismatch: current={current}, expected={expected_from} for --from {from_phase}"
        ]

    if (from_phase, to_phase) not in _VALID_TRANSITIONS_SET:
        return False, [
            f"Invalid transition: --from {from_phase} --to {to_phase}"
        ]

    gate_fn = {
        "scope": lambda: _gate_scope(workdir, config),
        "search": lambda: _gate_search(workdir, config),
        "analysis": lambda: _gate_analysis(workdir),
        "review": lambda: _gate_review(workdir),
        "final": lambda: _gate_final(workdir),
    }.get(from_phase)

    errors = gate_fn() if gate_fn else []

    passed = len(errors) == 0
    if passed:
        write_phase_state(workdir, f"post_{to_phase}")
    return passed, errors


def get_gateway_results(workdir: Path) -> list[CheckResult]:
    return run_gateway(workdir, _get_goal_type(workdir))
