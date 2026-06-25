"""Phase transition gate logic with explicit state file detection."""

from __future__ import annotations

import json
import string
import sys
from pathlib import Path
from typing import cast

from .lib.utils import config_path, find_project_root, ensure_dir, read_json, tokenize_cjk_aware, write_json
from .gateway import run_all as run_gateway
from .gateway import run_report_checks
from .lib.source_router import get_default_min_sources, get_route, recommend_sources
from .lib.exceptions import ArtifactError
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_PIPELINE_STATE,
    ARTIFACT_REVIEW_REPORT,
    ARTIFACT_SCOPE,
    ARTIFACT_SEARCH_PLAN,
    _CHINESE_STOP_WORDS,
    _COVERAGE_THRESHOLD,
    _DEPTH_MIN_SOURCES_PER_DIRECTION,
    _ENGLISH_STOP_WORDS,
    _NON_EXACT_EVIDENCE_TYPES,
    _VALID_TRANSITIONS_SET,
)

_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS


def _is_stop_word(token: str) -> bool:
    """Return True if token should be filtered out."""
    if len(token) <= 1:
        return True
    if all(c in string.punctuation for c in token):
        return True
    if token in _STOP_WORDS:
        return True
    return False


def _tokenize_direction(direction: str) -> list[str]:
    """Tokenize a search direction using CJK-aware segmentation, filter stop words."""
    return [t for t in tokenize_cjk_aware(direction, lowercase=True) if not _is_stop_word(t)]


