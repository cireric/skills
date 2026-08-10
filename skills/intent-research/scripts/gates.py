from __future__ import annotations

import re
from pathlib import Path

from .lib.check_types import CheckResult
from .lib.constants import (
    _NON_EXACT_EVIDENCE_TYPES,
    _VALID_EVIDENCE_TYPES,
    _VALID_GOAL_TYPES,
    _VALID_PRECISION,
    _SOURCES_DIR,
)
from .lib.utils import normalize_url, read_json, build_collected_url_set

_CJK_RANGES = (
    (0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F), (0x2B740, 0x2B81F), (0x2B820, 0x2CEAF),
    (0xF900, 0xFAFF), (0x2F800, 0x2FA1F),
    (0x3000, 0x303F), (0xFF00, 0xFFEF),
    (0x3040, 0x309F), (0x30A0, 0x30FF),
    (0xAC00, 0xD7AF),
)


def _has_cjk(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def check_scope(scope: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    topic = scope.get("topic", "")
    if not topic:
        results.append(CheckResult("scope_topic", "BLOCKER", "scope.json missing topic"))
    else:
        results.append(CheckResult("scope_topic", "PASS"))

    goal_type = scope.get("goal_type", "")
    if goal_type not in _VALID_GOAL_TYPES:
        results.append(CheckResult("scope_goal_type", "BLOCKER", f"invalid goal_type: {goal_type!r}"))
    else:
        results.append(CheckResult("scope_goal_type", "PASS"))

    if topic and _has_cjk(topic):
        if not scope.get("english_title"):
            results.append(CheckResult("scope_english_title", "BLOCKER", "CJK topic requires english_title"))
        else:
            results.append(CheckResult("scope_english_title", "PASS"))

    return results


def check_collected(collected: list[dict], scope: dict) -> list[CheckResult]:
    results: list[CheckResult] = []

    if not collected:
        results.append(CheckResult("collected_empty", "BLOCKER", "collected.json is empty"))
        return results

    results.append(CheckResult("collected_empty", "PASS"))

    directions = scope.get("search_directions", [])
    if directions:
        missing_dirs = []
        covered = set()
        for entry in collected:
            d = entry.get("direction", "")
            if d and d != "other":
                covered.add(d)
        for d in directions:
            if d not in covered:
                missing_dirs.append(d)
        if missing_dirs:
            results.append(CheckResult(
                "direction_coverage", "WARN",
                f"directions with no sources: {missing_dirs}"
            ))
        else:
            results.append(CheckResult("direction_coverage", "PASS"))

    no_direction = [e.get("url", "?") for e in collected if not e.get("direction")]
    if no_direction:
        results.append(CheckResult(
            "direction_tagging", "WARN",
            f"{len(no_direction)} entries missing direction field"
        ))
    else:
        results.append(CheckResult("direction_tagging", "PASS"))

    return results


def check_source_sufficiency(collected: list[dict], scope: dict, analysis: dict | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    decision_questions = scope.get("decision_questions", [])

    if not decision_questions:
        results.append(CheckResult("source_sufficiency", "PASS", "no decision_questions defined"))
        return results

    tier1_2_urls = set()
    for entry in collected:
        tier = entry.get("source_tier")
        if tier is not None and int(tier) <= 2:
            tier1_2_urls.add(normalize_url(entry.get("url", "")))

    high_tier_count = len(tier1_2_urls)
    total = len(collected)

    if high_tier_count == 0:
        results.append(CheckResult(
            "source_sufficiency", "WARN",
            f"no Tier 1/2 sources found ({total} total). Decision questions may not be answerable with high-quality evidence."
        ))
        return results

    uncovered_dqs = []
    for dq in decision_questions:
        dq_id = dq.get("id", "")
        if not dq_id:
            continue
        has_tier12 = False
        if analysis:
            for section in analysis.get("sections", []):
                if dq_id in section.get("decision_questions_answered", []):
                    for claim in section.get("claims", []):
                        for url in claim.get("sources", []):
                            if normalize_url(url) in tier1_2_urls:
                                has_tier12 = True
                                break
                        if has_tier12:
                            break
                if has_tier12:
                    break
        if not has_tier12:
            uncovered_dqs.append(dq.get("question", dq_id))

    if uncovered_dqs:
        results.append(CheckResult(
            "source_sufficiency", "WARN",
            f"{len(uncovered_dqs)} DQ(s) lack Tier 1/2 sources: " + "; ".join(uncovered_dqs[:5])
        ))
    elif high_tier_count / total < 0.20:
        results.append(CheckResult(
            "source_sufficiency", "WARN",
            f"Tier 1/2 sources only {high_tier_count}/{total} ({high_tier_count/total:.0%}). Consider finding more primary sources."
        ))
    else:
        results.append(CheckResult(
            "source_sufficiency", "PASS",
            f"Tier 1/2: {high_tier_count}/{total} ({high_tier_count/total:.0%}), all DQs covered"
        ))

    return results


def check_precision_rules(analysis: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    violations = []

    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for i, claim in enumerate(section.get("claims", [])):
            et = claim.get("evidence_type", "")
            prec = claim.get("precision", "")
            if et in _NON_EXACT_EVIDENCE_TYPES and prec == "exact":
                violations.append(f"section={sec_id} claim={i}: evidence_type={et!r} cannot have precision=exact")
            if et and et not in _VALID_EVIDENCE_TYPES:
                violations.append(f"section={sec_id} claim={i}: invalid evidence_type={et!r}")
            if prec and prec not in _VALID_PRECISION:
                violations.append(f"section={sec_id} claim={i}: invalid precision={prec!r}")

    if violations:
        results.append(CheckResult(
            "precision_rules", "BLOCKER",
            f"{len(violations)} violation(s): " + "; ".join(violations[:5])
        ))
    else:
        results.append(CheckResult("precision_rules", "PASS"))

    return results


def check_ref_markers(analysis: dict, collected_urls: set[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    missing = []
    ref_re = re.compile(r'\{\{ref:(.*?)\}\}')

    for section in analysis.get("sections", []):
        content = section.get("content", "")
        for match in ref_re.finditer(content):
            url = normalize_url(match.group(1).strip())
            if url not in collected_urls:
                missing.append(url)

    if missing:
        results.append(CheckResult(
            "ref_marker_validity", "BLOCKER",
            f"{len(missing)} ref URL(s) not in collected.json: " + "; ".join(missing[:5])
        ))
    else:
        results.append(CheckResult("ref_marker_validity", "PASS"))

    return results


def run_all_checks(workdir: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    scope_path = workdir / "scope.json"
    collected_path = workdir / "collected.json"
    analysis_path = workdir / "analysis.json"

    scope = {}
    collected = []
    analysis = {}

    if analysis_path.exists():
        analysis = read_json(analysis_path)

    if scope_path.exists():
        scope = read_json(scope_path)
        results.extend(check_scope(scope))

    if collected_path.exists():
        collected = read_json(collected_path)
        if scope:
            results.extend(check_collected(collected, scope))
            results.extend(check_source_sufficiency(collected, scope, analysis or None))

    if analysis_path.exists():
        results.extend(check_precision_rules(analysis))
        if collected:
            collected_urls = build_collected_url_set(collected)
            results.extend(check_ref_markers(analysis, collected_urls))

    return results
