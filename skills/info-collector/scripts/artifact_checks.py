"""Artifact-level gateway checks: operate on JSON artifacts in workdir."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_SCOPE,
    _CHINESE_STOP_WORDS,
    _CONCRETENESS_STRICT_GOAL_TYPES,
    _EXPLORATORY_GOAL_TYPES,
    _METHODOLOGY_MIN_WORDS,
    _MIN_SOURCES,
    _QUANTITATIVE_GOAL_TYPES,
    _REQUIRED_SECTION_IDS,
    _SINGLE_SOURCE_RATIO,
    _TIER_BALANCE_THRESHOLD,
    _VAGUE_DENSITY_THRESHOLD,
    _VAGUE_PHRASES_EN,
    _VAGUE_PHRASES_ZH,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_by_url, build_collected_url_set, normalize_url, read_json, tokenize_cjk_aware

_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')

@dataclass
class CheckResult:
    name: str
    level: str  # "BLOCKER" | "WARN"
    passed: bool
    message: str = ""

def _read_artifact(path: Path, check_name: str, read_error_level: str = "BLOCKER") -> tuple[dict | None, CheckResult | None]:
    """Read a JSON artifact, returning (data, None) on success or (None, CheckResult) on failure.

    On ArtifactError:
      - read_error_level="BLOCKER" → CheckResult(name, "BLOCKER", False, str(e))
      - read_error_level="WARN"    → CheckResult(name, "WARN", True, f"Cannot read {path.name}")
    """
    try:
        data = read_json(path)
    except ArtifactError as e:
        if read_error_level == "BLOCKER":
            return None, CheckResult(check_name, "BLOCKER", False, str(e))
        return None, CheckResult(check_name, "WARN", True, f"Cannot read {path.name}")
    return data, None

def check_artifact_exists(workdir: Path) -> CheckResult:
    missing = []
    for name in (ARTIFACT_SCOPE, ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS):
        if not (workdir / name).exists():
            missing.append(name)
    if missing:
        return CheckResult("artifact_exists", "BLOCKER", False, f"Missing: {', '.join(missing)}")
    return CheckResult("artifact_exists", "BLOCKER", True)


def check_url_traceability(workdir: Path) -> CheckResult:
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "url_traceability")
    if err:
        return err
    collected, err = _read_artifact(workdir / ARTIFACT_COLLECTED, "url_traceability")
    if err:
        return err
    collected_urls = build_collected_url_set(collected)
    untraceable: list[str] = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            for url in claim.get("source_urls", []):
                norm = normalize_url(url)
                if norm not in collected_urls:
                    untraceable.append(f"sections.{sec_id}.claims[{ci}]: {url}")
    if untraceable:
        count = len(untraceable)
        if count <= 5:
            detail = "; ".join(untraceable)
        else:
            detail = f"{count} claim URLs not found in collected.json (showing first 5): " + "; ".join(untraceable[:5])
        return CheckResult("url_traceability", "BLOCKER", False, detail)
    return CheckResult("url_traceability", "BLOCKER", True)


def check_section_coverage(workdir: Path, goal_type: str) -> CheckResult:
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "section_coverage")
    if err:
        return err
    if goal_type in _EXPLORATORY_GOAL_TYPES:
        present = {s["id"] for s in analysis.get("sections", [])}
        if "overview" not in present:
            return CheckResult(
                "section_coverage",
                "BLOCKER",
                False,
                "Missing 'overview' section for exploratory goal_type",
            )
        if len(present) < 2:
            return CheckResult(
                "section_coverage",
                "BLOCKER",
                False,
                f"Exploratory goal_type requires at least 2 sections, found {len(present)}: {', '.join(present)}",
            )
        return CheckResult("section_coverage", "BLOCKER", True)
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




def check_analysis_schema(workdir: Path) -> CheckResult:
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "analysis_schema")
    if err:
        return err
    from .lib.schemas import validate_analysis
    schema_errors = validate_analysis(analysis)
    if schema_errors:
        detail = "; ".join(f"{e.field}: {e.message}" for e in schema_errors)
        return CheckResult("analysis_schema", "BLOCKER", False, detail)
    for section in analysis.get("sections", []):
        content = section.get("content", "")
        if content.startswith("## "):
            return CheckResult(
                "analysis_schema", "WARN", True,
                "Section content starts with '## ' (possible duplicate markdown heading)",
            )
    return CheckResult("analysis_schema", "BLOCKER", True)


def check_quality_heuristics(workdir: Path) -> CheckResult:
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "quality_heuristics", "WARN")
    if err:
        return err
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


_VERSION_PATTERN = re.compile(r'\bv\d+\.\d+', re.IGNORECASE)


def _count_words(text: str) -> int:
    return len(tokenize_cjk_aware(text))



_LIST_ITEM_PATTERN = re.compile(r'^\s*\d+\.', re.MULTILINE)
_NUMBER_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\b')


def _has_valid_number(text: str) -> bool:
    text = _YEAR_PATTERN.sub("", text)
    text = _VERSION_PATTERN.sub("", text)
    text = _LIST_ITEM_PATTERN.sub("", text)
    return bool(_NUMBER_PATTERN.search(text))


def _has_concrete_name(text: str) -> bool:
    if re.search(r'`[^`]+`', text):
        return True
    sentences = re.split(r'[.!?。！？]+', text)
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        words = stripped.split()
        for i, word in enumerate(words):
            clean = word.strip(",.;:;!?()[]{{}}'\"")
            if i == 0:
                if len(clean) >= 2 and clean[0].isupper() and clean[1:].islower():
                    return True
                continue
            if len(clean) >= 2 and clean[0].isupper():
                return True
    i = 0
    while i < len(text):
        ch = text[i]
        if '\u4e00' <= ch <= '\u9fff':
            j = i + 1
            while j < len(text) and '\u4e00' <= text[j] <= '\u9fff':
                j += 1
            segment = text[i:j]
            if len(segment) >= 2 and segment not in _CHINESE_STOP_WORDS and segment not in _VAGUE_PHRASES_ZH:
                return True
            i = j
        else:
            i += 1
    return False


def check_content_concreteness(workdir: Path, goal_type: str) -> CheckResult:
    if goal_type not in _QUANTITATIVE_GOAL_TYPES:
        return CheckResult("content_concreteness", "WARN", True, "Skipped (non-quantitative goal type)")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "content_concreteness", "WARN")
    if err:
        return err
    vague_issues = []
    number_issues = []
    name_issues = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        content = section.get("content", "")
        claims = section.get("claims", [])
        has_claims = bool(claims)
        total_words = _count_words(content)
        vague_count = 0
        lower_content = content.lower()
        for phrase in _VAGUE_PHRASES_ZH:
            vague_count += lower_content.count(phrase.lower())
        for phrase in _VAGUE_PHRASES_EN:
            vague_count += lower_content.count(phrase.lower())
        if total_words > 0 and vague_count / total_words > _VAGUE_DENSITY_THRESHOLD:
            vague_issues.append(f"Section '{sec_id}': vague phrase density {vague_count / total_words:.0%} exceeds threshold")
        if has_claims:
            if not _has_valid_number(content):
                if goal_type in _CONCRETENESS_STRICT_GOAL_TYPES:
                    number_issues.append(f"Section '{sec_id}': no valid numbers found")
                else:
                    number_issues.append(f"Section '{sec_id}': no valid numbers found (advisory)")
            if not _has_concrete_name(content):
                if goal_type in _CONCRETENESS_STRICT_GOAL_TYPES:
                    name_issues.append(f"Section '{sec_id}': no concrete names found")
                else:
                    name_issues.append(f"Section '{sec_id}': no concrete names found (advisory)")
    blockers = []
    warnings = []
    if vague_issues:
        warnings.extend(vague_issues)
    if goal_type in _CONCRETENESS_STRICT_GOAL_TYPES:
        if number_issues:
            blockers.extend(number_issues)
        if name_issues:
            blockers.extend(name_issues)
    else:
        if number_issues:
            warnings.extend(number_issues)
        if name_issues:
            warnings.extend(name_issues)
    if blockers:
        return CheckResult("content_concreteness", "BLOCKER", False, "; ".join(blockers + warnings))
    if warnings:
        return CheckResult("content_concreteness", "WARN", False, "; ".join(warnings))
    return CheckResult("content_concreteness", "BLOCKER", True)


def check_methodology_depth(workdir: Path, goal_type: str) -> CheckResult:
    """WARN if methodology section is too short or lacks a Markdown table."""
    if goal_type not in _QUANTITATIVE_GOAL_TYPES:
        return CheckResult("methodology_depth", "WARN", True, "Skipped (non-quantitative goal type)")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "methodology_depth", "WARN")
    if err:
        return err
    methodology = None
    for section in analysis.get("sections", []):
        if section.get("id") == "methodology":
            methodology = section
            break
    if methodology is None:
        return CheckResult("methodology_depth", "WARN", True, "Skipped (no methodology section)")
    content = methodology.get("content", "")
    issues = []
    word_count = _count_words(content)
    if word_count < _METHODOLOGY_MIN_WORDS:
        issues.append(f"Methodology section has only {word_count} words (min {_METHODOLOGY_MIN_WORDS})")
    if "|" not in content:
        issues.append("Methodology section has no Markdown table")
    if issues:
        return CheckResult("methodology_depth", "WARN", False, "; ".join(issues))
    return CheckResult("methodology_depth", "WARN", True)


def check_recommendation_structure(workdir: Path, goal_type: str) -> CheckResult:
    """WARN if recommendation section lacks comparison table or '不推荐'/'not recommended'."""
    if goal_type not in ("tech_selection", "competitive_comparison"):
        return CheckResult(
            "recommendation_structure", "WARN", True, "Skipped (non-applicable goal type)"
        )
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "recommendation_structure", "WARN")
    if err:
        return err
    recommendation = None
    for section in analysis.get("sections", []):
        if section.get("id") == "recommendation":
            recommendation = section
            break
    if recommendation is None:
        return CheckResult(
            "recommendation_structure", "WARN", True, "Skipped (no recommendation section)"
        )
    content = recommendation.get("content", "")
    issues = []
    if "|" not in content:
        issues.append("recommendation section lacks comparison table")
    if "不推荐" not in content and "not recommended" not in content:
        issues.append(
            "recommendation section lacks '不推荐'/'not recommended' "
            "for tech_selection/competitive_comparison"
        )
    if issues:
        return CheckResult("recommendation_structure", "WARN", False, "; ".join(issues))
    return CheckResult("recommendation_structure", "WARN", True)


def check_source_tier_balance(workdir: Path, goal_type: str) -> CheckResult:
    """WARN if referenced sources have <30% Tier 1+2 sources."""
    if goal_type not in _QUANTITATIVE_GOAL_TYPES:
        return CheckResult("source_tier_balance", "WARN", True, "Skipped (non-quantitative goal type)")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "source_tier_balance", "WARN")
    if err:
        return err
    collected, err = _read_artifact(workdir / ARTIFACT_COLLECTED, "source_tier_balance", "WARN")
    if err:
        return err
    if not collected:
        return CheckResult("source_tier_balance", "WARN", True, "Skipped (no collected items)")
    collected_by_url = build_collected_by_url(collected)
    referenced_urls = set()
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            for url in claim.get("source_urls", []):
                referenced_urls.add(normalize_url(url))
    if not referenced_urls:
        return CheckResult("source_tier_balance", "WARN", True, "Skipped (no referenced URLs)")
    tier1_2_count = 0
    total_with_tier = 0
    for norm_url in referenced_urls:
        item = collected_by_url.get(norm_url)
        if item is None:
            continue
        tier = item.get("source_tier")
        if tier is not None:
            total_with_tier += 1
            if tier in (1, 2):
                tier1_2_count += 1
    if total_with_tier == 0:
        return CheckResult("source_tier_balance", "WARN", True, "Skipped (no sources with tier)")
    ratio = tier1_2_count / total_with_tier
    if ratio < _TIER_BALANCE_THRESHOLD:
        return CheckResult(
            "source_tier_balance",
            "WARN",
            False,
            f"Low Tier 1+2 source ratio: {tier1_2_count}/{total_with_tier} ({ratio:.0%}) < {_TIER_BALANCE_THRESHOLD:.0%}",
        )
    return CheckResult("source_tier_balance", "WARN", True)


def run_all(workdir: Path, goal_type: str) -> list[CheckResult]:
    from .claim_validator import ClaimValidator
    claim_results = ClaimValidator(workdir, goal_type).check()
    return [
        check_artifact_exists(workdir),
        check_url_traceability(workdir),
        check_section_coverage(workdir, goal_type),
        check_analysis_schema(workdir),
        check_quality_heuristics(workdir),
        check_content_concreteness(workdir, goal_type),
        check_methodology_depth(workdir, goal_type),
        check_recommendation_structure(workdir, goal_type),
        check_source_tier_balance(workdir, goal_type),
    ] + claim_results
