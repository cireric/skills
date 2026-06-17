"""Phase transition gate logic with implicit state detection."""

from __future__ import annotations

import re
import string
import sys
from pathlib import Path
from typing import cast

from .cli import _find_project_root
from .gateway import CheckResult
from .gateway import run_all as run_gateway
from .lib.source_router import get_default_min_sources, get_route, recommend_sources
from .lib.exceptions import ArtifactError
from .lib.utils import ensure_dir, normalize_url, read_json, write_json


from .lib.constants import _CHINESE_STOP_WORDS, _ENGLISH_STOP_WORDS

_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS

_DEPTH_MIN_SOURCES_PER_DIRECTION = {"quick": 1, "standard": 3, "deep": 5}


def _is_stop_word(token: str) -> bool:
    """Return True if token should be filtered out."""
    if len(token) <= 1:
        return True
    if all(c in string.punctuation for c in token):
        return True
    if token in _STOP_WORDS:
        return True
    return False


_COVERAGE_THRESHOLD = 0.5


def _tokenize_direction(direction: str) -> list[str]:
    """Tokenize a search direction using simple split + CJK character segmentation, filter stop words."""
    text = direction.lower()
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if '\u4e00' <= ch <= '\u9fff':
            j = i + 1
            while j < len(text) and '\u4e00' <= text[j] <= '\u9fff':
                j += 1
            tokens.append(text[i:j])
            i = j
        elif ch.isspace() or ch in string.punctuation:
            i += 1
        else:
            j = i + 1
            while j < len(text) and not text[j].isspace() and text[j] not in string.punctuation and not ('\u4e00' <= text[j] <= '\u9fff'):
                j += 1
            tokens.append(text[i:j])
            i = j
    return [t for t in tokens if not _is_stop_word(t)]


def detect_current_phase(workdir: Path) -> str:
    """Return current phase string based on which artifacts exist.

    Returns one of: pre_scope, post_scope, post_search, post_analysis, post_review
    """
    if not workdir.exists():
        return "pre_scope"
    scope_present = (workdir / "scope.json").exists()
    collected_present = (workdir / "collected.json").exists()
    analysis_present = (workdir / "analysis.json").exists()
    review_present = (workdir / "review_report.md").exists()

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


_VALID_TRANSITIONS = {
    "scope": "search",
    "search": "analysis",
    "analysis": "review",
    "review": "final",
    "final": "cleanup",
}


def _check_scope_schema(workdir: Path) -> list[str]:
    errors = []
    try:
        scope = read_json(workdir / "scope.json")
    except ArtifactError as e:
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


def _has_cjk_tokens(directions: list[str]) -> bool:
    """Return True if any direction contains CJK characters that produce whole-segment tokens."""
    for d in directions:
        for ch in d:
            if '\u4e00' <= ch <= '\u9fff':
                return True
    return False


