"""Phase transition gate logic with explicit state file detection."""

from __future__ import annotations

import json
import re
import string
import sys
from pathlib import Path
from typing import cast

from .cli import _find_project_root
from .gateway import CheckResult
from .gateway import run_all as run_gateway
from .gateway import run_report_checks
from .lib.source_router import get_default_min_sources, get_route, recommend_sources
from .lib.exceptions import ArtifactError
from .lib.utils import ensure_dir, read_json, write_json


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


_SECTION_KEYS = frozenset({"id", "title", "content", "claims"})
_CLAIM_KEYS = frozenset({
    "text", "source_urls", "evidence_type", "confidence",
    "precision", "metric_type", "source_metadata", "verified",
})


_NON_EXACT_EVIDENCE_TYPES = frozenset({"third_party_estimate", "qualitative_trend", "expert_opinion"})


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


def _write_phase_state(workdir: Path, phase: str) -> None:
    state_path = workdir / "pipeline_state.json"
    try:
        write_json({"current_phase": phase}, state_path)
    except OSError:
        pass


def detect_current_phase(workdir: Path) -> str:
    """Return current phase string based on state file or artifact presence.

    Returns one of: pre_scope, post_scope, post_search, post_analysis, post_review
    """
    if not workdir.exists():
        return "pre_scope"
    state_path = workdir / "pipeline_state.json"
    if state_path.exists():
        try:
            state = read_json(state_path)
            phase = state.get("current_phase", "")
            if phase in ("pre_scope", "post_scope", "post_search", "post_analysis", "post_review"):
                return phase
        except Exception:
            pass
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


_VALID_TRANSITIONS_SET = {
    ("scope", "search"),
    ("search", "analysis"),
    ("analysis", "review"),
    ("review", "final"),
    ("review", "review"),
    ("final", "cleanup"),
}


def _check_scope_schema(workdir: Path) -> list[str]:
    try:
        scope = read_json(workdir / "scope.json")
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
    else:
        from .lib.schemas import validate_collected
        schema_errors = validate_collected(collected)
        if schema_errors:
            blockers.extend(f"collected.json {e.field}: {e.message}" for e in schema_errors)

    goal_type = _get_goal_type(workdir)
    min_src = get_default_min_sources(goal_type, config)
    if len(collected) < min_src:
        warnings.append(f"min_sources warning: {len(collected)} < {min_src} (configurable WARN)")

    # Tier coverage check (ADR 0007): verify collected sources cover each tier in the route
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

    scope = read_json(workdir / "scope.json")
    needed = set(scope.get("search_directions", []))
    if needed:
        covered = set()
        direction_counts: dict[str, int] = {d: 0 for d in needed}

        # First pass: explicit covered_directions from collected entries (ADR 0017)
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

        # Second pass: token matching for entries without covered_directions
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
    # fetched_content depth check (per-tier minimums)
    _TIER_MINS = {1: 1000, 2: 800, 3: 600, 4: 400}
    if collected:
        empty_count = sum(1 for e in collected if not e.get("fetched_content", "") and not e.get("fetch_failed", False))
        stub_count = sum(
            1 for e in collected
            if e.get("fetched_content", "") and not e.get("fetch_failed", False)
            and len(e.get("fetched_content", "")) < _TIER_MINS.get(e.get("source_tier", 0), 200)
        )
        fetch_failed_count = sum(1 for e in collected if e.get("fetch_failed", False))
        total = len(collected)
        checked = total - fetch_failed_count
        problem_count = empty_count + stub_count
        ratio = problem_count / checked if checked > 0 else 0
        if empty_count > 0:
            warnings.append(
                f"fetched_content_depth WARN: {empty_count}/{total} entries have no fetched_content"
            )
        if stub_count > 0:
            warnings.append(
                f"fetched_content_depth WARN: {stub_count}/{total} entries have stub fetched_content (below per-tier minimum)"
            )
        if fetch_failed_count > 0:
            warnings.append(
                f"fetched_content_depth WARN: {fetch_failed_count}/{total} entries have fetch_failed=true (exempt)"
            )
        if ratio > 0.30:
            blockers.append(
                f"fetched_content_depth BLOCKER: {problem_count}/{checked} entries ({ratio:.0%}) have missing or stub fetched_content — re-fetch with full content before proceeding"
            )
    # search_plan compliance check
    plan_path = workdir / "search_plan.json"
    if plan_path.exists():
        try:
            plan = read_json(plan_path)
            tasks = plan.get("tasks", [])
            if tasks:
                pending = sum(1 for t in tasks if t.get("status") == "pending")
                completed = sum(1 for t in tasks if t.get("status") == "completed")
                if pending and not completed:
                    warnings.append(
                        f"search_plan_compliance WARN: 0/{len(tasks)} tasks completed, {pending} pending — search_plan was not followed"
                    )
                dirs_in_plan = set(t.get("direction", "") for t in tasks)
                dirs_completed = set(t.get("direction", "") for t in tasks if t.get("status") == "completed")
                dirs_missing = dirs_in_plan - dirs_completed
                if dirs_missing:
                    warnings.append(
                        f"search_plan_compliance WARN: directions without completed tasks: {', '.join(sorted(dirs_missing))}"
                    )
        except ArtifactError:
            pass
    return blockers, warnings



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

    write_json({"goal_type": goal_type, "depth": depth, "route": route_path, "tasks": tasks}, workdir / "search_plan.json")


