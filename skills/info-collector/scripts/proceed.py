"""Phase transition gate logic with explicit state file detection."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import cast

from .lib.utils import config_path, ensure_dir, read_json, write_json, build_collected_url_set, normalize_url
from .artifact_checks import CheckResult, run_all as run_gateway
from .report_checks import run_report_checks
from .search_gate import SearchGate
from .lib.exceptions import ArtifactError
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_FIX_LIST,
    ARTIFACT_FIX_REPORT,
    ARTIFACT_LIGHTWEIGHT_REVIEW,
    ARTIFACT_PIPELINE_STATE,
    ARTIFACT_REVIEW_REPORT,
    ARTIFACT_SCOPE,
    _EVIDENCE_TYPE_ALIASES,
    _NON_EXACT_EVIDENCE_TYPES,
    _REQUIRED_SECTION_IDS,
    _SOURCE_TYPE_ALIASES,
    _VALID_CONFIDENCE,
    _VALID_EVIDENCE_TYPES,
    _VALID_PRECISION,
    _VALID_SOURCE_TYPES,
    _VALID_TRANSITIONS_SET,
)

_SECTION_KEYS = frozenset({"id", "title", "content", "claims", "depth_strategy", "key_insights", "tensions", "order"})
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


def _preprocess_cjk_quotes(raw: str) -> str:
    """Replace CJK full-width double quotes with ASCII single quotes.

    CJK full-width quotes \u201c\u201d inside JSON string values can break JSON
    parsing when they contain unescaped ASCII double quotes. Replacing them with
    ASCII single quotes (0x27) is a deterministic defense that does not rely on
    prompt constraints. ADR 0053.
    """
    return raw.replace("\u201c", "'").replace("\u201d", "'")


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
        raw_text = _preprocess_cjk_quotes(raw_text)
        repaired = _repair_json_text(raw_text)
        try:
            data = json.loads(repaired)
            return data, None
        except json.JSONDecodeError as e2:
            return None, f"Cannot read {path.name}: Invalid JSON even after repair: {e2}"


def _validate_section_files(workdir: Path) -> list[str]:
    """Validate section files against trust boundary (ADR 0053).

    Reads analysis_section_*.json files and validates each against
    the trust boundary (structural + semantic). Returns error messages
    for any failures.
    """
    from .trust_boundary import validate_section_output
    from .lib.utils import build_collected_url_set

    collected_urls: set[str] = set()
    collected_path = workdir / ARTIFACT_COLLECTED
    if collected_path.exists():
        try:
            collected = read_json(collected_path)
            if isinstance(collected, list):
                collected_urls = build_collected_url_set(collected)
        except ArtifactError:
            pass

    errors: list[str] = []
    section_files = sorted(workdir.glob("analysis_section_*.json"))
    for sf in section_files:
        if is_section_incomplete(sf):
            continue
        raw = sf.read_text(encoding="utf-8")
        raw = _preprocess_cjk_quotes(raw)
        result = validate_section_output(raw, collected_urls)
        if not result.passed:
            for err in result.errors:
                errors.append(
                    f"[BLOCKER] trust_boundary({sf.name}): {err.path} — {err.error}: "
                    f"expected {err.expected}, got {err.actual}"
                )
    return errors


def mark_section_incomplete(section_path: Path) -> None:
    """Mark a section file as incomplete (ADR 0053).

    Called when trust boundary validation fails 3 times and the
    orchestrator's manual rewrite also fails. The section's content
    remains but is flagged as unreliable.
    """
    try:
        data = json.loads(section_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, dict):
        return
    data["status"] = "incomplete"
    section_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_section_incomplete(section_path: Path) -> bool:
    """Check whether a section file is marked incomplete (ADR 0053)."""
    try:
        data = json.loads(section_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(data, dict) and data.get("status") == "incomplete"


_MERGE_COMPLETED_KEY = "_merge_completed"


def _sort_sections(sections: list[dict], goal_type: str = "") -> list[dict]:
    """Sort sections into reading order.

    For quantitative goal_types (tech_selection, etc.), sections are ordered
    by _REQUIRED_SECTION_IDS position, with `order` field as override.
    For exploratory goal_types (panoramic, exploratory, etc.), ordering is
    entirely driven by the agent-assigned `order` field; sections without
    `order` fall back to id-lexicographic.
    """
    id_order = _REQUIRED_SECTION_IDS.get(goal_type, [])
    has_canonical_order = bool(id_order)

    def _sort_key(sec: dict) -> tuple:
        has_order = "order" in sec and isinstance(sec["order"], int)
        sid = sec.get("id", "")
        if has_canonical_order:
            id_pos = {s: i for i, s in enumerate(id_order)}
            if has_order:
                return (0, sec["order"], sid)
            pos = id_pos.get(sid, len(id_order))
            return (1, pos, sid)
        else:
            if has_order:
                return (0, sec["order"], sid)
            return (1, 0, sid)

    return sorted(sections, key=_sort_key)


def _merge_section_files(workdir: Path, topic: str = "", goal_type: str = "") -> dict | None:
    """Merge analysis_section_*.json into analysis.json (ADR 0054).

    JSON merge only — never rewrite or rephrase section content.
    Idempotent: if analysis.json already exists and was produced by
    this function, returns the existing analysis without re-merging.
    Sections are ordered by: explicit `order` field > _REQUIRED_SECTION_IDS
    position (quantitative goal_types only) > id-lexicographic (fallback).
    """
    section_files = sorted(workdir.glob("analysis_section_*.json"))
    if not section_files:
        return None

    analysis_path = workdir / ARTIFACT_ANALYSIS
    if analysis_path.exists():
        try:
            existing = read_json(analysis_path)
            if isinstance(existing, dict) and existing.get(_MERGE_COMPLETED_KEY) is True:
                return existing
        except (ArtifactError, json.JSONDecodeError):
            pass

    sections = []
    for sf in section_files:
        raw = sf.read_text(encoding="utf-8")
        raw = _preprocess_cjk_quotes(raw)
        try:
            sec = json.loads(raw)
            if isinstance(sec, dict):
                sections.append(sec)
        except json.JSONDecodeError:
            continue

    if not sections:
        return None

    sections = _sort_sections(sections, goal_type)

    analysis = {
        "topic": topic,
        "goal_type": goal_type,
        "sections": sections,
        _MERGE_COMPLETED_KEY: True,
    }
    write_json(analysis, analysis_path)
    return analysis


_REF_MARKER_RE = __import__("re").compile(r"\{\{ref:(.*?)\}\}")


def _check_url_consistency(analysis: dict, collected_urls: set[str]) -> list[str]:
    """Check URL consistency after merge (ADR 0054).

    Scans all {{ref:URL}} markers and sources URLs in analysis.json,
    compares against collected_urls. Returns WARN messages for mismatches
    with "did you mean?" suggestions.
    """
    from .artifact_checks import _suggest_similar_urls

    warnings: list[str] = []
    for sec in analysis.get("sections", []):
        content = sec.get("content", "")
        for url in _REF_MARKER_RE.findall(content):
            norm = normalize_url(url)
            if norm not in collected_urls:
                suggestions = _suggest_similar_urls(url, collected_urls)
                hint = f" (did you mean: {', '.join(suggestions)}?)" if suggestions else ""
                warnings.append(f"[WARN] URL not in collected.json: {url}{hint}")

        for field_name in ("key_insights", "tensions", "claims"):
            items = sec.get(field_name)
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                for url in item.get("sources", []):
                    norm = normalize_url(url)
                    if norm not in collected_urls:
                        suggestions = _suggest_similar_urls(url, collected_urls)
                        hint = f" (did you mean: {', '.join(suggestions)}?)" if suggestions else ""
                        warnings.append(f"[WARN] URL not in collected.json: {url}{hint}")
    return warnings


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
                # Auto-fix invalid source_type in source_metadata: try alias, then downgrade to survey
                meta = cl.get("source_metadata")
                if isinstance(meta, dict) and "source_type" in meta:
                    st = meta["source_type"]
                    if st not in _VALID_SOURCE_TYPES:
                        meta["source_type"] = _SOURCE_TYPE_ALIASES.get(st, "survey")
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
    tb_errors = _validate_section_files(workdir)
    if tb_errors:
        return tb_errors

    section_files = list(workdir.glob("analysis_section_*.json"))
    if section_files and not (workdir / ARTIFACT_ANALYSIS).exists():
        scope = {}
        try:
            scope = read_json(workdir / ARTIFACT_SCOPE)
        except ArtifactError:
            pass
        merged = _merge_section_files(
            workdir,
            topic=scope.get("topic", ""),
            goal_type=scope.get("goal_type", "other"),
        )
        if merged is not None:
            collected_urls_for_check: set[str] = set()
            try:
                collected = read_json(workdir / ARTIFACT_COLLECTED)
                if isinstance(collected, list):
                    collected_urls_for_check = build_collected_url_set(collected)
            except ArtifactError:
                pass
            url_warnings = _check_url_consistency(merged, collected_urls_for_check)
            for w in url_warnings:
                print(f"  {w}", file=sys.stderr)

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


def check_fix_report(workdir: Path) -> dict | None:
    """Parse fix_report.json and count BLOCKER/WARN fix status (ADR 0055).

    Returns dict with blocker_fixed, blocker_skipped, warn_skipped counts,
    or None if fix_report.json does not exist.
    """
    fix_report_path = workdir / ARTIFACT_FIX_REPORT
    if not fix_report_path.exists():
        return None
    try:
        fix_report = read_json(fix_report_path)
    except (ArtifactError, json.JSONDecodeError):
        return None

    fix_list_path = workdir / ARTIFACT_FIX_LIST
    severity_map: dict[int, str] = {}
    if fix_list_path.exists():
        try:
            fix_list = read_json(fix_list_path)
            if isinstance(fix_list, list):
                for item in fix_list:
                    if isinstance(item, dict):
                        severity_map[item.get("issue_id")] = item.get("severity", "BLOCKER")
        except (ArtifactError, json.JSONDecodeError):
            pass

    blocker_fixed = 0
    blocker_skipped = 0
    warn_skipped = 0
    for entry in fix_report:
        if not isinstance(entry, dict):
            continue
        severity = severity_map.get(entry.get("issue_id"), "BLOCKER")
        status = entry.get("status", "")
        if severity == "BLOCKER":
            if status == "fixed":
                blocker_fixed += 1
            else:
                blocker_skipped += 1
        else:
            if status != "fixed":
                warn_skipped += 1

    return {"blocker_fixed": blocker_fixed, "blocker_skipped": blocker_skipped, "warn_skipped": warn_skipped}


def determine_review_status(workdir: Path) -> str:
    """Determine review_status based on fix_report + lightweight review (ADR 0055).

    Returns "passed" or "degraded".
    BLOCKER all fixed + lightweight review confirmed → passed.
    Skipped WARNs do not cause degraded (spec: "Should fix but report is still usable").
    """
    fix_summary = check_fix_report(workdir)
    if fix_summary is None:
        return "degraded"

    if fix_summary["blocker_skipped"] > 0:
        return "degraded"

    lw_path = workdir / ARTIFACT_LIGHTWEIGHT_REVIEW
    if lw_path.exists():
        try:
            lw = read_json(lw_path)
            if not lw.get("all_blockers_fixed", False):
                return "degraded"
        except (ArtifactError, json.JSONDecodeError):
            return "degraded"

    return "passed"


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


def _re_merge_after_fix(workdir: Path) -> None:
    analysis_path = workdir / ARTIFACT_ANALYSIS
    if analysis_path.exists():
        try:
            analysis_path.unlink()
        except OSError:
            pass
    scope = {}
    try:
        scope = read_json(workdir / ARTIFACT_SCOPE)
    except (ArtifactError, OSError):
        pass
    _merge_section_files(
        workdir,
        topic=scope.get("topic", ""),
        goal_type=scope.get("goal_type", "other"),
    )
    collected_urls: set[str] | None = None
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
        if isinstance(collected, list):
            collected_urls = build_collected_url_set(collected)
    except (ArtifactError, OSError):
        pass
    try:
        analysis = read_json(workdir / ARTIFACT_ANALYSIS)
        if isinstance(analysis, dict):
            analysis = _sanitize_sections(analysis, collected_urls=collected_urls)
            write_json(analysis, workdir / ARTIFACT_ANALYSIS)
    except (ArtifactError, OSError):
        pass


def _gate_review(workdir: Path, to_phase: str = "review") -> list[str]:
    """Review gate: blocks on BLOCKER-level failures.

    - analysis→review: passes through. Review is an agent-level concern.
    - review→review (self-loop): requires review_report.md to exist (ADR 0056).
    - review→final: runs advisory gateway checks + BLOCKER on missing
      review_report.md + repair loop re-merge + status check (ADR 0055, ADR 0056).
    """
    errors: list[str] = []
    if to_phase == "review":
        current = detect_current_phase(workdir)
        if current == "post_review":
            rr_path = workdir / ARTIFACT_REVIEW_REPORT
            if not rr_path.exists():
                errors.append("[BLOCKER] review_report.md does not exist — no previous review found (self-loop guard)")
        return errors
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

        fix_summary = check_fix_report(workdir)
        if fix_summary is not None:
            if fix_summary["blocker_fixed"] > 0:
                _re_merge_after_fix(workdir)
            if fix_summary["blocker_skipped"] > 0:
                errors.append(
                    f"[BLOCKER] repair_loop: {fix_summary['blocker_skipped']} BLOCKER issue(s) not fixed — "
                    f"report status is degraded"
                )
            elif fix_summary["warn_skipped"] > 0:
                print(
                    f"  [WARN] repair_loop: {fix_summary['warn_skipped']} WARN issue(s) skipped — "
                    f"report is usable but not all issues resolved",
                    file=sys.stderr,
                )
    return errors


def check_report(workdir: Path) -> list[str]:
    """Run report checks on the generated report file (ADR 0056).

    Called by cmd_report as a post-generation step. No longer a pipeline gate.
    """
    report_path = _find_report_path(workdir)
    if report_path is None:
        return ["No report file found in output directory"]
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
