"""Phase transition gate logic with explicit state file detection."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import cast

from .lib.utils import config_path, ensure_dir, read_json, write_json, build_collected_url_set
from .artifact_checks import CheckResult, run_all as run_gateway
from .report_checks import run_report_checks
from .search_gate import SearchGate
from .lib.exceptions import ArtifactError
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_PIPELINE_STATE,
    ARTIFACT_REVIEW_REPORT,
    ARTIFACT_SCOPE,
    _EVIDENCE_TYPE_ALIASES,
    _NON_EXACT_EVIDENCE_TYPES,
    _VALID_CONFIDENCE,
    _VALID_EVIDENCE_TYPES,
    _VALID_PRECISION,
    _VALID_TRANSITIONS_SET,
)

_SECTION_KEYS = frozenset({"id", "title", "content", "claims", "depth_strategy", "key_insights", "tensions"})
_CLAIM_KEYS = frozenset({
    "summary", "sources", "evidence_type", "confidence",
    "precision", "metric_type", "source_metadata", "verified",
    "source_verification",
})


def _repair_json_text(raw: str) -> str:
    """Attempt to fix unescaped double quotes inside JSON string values.

    When an LLM subagent writes Markdown content containing ``"quoted text"``
    inside a JSON string, the resulting file is invalid JSON because the inner
    quotes are not escaped.  This function finds unescaped ``"`` that appear
    *inside* string values and escapes them as ``\\"``.

    Strategy: iterate character-by-character, tracking whether we are inside a
    JSON string and whether the current char is escaped.  When we encounter an
    unescaped ``"`` that is *not* a valid string delimiter (i.e. it is not
    followed by a structural character like ``: , ] }`` and not preceded by one
    like ``: , [ {``), we escape it.
    """
    result: list[str] = []
    in_string = False
    i = 0
    while i < len(raw):
        ch = raw[i]
        if not in_string:
            result.append(ch)
            if ch == '"':
                in_string = True
            i += 1
            continue
        # We are inside a JSON string
        if ch == '\\' and i + 1 < len(raw):
            result.append(ch)
            result.append(raw[i + 1])
            i += 2
            continue
        if ch == '"':
            # Is this the closing quote of the string, or a rogue unescaped quote?
            # A closing quote is followed by a structural char or EOF
            rest = raw[i + 1:].lstrip()
            if not rest or rest[0] in ':,]}':
                result.append(ch)
                in_string = False
                i += 1
                continue
            # This looks like a rogue quote inside the string — escape it
            result.append('\\"')
            i += 1
            continue
        result.append(ch)
        i += 1
    return ''.join(result)


def _read_json_with_repair(path: Path) -> tuple[dict | list | None, str | None]:
    """Read JSON, attempting quote repair on JSONDecodeError.

    Returns (data, error_message).  On success, error_message is None.
    On failure, data is None and error_message describes the problem.
    """
    try:
        data = read_json(path)
        return data, None
    except ArtifactError as e:
        if "Invalid JSON" not in str(e):
            return None, f"Cannot read {path.name}: {e}"
        raw_text = path.read_text(encoding="utf-8")
        repaired = _repair_json_text(raw_text)
        try:
            data = json.loads(repaired)
            return data, None
        except json.JSONDecodeError as e2:
            return None, f"Cannot read {path.name}: Invalid JSON even after repair: {e2}"


def _sanitize_sections(analysis: dict, collected_urls: set[str] | None = None) -> dict:
    """Clean subagent output before schema validation."""
    result = dict(analysis)
    sections = result.get("sections")
    if not isinstance(sections, list):
        return result

    cleaned_sections = []
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            cleaned_sections.append(section)
            continue
        sec = dict(section)
        if "section_id" in sec and "id" not in sec:
            sec["id"] = sec.pop("section_id")
        if "claims" not in sec:
            sec["claims"] = []
        # Structural safeguard: key_insights / tensions must be lists of dicts
        # ({summary, sources}). A string array is a schema violation — raise a
        # precise, actionable error instead of silently poisoning the analysis.
        for field in ("key_insights", "tensions"):
            items = sec.get(field)
            if isinstance(items, list):
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        raise ValueError(
                            f"sections[{i}].{field}[{j}] is a {type(item).__name__}, "
                            f"not an object. Expected {{summary, sources}}. "
                            f"Wrap each item as {{\"summary\": <text>, \"sources\": [<url>]}}."
                        )
        claims = sec.get("claims")
        if isinstance(claims, list):
            cleaned_claims = []
            for claim in claims:
                if not isinstance(claim, dict):
                    cleaned_claims.append(claim)
                    continue
                cl = dict(claim)
                if "text" in cl and "summary" not in cl:
                    cl["summary"] = cl.pop("text")
                if "source_urls" in cl and "sources" not in cl:
                    cl["sources"] = cl.pop("source_urls")
                # Auto-fix invalid evidence_type: try safe alias first, then
                # downgrade to qualitative_trend (never escalate to official/independent).
                if "evidence_type" in cl:
                    et = cl["evidence_type"]
                    if et not in _VALID_EVIDENCE_TYPES:
                        cl["evidence_type"] = _EVIDENCE_TYPE_ALIASES.get(et, "qualitative_trend")
                # Auto-fix invalid confidence: downgrade to medium
                if "confidence" in cl and cl["confidence"] not in _VALID_CONFIDENCE:
                    cl["confidence"] = "medium"
                # Auto-fix invalid precision: downgrade to qualitative
                if "precision" in cl and cl["precision"] not in _VALID_PRECISION:
                    cl["precision"] = "qualitative"
                # Auto-fix precision inflation: downgrade exact -> range for non-official evidence
                # Must run AFTER evidence_type sanitization so it sees the corrected type
                if (
                    cl.get("precision") == "exact"
                    and cl.get("evidence_type") in _NON_EXACT_EVIDENCE_TYPES
                ):
                    cl["precision"] = "range"
                # Auto-fix URL traceability: remove sources not in collected.json
                if collected_urls is not None and "sources" in cl:
                    valid = [u for u in cl["sources"] if u in collected_urls]
                    if valid:
                        cl["sources"] = valid
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

    Returns one of: pre_scope, post_scope, post_search, post_analysis, post_review, post_final
    """
    if not workdir.exists():
        return "pre_scope"
    state_path = workdir / ARTIFACT_PIPELINE_STATE
    if state_path.exists():
        try:
            state = read_json(state_path)
            phase = state.get("current_phase", "")
            if phase in ("pre_scope", "post_scope", "post_search", "post_analysis", "post_review", "post_final"):
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


def _find_report_path(workdir: Path) -> Path | None:
    """Find the latest .md report file in the configured output directory."""
    project_root = workdir.parent
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


def _format_check_result(r: CheckResult, prefix: str = "  ") -> list[str]:
    """Format a failed CheckResult as output lines, including repair_hints."""
    lines = [f"{prefix}{r.message}"]
    for hint in r.repair_hints:
        lines.append(f"{prefix}→ {hint}")
    return lines


def _fill_scope_defaults(workdir: Path) -> None:
    """Fill optional depth/audience defaults in scope.json if missing."""
    scope_path = workdir / ARTIFACT_SCOPE
    try:
        scope = read_json(scope_path)
    except ArtifactError:
        return
    changed = False
    if "depth" not in scope:
        scope["depth"] = "standard"
        changed = True
    if "audience" not in scope:
        scope["audience"] = "general"
        changed = True
    if changed:
        write_json(scope, scope_path)


def _gate_scope(workdir: Path, config: dict | None) -> list[str]:
    _fill_scope_defaults(workdir)
    errors = _check_scope_schema(workdir)
    return errors


def _gate_search(workdir: Path, config: dict | None) -> list[str]:
    results = SearchGate(workdir, config).check()
    blockers = []
    for r in results:
        if r.passed:
            continue
        if r.level == "BLOCKER":
            blockers.append(r.message)
            for hint in r.repair_hints:
                print(f"  → {hint}", file=sys.stderr)
        else:
            print(f"  [WARN] {r.message}", file=sys.stderr)
            for hint in r.repair_hints:
                print(f"  → {hint}", file=sys.stderr)
    return blockers


def _gate_analysis(workdir: Path) -> list[str]:
    errors: list[str] = []
    analysis, err = _read_json_with_repair(workdir / ARTIFACT_ANALYSIS)
    if err is not None:
        errors.append(err)
        return errors
    collected_urls: set[str] | None = None
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
        if isinstance(collected, list):
            collected_urls = build_collected_url_set(collected)
    except ArtifactError:
        pass
    try:
        analysis = _sanitize_sections(analysis, collected_urls=collected_urls)
    except ValueError as e:
        errors.append(f"[BLOCKER] analysis_schema: {e}")
        return errors
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
            "source_verification_check", "subagent_delegation",
        }
        blockers = [
            r for r in gateway_results
            if r.level == "BLOCKER" and not r.passed and r.name in analysis_check_names
        ]
        for b in blockers:
            errors.append(f"[BLOCKER] {b.name}: {b.message}")
            for hint in b.repair_hints:
                errors.append(f"  → {hint}")
        for r in gateway_results:
            if r.level == "INFO":
                print(f"  [INFO] {r.message}", file=sys.stderr)
    from .claim_validator import apply_source_verification
    apply_source_verification(workdir)
    return errors