_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({
    "text", "source_urls", "evidence_type", "confidence",
    "precision", "metric_type", "source_metadata", "verified",
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


def _has_cjk_tokens(directions: list[str]) -> bool:
    """Return True if any direction contains CJK characters that produce whole-segment tokens."""
    for d in directions:
        for ch in d:
            if '\u4e00' <= ch <= '\u9fff':
                return True
    return False


def _check_tier_coverage(collected: list[dict], goal_type: str, config: dict | None) -> list[str]:
    """Check that collected sources cover each tier in the goal_type's route."""
    warnings: list[str] = []
    route = get_route(goal_type, config)
    route_path = route.get("path", [])
    optional_tiers = route.get("optional_tiers", [])
    if route_path and collected:
        covered_tiers = {entry.get("source_tier") for entry in collected if entry.get("source_tier")}
        missing_required = [t for t in route_path if t not in covered_tiers]
        if missing_required:
            warnings.append(
                f"tier_coverage WARN: route requires tiers {route_path}, "
                f"but tiers {missing_required} have no sources in collected.json"
            )
        missing_optional = [t for t in optional_tiers if t not in covered_tiers]
        if missing_optional:
            print(
                f"  [INFO] tier_coverage: optional tiers {missing_optional} have no sources (non-blocking)",
                file=sys.stderr,
            )
    return warnings


def _check_topic_coverage(
    collected: list[dict], scope: dict, needed: set[str],
) -> tuple[list[str], list[str]]:
    """Check topic coverage via covered_directions + token matching. Returns (blockers, warnings)."""
    blockers: list[str] = []
    warnings: list[str] = []
    covered = set()
    direction_counts: dict[str, int] = {d: 0 for d in needed}

    for entry in collected:
        cd = entry.get("covered_directions")
        if cd is None:
            continue
        if not isinstance(cd, list):
            warnings.append(
                f"covered_directions WARN: entry '{entry.get('title', '')}' "
                f"has non-list covered_directions, ignoring"
            )
            continue
        if len(cd) > 3:
            warnings.append(
                f"covered_directions WARN: entry '{entry.get('title', '')}' "
                f"has {len(cd)} directions (max 3), ignoring"
            )
            continue
        invalid = [d for d in cd if d not in needed]
        if invalid:
            warnings.append(
                f"covered_directions WARN: entry '{entry.get('title', '')}' "
                f"has invalid directions: {invalid}, ignoring"
            )
            continue
        for d in cd:
            covered.add(d)
            direction_counts[d] += 1

    for entry in collected:
        if entry.get("covered_directions") is not None:
            continue
        combined_text = (
            entry.get("title", "")
            + " " + entry.get("snippet", "")
            + " " + entry.get("fetched_content", "")[:500]
        ).lower()
        for direction in needed:
            tokens = _tokenize_direction(direction)
            if not tokens:
                continue
            matched = sum(1 for t in tokens if t in combined_text)
            if matched / len(tokens) >= _COVERAGE_THRESHOLD:
                covered.add(direction)
                direction_counts[direction] += 1

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


def _check_search_plan_inline(workdir: Path) -> list[str]:
    """Inline search_plan compliance check for _check_search_gate."""
    from .artifact_checks import check_search_plan_compliance
    result = check_search_plan_compliance(workdir)
    if result.passed:
        return []
    return [f"search_plan_compliance {result.level}: {result.message}"]


def _check_search_gate(workdir: Path, config: dict | None = None) -> tuple[list[str], list[str]]:
    """Returns (blockers, warnings). Blockers fail the gate, warnings are printed."""
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
    except ArtifactError as e:
        return [f"Cannot read collected.json: {e}"], []
    if not collected or len(collected) < 1:
        blockers.append("collected.json must have at least 1 entry")
    else:
        from .lib.schemas import validate_collected
        schema_errors = validate_collected(collected)
        if schema_errors:
            blockers.extend(f"collected.json {e.field}: {e.message}" for e in schema_errors)

    goal_type = _get_goal_type(workdir)
    min_src = get_default_min_sources(goal_type, config)
    if len(collected) < min_src:
        warnings.append(f"min_sources warning: {len(collected)} < {min_src} (configurable WARN)")

    warnings.extend(_check_tier_coverage(collected, goal_type, config))

    scope = read_json(workdir / ARTIFACT_SCOPE)
    needed = set(scope.get("search_directions", []))
    if needed:
        tc_blockers, tc_warnings = _check_topic_coverage(collected, scope, needed)
        blockers.extend(tc_blockers)
        warnings.extend(tc_warnings)

    from .gateway import check_fetched_content_depth
    fetched_result = check_fetched_content_depth(workdir)
    if not fetched_result.passed:
        if fetched_result.level == "BLOCKER":
            blockers.append(fetched_result.message)
        else:
            warnings.append(fetched_result.message)

    warnings.extend(_check_search_plan_inline(workdir))
    return blockers, warnings


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
            site_queries = [s.get("site_query", s.get("domain", "")) for s in tier_sources]
            is_chinese_tier = any(
                s.get("domain", "").endswith((".cn", ".com.cn")) or "cnki" in s.get("domain", "")
                for s in tier_sources
            )
            fetch_hint = ""
            tier_domains = [s.get("domain", "") for s in tier_sources]
            if any("arxiv.org" in d for d in tier_domains):
                fetch_hint = "MUST fetch full paper content (not just abstract) using exa_web_fetch_exa; search-result snippets are insufficient for Tier 1 academic sources"
            elif any("github.com" in d for d in tier_domains):
                fetch_hint = "Prefer fetching README, key source files, or documentation rather than just the repo listing"

            task = {
                "direction": direction,
                "tier": tier,
                "query_language": "zh" if is_chinese_tier else "en",
                "site_queries": site_queries,
                "min_sources": min_per_direction,
                "status": "pending",
                "collected_count": 0,
            }
            if fetch_hint:
                task["fetch_hint"] = fetch_hint
            tasks.append(task)

    write_json({"goal_type": goal_type, "depth": depth, "route": route_path, "tasks": tasks}, workdir / ARTIFACT_SEARCH_PLAN)


def _get_goal_type(workdir: Path) -> str:
    try:
        scope = read_json(workdir / ARTIFACT_SCOPE)
        return cast(str, scope.get("goal_type", "other"))
    except ArtifactError:
        return "other"


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
    blockers, warnings = _check_search_gate(workdir, config)
    for w in warnings:
        print(f"  [WARN] {w}", file=sys.stderr)
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
        from .lib.utils import normalize_url
        collected = read_json(workdir / ARTIFACT_COLLECTED)
        if isinstance(collected, list):
            collected_urls = {normalize_url(e.get("url", "")) for e in collected if isinstance(e, dict)}
    except ArtifactError:
        pass
    analysis = _sanitize_sections(analysis, collected_urls=collected_urls)
    write_json(analysis, workdir / ARTIFACT_ANALYSIS)
    from .lib.schemas import validate_analysis
    schema_errors = validate_analysis(analysis)
    if schema_errors:
        errors.extend(f"analysis.json {e.field}: {e.message}" for e in schema_errors)
    else:
        url_result = run_gateway(workdir, _get_goal_type(workdir))
        url_check = next((r for r in url_result if r.name == "url_traceability"), None)
        if url_check and not url_check.passed:
            errors.append(f"[BLOCKER] url_traceability: {url_check.message}")
    return errors


def _gate_review(workdir: Path) -> list[str]:
    gateway_results = run_gateway(workdir, _get_goal_type(workdir))
    blockers = [r for r in gateway_results if r.level == "BLOCKER" and not r.passed]
    return [f"[BLOCKER] {b.name}: {b.message}" for b in blockers]


def _gate_final(workdir: Path) -> list[str]:
    report_path = _find_report_path(workdir)
    if report_path is None:
        return ["No report file found in output directory for 3d verification"]
    report_results = run_report_checks(report_path)
    failed = [r for r in report_results if not r.passed]
    return [f"[{r.level}] {r.name}: {r.message}" for r in failed]


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
