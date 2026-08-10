from __future__ import annotations

import json
from pathlib import Path

from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_FIX_LIST,
    ARTIFACT_FIX_REPORT,
    ARTIFACT_LIGHTWEIGHT_REVIEW,
    ARTIFACT_SCOPE,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_url_set, read_json, write_json

__all__ = ["check_fix_report", "determine_review_status", "re_merge_after_fix"]


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


def re_merge_after_fix(workdir: Path) -> None:
    from .proceed import _merge_section_files
    from .sanitizer import sanitize_sections

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
            analysis = sanitize_sections(analysis, collected_urls=collected_urls)
            write_json(analysis, workdir / ARTIFACT_ANALYSIS)
    except (ArtifactError, OSError):
        pass
