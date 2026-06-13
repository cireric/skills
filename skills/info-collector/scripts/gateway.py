"""Hard gate checks: artifact_exists, url_traceability, section_coverage, schema, heuristics,
precision_inflation, claim_metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .lib.utils import normalize_url, read_json


# Goal types that involve quantitative analysis (benchmarks, data, metrics).
_QUANTITATIVE_GOAL_TYPES = frozenset({
    "tech_selection",
    "competitive_comparison",
    "feasibility_assessment",
    "market_analysis",
    "academic_research",
})

# Valid values for claim metadata fields.
_VALID_EVIDENCE_TYPES = frozenset({
    "official_data", "independent_benchmark", "third_party_estimate",
    "qualitative_trend", "expert_opinion",
})
_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})


@dataclass
class CheckResult:
    name: str
    level: str  # "BLOCKER" | "WARN"
    passed: bool
    message: str = ""


def check_artifact_exists(workdir: Path) -> CheckResult:
    missing = []
    for name in ("scope.json", "collected.json", "analysis.json"):
        if not (workdir / name).exists():
            missing.append(name)
    if missing:
        return CheckResult("artifact_exists", "BLOCKER", False, f"Missing: {', '.join(missing)}")
    return CheckResult("artifact_exists", "BLOCKER", True)


def check_url_traceability(workdir: Path) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
        collected = read_json(workdir / "collected.json")
    except Exception as e:
        return CheckResult("url_traceability", "BLOCKER", False, str(e))
    collected_urls = {normalize_url(item["url"]) for item in collected if "url" in item}
    untraceable = []
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            for url in claim.get("source_urls", []):
                norm = normalize_url(url)
                if norm not in collected_urls:
                    untraceable.append(norm)
    if untraceable:
        return CheckResult(
            "url_traceability",
            "BLOCKER",
            False,
            f"{len(untraceable)} claim URLs not found in collected.json",
        )
    return CheckResult("url_traceability", "BLOCKER", True)


_REQUIRED_SECTION_IDS: dict[str, list[str]] = {
    "tech_selection": ["overview", "comparison", "recommendation", "methodology"],
    "feasibility_assessment": ["overview", "analysis", "conclusion", "methodology"],
    "fact_check": ["claims", "evidence", "conclusion"],
    "competitive_comparison": ["overview", "comparison", "positioning", "methodology"],
    "academic_research": ["abstract", "findings", "references", "methodology"],
    "market_analysis": ["overview", "data", "trends", "conclusion", "methodology"],
}


def check_section_coverage(workdir: Path, goal_type: str) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
    except Exception as e:
        return CheckResult("section_coverage", "BLOCKER", False, str(e))
    required = _REQUIRED_SECTION_IDS.get(goal_type, ["overview", "details"])
    present = {s["id"] for s in analysis.get("sections", [])}
    missing = [r for r in required if r not in present]
    if missing:
        return CheckResult(
            "section_coverage",
            "BLOCKER",
            False,
            f"Missing sections for {goal_type}: {', '.join(missing)}",
        )
    return CheckResult("section_coverage", "BLOCKER", True)


def _validate_section_claims(sections: list) -> str | None:
    for i, sec in enumerate(sections):
        for field in ("id", "title", "content"):
            if field not in sec:
                return f"sections[{i}] missing '{field}'"
        for j, claim in enumerate(sec.get("claims", [])):
            for field in ("text", "source_urls"):
                if field not in claim:
                    return f"sections[{i}].claims[{j}] missing '{field}'"
            if not claim.get("source_urls"):
                return f"sections[{i}].claims[{j}].source_urls is empty"
    return None


def check_analysis_schema(workdir: Path) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
    except Exception as e:
        return CheckResult("analysis_schema", "BLOCKER", False, str(e))
    for key, label in (("topic", "str"), ("goal_type", "str")):
        if key not in analysis or not isinstance(analysis[key], str):
            return CheckResult("analysis_schema", "BLOCKER", False, f"Missing '{key}' ({label})")
    sections = analysis.get("sections", [])
    if not sections:
        return CheckResult(
            "analysis_schema", "BLOCKER", False, "Missing 'sections' (non-empty list)"
        )
    err = _validate_section_claims(sections)
    if err:
        return CheckResult("analysis_schema", "BLOCKER", False, err)
    return CheckResult("analysis_schema", "BLOCKER", True)


_MIN_SOURCES = 2
_SINGLE_SOURCE_RATIO = 0.5


def check_quality_heuristics(workdir: Path) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
    except Exception:
        return CheckResult("quality_heuristics", "WARN", True, "Cannot read analysis.json")
    single_source_claims = 0
    total_claims = 0
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            total_claims += 1
            if len(claim.get("source_urls", [])) < _MIN_SOURCES:
                single_source_claims += 1
    issues = []
    if total_claims > 0 and single_source_claims / total_claims > _SINGLE_SOURCE_RATIO:
        issues.append(f"{single_source_claims}/{total_claims} claims have single source")
    if issues:
        return CheckResult("quality_heuristics", "WARN", False, "; ".join(issues))
    return CheckResult("quality_heuristics", "WARN", True)


def check_claim_metadata(workdir: Path, goal_type: str) -> CheckResult:
    """WARN if >50% of claims in quantitative goal_types lack evidence_type/confidence/precision."""
    if goal_type not in _QUANTITATIVE_GOAL_TYPES:
        return CheckResult("claim_metadata", "WARN", True, "Skipped (non-quantitative goal type)")
    try:
        analysis = read_json(workdir / "analysis.json")
    except Exception:
        return CheckResult("claim_metadata", "WARN", True, "Cannot read analysis.json")
    total = 0
    missing = 0
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            total += 1
            if not all(k in claim for k in ("evidence_type", "confidence", "precision")):
                missing += 1
    if total == 0:
        return CheckResult("claim_metadata", "WARN", True)
    ratio = missing / total
    if ratio > 0.5:
        return CheckResult(
            "claim_metadata",
            "WARN",
            False,
            f"{missing}/{total} claims lack evidence_type/confidence/precision metadata "
            f"(ratio={ratio:.0%})",
        )
    return CheckResult("claim_metadata", "WARN", True)


# Regex pattern to spot potentially inflated precision: numbers like "98%", "95%", "52,479" etc.
# Used as a heuristic signal, not a deterministic check.
_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:,\d{3})*|\d+)"       # number: 98, 52479, 112000
    r"(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?"  # optional unit
    r"(?!\w)"
)


def check_precision_inflation(workdir: Path) -> CheckResult:
    """BLOCKER if claim has precision='exact' but evidence_type forbids it.
    WARN if evidence_type='third_party_estimate' and claim text contains precise-looking numbers."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except Exception:
        return CheckResult("precision_inflation", "BLOCKER", True, "Cannot read analysis.json")
    issues = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            text = claim.get("text", "")
            ev = claim.get("evidence_type")
            prec = claim.get("precision")
            # BLOCKER: exact precision + inappropriate evidence type
            if prec == "exact" and ev in ("third_party_estimate", "qualitative_trend", "expert_opinion"):
                issues.append(
                    f"sections.{sec_id}.claims[{ci}]: precision='exact' with "
                    f"evidence_type='{ev}' — use precision='range' or 'qualitative'"
                )
            # WARN: third_party_estimate with precise-looking numbers even without annotation
            if ev == "third_party_estimate" and _PRECISE_NUMBER_PATTERN.search(text):
                issues.append(
                    f"sections.{sec_id}.claims[{ci}]: evidence_type='third_party_estimate' "
                    f"but text contains precise number — use precision='range' or rephrase qualitatively"
                )
    if issues:
        return CheckResult("precision_inflation", "BLOCKER", False, "; ".join(issues))
    return CheckResult("precision_inflation", "BLOCKER", True)


def run_all(workdir: Path, goal_type: str) -> list[CheckResult]:
    return [
        check_artifact_exists(workdir),
        check_url_traceability(workdir),
        check_section_coverage(workdir, goal_type),
        check_analysis_schema(workdir),
        check_quality_heuristics(workdir),
        check_precision_inflation(workdir),
        check_claim_metadata(workdir, goal_type),
    ]