def _check_search_gate(workdir: Path, config: dict | None = None) -> tuple[list[str], list[str]]:
    """Returns (blockers, warnings). Blockers fail the gate, warnings are printed."""
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        collected = read_json(workdir / "collected.json")
    except ArtifactError as e:
        return [f"Cannot read collected.json: {e}"], []
    if not collected or len(collected) < 1:
        blockers.append("collected.json must have at least 1 entry")

    goal_type = _get_goal_type(workdir)
    min_src = get_default_min_sources(goal_type, config)
    if len(collected) < min_src:
        warnings.append(f"min_sources warning: {len(collected)} < {min_src} (configurable WARN)")

    # Tier coverage check (ADR 0007): verify collected sources cover each tier in the route
    route = get_route(goal_type, config)
    route_path = route.get("path", [])
    if route_path and collected:
        covered_tiers = {entry.get("source_tier") for entry in collected if entry.get("source_tier")}
        missing_tiers = [t for t in route_path if t not in covered_tiers]
        if missing_tiers:
            warnings.append(
                f"tier_coverage WARN: route requires tiers {route_path}, "
                f"but tiers {missing_tiers} have no sources in collected.json"
            )

    scope = read_json(workdir / "scope.json")
    needed = set(scope.get("search_directions", []))
    if needed:
        covered = set()
        direction_counts: dict[str, int] = {d: 0 for d in needed}
        for entry in collected:
            combined_text = (entry.get("title", "") + " " + entry.get("snippet", "")).lower()
            for direction in needed:
                tokens = _tokenize_direction(direction)
                if not tokens:
                    continue
                matched = sum(1 for t in tokens if t in combined_text)
                if matched / len(tokens) >= _COVERAGE_THRESHOLD:
                    covered.add(direction)
                    direction_counts[direction] += 1

        # Per-direction min sources check (ADR 0010)
        depth = scope.get("depth", "standard")
        min_per_direction = _DEPTH_MIN_SOURCES_PER_DIRECTION.get(depth, 3)
        for direction in needed:
            count = direction_counts.get(direction, 0)
            if count < min_per_direction:
                warnings.append(
                    f"per_direction_min_sources WARN: direction '{direction}' "
                    f"has {count} sources, depth='{depth}' requires {min_per_direction}"
                )

        missing = needed - covered
        if missing:
            cjk_heavy = _has_cjk_tokens(list(needed))
            if cjk_heavy:
                warnings.append(
                    f"topic_coverage WARN (CJK directions): search directions not covered: {', '.join(missing)}"
                )
            else:
                blockers.append(
                    f"topic_coverage BLOCKER: search directions not covered: {', '.join(missing)}"
                )
            for d in missing:
                tokens = _tokenize_direction(d)
                if tokens:
                    suggestions = [t for t in tokens if not _is_stop_word(t)]
                    if suggestions:
                        warnings.append(
                            f"  Suggestion: try searching for '{d}' with keywords: {', '.join(suggestions[:5])}"
                        )
    return blockers, warnings


def _check_url_traceability(analysis: dict, collected: list[dict]) -> list[str]:
    """Check that all claim source_urls exist in collected.json. Returns error list."""
    collected_urls = {normalize_url(item["url"]) for item in collected if "url" in item}
    untraceable: list[str] = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            for url in claim.get("source_urls", []):
                if normalize_url(url) not in collected_urls:
                    untraceable.append(
                        f"sections.{sec_id}.claims[{ci}]: source_url not in collected.json: {url}"
                    )
    if untraceable:
        prefix = f"url_traceability BLOCKER: {len(untraceable)} claim URLs not in collected.json"
        return [prefix] + [f"  {u}" for u in untraceable[:10]]
    return []


def _generate_search_plan(workdir: Path, config: dict | None = None) -> None:
    """Generate search_plan.json based on route × search_directions (ADR 0011)."""
    scope = read_json(workdir / "scope.json")
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
            site_queries = [s.get("site_query", s.get("domain", "")) for s in tier_sources]
            is_chinese_tier = any(
                s.get("domain", "").endswith((".cn", ".com.cn")) or "cnki" in s.get("domain", "")
                for s in tier_sources
            )
            tasks.append({
                "direction": direction,
                "tier": tier,
                "query_language": "zh" if is_chinese_tier else "en",
                "site_queries": site_queries,
                "min_sources": min_per_direction,
            })

    write_json({"goal_type": goal_type, "depth": depth, "route": route_path, "tasks": tasks}, workdir / "search_plan.json")


def _get_goal_type(workdir: Path) -> str:
    try:
        scope = read_json(workdir / "scope.json")
        return cast(str, scope.get("goal_type", "other"))
    except ArtifactError:
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
        if not errors:
            _generate_search_plan(workdir, config)

    elif from_phase == "search":
        search_blockers, search_warnings = _check_search_gate(workdir, config)
        errors.extend(search_blockers)
        for w in search_warnings:
            print(f"  [WARN] {w}", file=sys.stderr)

    elif from_phase == "analysis":
        try:
            analysis = read_json(workdir / "analysis.json")
            collected = read_json(workdir / "collected.json") or []
        except ArtifactError as e:
            errors.append(f"Cannot read artifacts: {e}")
        else:
            if "topic" not in analysis or "goal_type" not in analysis:
                errors.append("analysis.json missing topic or goal_type")
            if not analysis.get("sections"):
                errors.append("analysis.json sections is empty")
            url_errors = _check_url_traceability(analysis, collected)
            errors.extend(url_errors)

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