def _get_goal_type(workdir: Path) -> str:
    try:
        scope = read_json(workdir / "scope.json")
        return cast(str, scope.get("goal_type", "other"))
    except ArtifactError:
        return "other"


def _find_report_path(workdir: Path) -> Path | None:
    """Find the latest .md report file in the configured output directory."""
    from .cli import _find_project_root

    project_root = _find_project_root()
    config_path = Path(__file__).parent.parent / "config.json"
    output_dir = project_root / "./reports/"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            output_dir = project_root / config.get("output_dir", "./reports/")
        except (OSError, json.JSONDecodeError):
            pass
    if not output_dir.exists():
        return None
    md_files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return md_files[0] if md_files else None


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

    if (from_phase, to_phase) not in _VALID_TRANSITIONS_SET:
        return False, [
            f"Invalid transition: --from {from_phase} --to {to_phase}"
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
        except ArtifactError as e:
            errors.append(f"Cannot read analysis.json: {e}")
        else:
            # Load collected URLs for auto-fix (URL filtering + precision fix)
            collected_urls: set[str] | None = None
            try:
                from .lib.utils import normalize_url
                collected = read_json(workdir / "collected.json")
                if isinstance(collected, list):
                    collected_urls = {normalize_url(e.get("url", "")) for e in collected if isinstance(e, dict)}
            except ArtifactError:
                pass
            analysis = _sanitize_sections(analysis, collected_urls=collected_urls)
            write_json(analysis, workdir / "analysis.json")
            from .lib.schemas import validate_analysis
            schema_errors = validate_analysis(analysis)
            if schema_errors:
                errors.extend(f"analysis.json {e.field}: {e.message}" for e in schema_errors)
            else:
                url_result = run_gateway(workdir, _get_goal_type(workdir))
                url_check = next((r for r in url_result if r.name == "url_traceability"), None)
                if url_check and not url_check.passed:
                    errors.append(f"[BLOCKER] url_traceability: {url_check.message}")

    elif from_phase == "review":
        gateway_results = run_gateway(workdir, _get_goal_type(workdir))
        blockers = [r for r in gateway_results if r.level == "BLOCKER" and not r.passed]
        for b in blockers:
            errors.append(f"[BLOCKER] {b.name}: {b.message}")

    elif from_phase == "final":
        report_path = _find_report_path(workdir)
        if report_path is None:
            errors.append("No report file found in output directory for 3d verification")
        else:
            report_results = run_report_checks(report_path)
            failed = [r for r in report_results if not r.passed]
            for r in failed:
                errors.append(f"[{r.level}] {r.name}: {r.message}")

    passed = len(errors) == 0
    if passed:
        _write_phase_state(workdir, f"post_{to_phase}")
    return passed, errors


def get_gateway_results(workdir: Path) -> list[CheckResult]:
    return run_gateway(workdir, _get_goal_type(workdir))