def _check_review_report_exists(workdir: Path) -> CheckResult:
    """Check that review_report.md exists and is non-empty.

    Review is mandatory (ADR 0028, minimum: degraded).
    Missing review_report.md is BLOCKER — the agent must have
    auto-started a review subagent and produced a review report.
    """
    report_path = workdir / ARTIFACT_REVIEW_REPORT
    if not report_path.exists():
        return CheckResult("review_report_exists", "BLOCKER", False, "review_report.md does not exist — review subagent may have failed silently")
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError:
        return CheckResult("review_report_exists", "BLOCKER", False, "Cannot read review_report.md")
    if not content.strip():
        return CheckResult("review_report_exists", "BLOCKER", False, "review_report.md is empty — review subagent may have failed silently")
    return CheckResult("review_report_exists", "BLOCKER", True)


def _gate_review(workdir: Path, to_phase: str = "review") -> list[str]:
    """Review gate: blocks on BLOCKER-level failures.

    - analysis→review / review→review: just passes through. Review is an
      agent-level concern (SKILL.md instructs the agent to auto-start a
      review subagent). Gateway checks are not re-run on self-loops.
    - review→final: runs advisory gateway checks + BLOCKER on missing
      review_report.md.
    """
    errors: list[str] = []
    if to_phase == "final":
        gateway_results = run_gateway(workdir, _get_goal_type(workdir))
        for r in gateway_results:
            if not r.passed:
                print(f"  [ADVISORY] {r.name}: {r.message}", file=sys.stderr)
                for hint in r.repair_hints:
                    print(f"  → {hint}", file=sys.stderr)
        rr_check = _check_review_report_exists(workdir)
        if not rr_check.passed:
            if rr_check.level == "BLOCKER":
                errors.append(f"[BLOCKER] {rr_check.name}: {rr_check.message}")
                for hint in rr_check.repair_hints:
                    errors.append(f"  → {hint}")
            else:
                print(f"  [WARN] {rr_check.name}: {rr_check.message}", file=sys.stderr)
    return errors


def _gate_final(workdir: Path) -> list[str]:
    report_path = _find_report_path(workdir)
    if report_path is None:
        return ["No report file found in output directory for 3d verification"]
    report_results = run_report_checks(report_path)
    blockers = [r for r in report_results if r.level == "BLOCKER" and not r.passed]
    errors: list[str] = []
    for b in blockers:
        errors.append(f"[BLOCKER] {b.name}: {b.message}")
        for hint in b.repair_hints:
            errors.append(f"  → {hint}")
    return errors


def proceeds(
    workdir: Path, from_phase: str, to_phase: str, config: dict | None = None
) -> tuple[bool, list[str]]:
    """Run gate for the given transition. Returns (passed, error_messages)."""
    ensure_dir(workdir)
    current = detect_current_phase(workdir)
    expected_from = f"post_{from_phase}"
    if current != expected_from:
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
        "review": lambda: _gate_review(workdir, to_phase),
        "final": lambda: _gate_final(workdir),
    }.get(from_phase)

    # Retry limits (SKILL.md-level instruction, not auto-loop):
    #   gate2 (search→analysis): max 3 retries;
    #     after limit, print "Search gate retry limit (3) reached. Pausing for human review."
    #   gate3 (analysis→review): max 2 retries;
    #     after limit, print "Analysis gate retry limit (2) reached. Pausing for human review."

    errors = gate_fn() if gate_fn else []

    passed = len(errors) == 0
    if passed:
        write_phase_state(workdir, f"post_{to_phase}")
    return passed, errors


def get_gateway_results(workdir: Path) -> list[CheckResult]:
    return run_gateway(workdir, _get_goal_type(workdir))
