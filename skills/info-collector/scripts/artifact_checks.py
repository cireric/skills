"""Artifact-level gateway checks: operate on JSON artifacts in workdir."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_SCOPE,
    _CHINESE_STOP_WORDS,
    _EXPLORATORY_GOAL_TYPES,
    _METHODOLOGY_MIN_WORDS,
    _MIN_KEY_INSIGHTS_PANORAMIC,
    _MIN_SOURCES,
    _QUANTITATIVE_GOAL_TYPES,
    _REQUIRED_SECTION_IDS,
    _SUBAGENT_DELEGATION_MIN_SECTIONS,
    _TIER_BALANCE_THRESHOLD,
    _VAGUE_DENSITY_THRESHOLD,
    _VAGUE_PHRASES_EN,
    _VAGUE_PHRASES_ZH,
    single_source_ratio_threshold,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_by_url, build_collected_url_set, normalize_url, read_json, tokenize_cjk_aware

_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')

def _suggest_similar_urls(url: str, known_urls: set[str], max_suggestions: int = 3) -> list[str]:
    """Find URLs in known_urls that are prefix-matches or have small edit distance."""
    norm = normalize_url(url)
    suggestions = []
    for known in known_urls:
        if known.startswith(norm[:40]) or norm.startswith(known[:40]):
            suggestions.append(known)
            if len(suggestions) >= max_suggestions:
                break
    return suggestions

@dataclass
class CheckResult:
    name: str
    level: str  # "BLOCKER" | "WARN" | "INFO"
    passed: bool
    message: str = ""
    repair_hints: list[str] = field(default_factory=list)

def _read_depth(workdir: Path) -> str:
    """Read the search depth from scope.json, defaulting to 'standard'."""
    try:
        scope = read_json(workdir / ARTIFACT_SCOPE)
    except ArtifactError:
        return "standard"
    depth = scope.get("depth")
    return depth if isinstance(depth, str) else "standard"


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
        return CheckResult(
            "artifact_exists", "BLOCKER", False,
            f"Missing: {', '.join(missing)}",
            repair_hints=[f"Missing required artifacts: {', '.join(missing)}. Ensure scope.json, collected.json, and analysis.json exist in .workdir/"],
        )
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
            for url in claim.get("sources", []):
                norm = normalize_url(url)
                if norm not in collected_urls:
                    detail = f"sections.{sec_id}.claims[{ci}]: {url}"
                    suggestions = _suggest_similar_urls(url, collected_urls)
                    if suggestions:
                        detail += f" (did you mean {suggestions[0]}?)"
                    untraceable.append(detail)
    if untraceable:
        count = len(untraceable)
        if count <= 5:
            detail = "; ".join(untraceable)
        else:
            detail = f"{count} claim URLs not found in collected.json (showing first 5): " + "; ".join(untraceable[:5])
        invalid_urls = [u.split(": ", 1)[-1].split(" (did you mean")[0] for u in untraceable]
        return CheckResult(
            "url_traceability", "BLOCKER", False, detail,
            repair_hints=[f"The following claim sources are not in collected.json: {', '.join(invalid_urls)}. Add these URLs to collected.json or update the claims to reference existing URLs"],
        )
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
                repair_hints=["Missing required sections: overview. goal_type=exploratory requires these section IDs. Add the missing sections to analysis.json"],
            )
        if len(present) < 2:
            return CheckResult(
                "section_coverage",
                "BLOCKER",
                False,
                f"Exploratory goal_type requires at least 2 sections, found {len(present)}: {', '.join(present)}",
                repair_hints=[f"Missing required sections: need at least 2 for exploratory goal_type, currently have {', '.join(present)}. goal_type={goal_type} requires these section IDs. Add the missing sections to analysis.json"],
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
            repair_hints=[f"Missing required sections: {', '.join(missing)}. goal_type={goal_type} requires these section IDs. Add the missing sections to analysis.json"],
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
        return CheckResult(
            "analysis_schema", "BLOCKER", False, detail,
            repair_hints=["analysis.json schema validation failed. Check that sections have id, title, content fields and claims have summary, sources, evidence_type, confidence, precision"],
        )
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
            if len(claim.get("sources", [])) < _MIN_SOURCES:
                single_source_claims += 1
    issues = []
    threshold = single_source_ratio_threshold(_read_depth(workdir))
    if (
        threshold is not None
        and total_claims > 0
        and single_source_claims / total_claims > threshold
    ):
        issues.append(
            f"{single_source_claims}/{total_claims} claims have single source "
            f"(WARN above {threshold:.0%} for depth={_read_depth(workdir)})"
        )
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
                number_issues.append(f"Section '{sec_id}': no valid numbers found")
            if not _has_concrete_name(content):
                name_issues.append(f"Section '{sec_id}': no concrete names found")
    warnings = vague_issues + number_issues + name_issues
    if warnings:
        return CheckResult("content_concreteness", "WARN", False, "; ".join(warnings))
    return CheckResult("content_concreteness", "WARN", True)


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
            for url in claim.get("sources", []):
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


def check_key_insights_coverage(workdir: Path, goal_type: str) -> CheckResult:
    if goal_type not in _EXPLORATORY_GOAL_TYPES:
        return CheckResult("key_insights_coverage", "WARN", True, "Skipped (non-exploratory goal type)")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "key_insights_coverage", "WARN")
    if err:
        return err
    issues = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        insights = section.get("key_insights")
        if insights is None:
            issues.append(f"Section '{sec_id}': missing key_insights")
        elif not isinstance(insights, list) or len(insights) < _MIN_KEY_INSIGHTS_PANORAMIC:
            count = len(insights) if isinstance(insights, list) else 0
            issues.append(f"Section '{sec_id}': {count} key_insights (min {_MIN_KEY_INSIGHTS_PANORAMIC})")
        elif isinstance(insights, list):
            for j, insight in enumerate(insights):
                if isinstance(insight, dict):
                    urls = insight.get("sources")
                    if not isinstance(urls, list) or len(urls) < _MIN_SOURCES:
                        count = len(urls) if isinstance(urls, list) else 0
                        issues.append(f"Section '{sec_id}' key_insights[{j}]: {count} sources (min {_MIN_SOURCES})")
        tensions = section.get("tensions")
        if isinstance(tensions, list):
            for j, tension in enumerate(tensions):
                if isinstance(tension, dict):
                    urls = tension.get("sources")
                    if not isinstance(urls, list) or len(urls) < _MIN_SOURCES:
                        count = len(urls) if isinstance(urls, list) else 0
                        issues.append(f"Section '{sec_id}' tensions[{j}]: {count} sources (min {_MIN_SOURCES})")
    if issues:
        return CheckResult("key_insights_coverage", "WARN", False, "; ".join(issues))
    return CheckResult("key_insights_coverage", "WARN", True)


def check_subagent_delegation(workdir: Path) -> CheckResult:
    if not workdir.exists():
        return CheckResult("subagent_delegation", "BLOCKER", True, "Skipped (workdir not found)")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "subagent_delegation", "WARN")
    if err:
        return err
    sections = analysis.get("sections", [])
    if len(sections) < _SUBAGENT_DELEGATION_MIN_SECTIONS:
        return CheckResult("subagent_delegation", "BLOCKER", True, "Skipped (fewer than 2 sections, delegation not required)")
    section_files = list(workdir.glob("analysis_section_*.json"))
    if not section_files:
        return CheckResult(
            "subagent_delegation",
            "BLOCKER",
            False,
            f"analysis.json has {len(sections)} sections but no analysis_section_*.json files found in .workdir/ — "
            f"subagent delegation is required for multi-section reports (see references/subagent-template.md). "
            f"Write each section via a separate subagent call, then merge with JSON merge only.",
            repair_hints=[f"analysis.json has {len(sections)} sections but no analysis_section_*.json files found in .workdir/. Delegate section writing to subagents, each producing analysis_section_{{id}}.json"],
        )
    missing_ids = []
    for section in sections:
        sec_id = section.get("id", "")
        if sec_id and not any(sec_id in f.name for f in section_files):
            missing_ids.append(sec_id)
    if missing_ids:
        return CheckResult(
            "subagent_delegation",
            "BLOCKER",
            False,
            f"Sections without matching analysis_section_*.json: {', '.join(missing_ids)} — "
            f"these sections may not have been written by independent subagents",
        )
    return CheckResult("subagent_delegation", "BLOCKER", True, f"{len(section_files)} section files found for {len(sections)} sections")


_SECTION_DEVIATION_THRESHOLD = 0.5


def check_section_deviation(workdir: Path) -> CheckResult:
    """WARN if actual sections deviate >50% from the section plan in analysis.json.

    The section plan is a reference template (ADR 0043) — agent may add, remove,
    merge, or split sections. But extreme deviation may indicate the agent lost
    track of the plan. This is advisory, not blocking.
    """
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "section_deviation", "WARN")
    if err:
        return err
    plan_ids = {s.get("id", "") for s in analysis.get("sections", []) if s.get("id")}
    if not plan_ids:
        return CheckResult("section_deviation", "WARN", True, "No section IDs in plan, deviation check skipped")
    section_files = list(workdir.glob("analysis_section_*.json"))
    if not section_files:
        return CheckResult("section_deviation", "WARN", True, "No section files, delegation check handles this")
    file_ids: set[str] = set()
    for f in section_files:
        name = f.stem.replace("analysis_section_", "")
        file_ids.add(name)
    plan_only = plan_ids - file_ids
    file_only = file_ids - plan_ids
    total = len(plan_ids)
    deviation = (len(plan_only) + len(file_only)) / total if total else 0
    if deviation > _SECTION_DEVIATION_THRESHOLD:
        details: list[str] = []
        if plan_only:
            details.append(f"planned but not written: {', '.join(sorted(plan_only))}")
        if file_only:
            details.append(f"written but not planned: {', '.join(sorted(file_only))}")
        return CheckResult(
            "section_deviation", "WARN", False,
            f"Section deviation {deviation:.0%} exceeds {_SECTION_DEVIATION_THRESHOLD:.0%} threshold — {'; '.join(details)}",
            repair_hints=["Section plan is a reference template (ADR 0043), but high deviation may indicate lost structure. Consider aligning plan and content."],
        )
    return CheckResult("section_deviation", "WARN", True, f"Section deviation {deviation:.0%}")


_TABLE_SUGGESTION_MIN_CLAIMS = 4


def check_table_suggestion(workdir: Path) -> CheckResult:
    """Suggest using Markdown tables for sections with many structured claims.

    Reads analysis.json to count claims per section.
    If a section has ≥4 claims, suggests using tables (ADR 0044).
    """
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "table_suggestion", "WARN")
    if err:
        return err
    sections = analysis.get("sections", [])
    suggestions = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        claims = section.get("claims", [])
        if not isinstance(claims, list):
            continue
        if len(claims) >= _TABLE_SUGGESTION_MIN_CLAIMS:
            title = section.get("title", section.get("id", "unknown"))
            suggestions.append(f"'{title}' has {len(claims)} claims — consider using Markdown tables for structured data")
    if suggestions:
        return CheckResult(
            "table_suggestion", "WARN", False,
            "; ".join(suggestions),
            repair_hints=["Convert multi-entity comparisons or multi-row data into Markdown tables for better scannability"],
        )
    return CheckResult("table_suggestion", "WARN", True)


def check_direction_coverage(workdir: Path) -> CheckResult:
    """WARN claim-anchor (ADR 0052): for each declared direction that has
    collected sources tagged to it, at least one claim should reference a
    source serving that direction. This is the soft anti-gaming backstop;
    the hard coverage floor lives in SearchGate.direction_coverage (BLOCKER).
    """
    scope, err = _read_artifact(workdir / ARTIFACT_SCOPE, "direction_coverage", "WARN")
    if err:
        return err
    directions = scope.get("search_directions")
    norm_dirs = [str(d).strip().lower() for d in directions if isinstance(d, str) and d.strip()] if isinstance(directions, list) else []
    if not norm_dirs:
        return CheckResult("direction_coverage", "WARN", True, "No search_directions in scope, check skipped")
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
    except ArtifactError:
        collected = None
    if not isinstance(collected, list):
        return CheckResult("direction_coverage", "WARN", True, "No collected.json, check skipped")
    dir_urls: dict[str, set[str]] = {}
    for entry in collected:
        if not isinstance(entry, dict):
            continue
        d = entry.get("direction")
        if not isinstance(d, str) or not d.strip():
            continue
        d = d.strip().lower()
        url = entry.get("url")
        if url:
            dir_urls.setdefault(d, set()).add(normalize_url(url))
    declared_with_sources = [d for d in norm_dirs if d in dir_urls]
    if not declared_with_sources:
        return CheckResult("direction_coverage", "WARN", True, "No collected sources tagged to declared directions, check skipped")
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "direction_coverage", "WARN")
    if err:
        return err
    covered: set[str] = set()
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            for u in claim.get("sources", []):
                nu = normalize_url(u)
                for d in declared_with_sources:
                    if nu in dir_urls[d]:
                        covered.add(d)
    uncovered = [d for d in declared_with_sources if d not in covered]
    if uncovered:
        return CheckResult(
            "direction_coverage", "WARN", False,
            f"declared directions have sources but no claim references them: {', '.join(uncovered)}",
            repair_hints=[f"Add claims referencing the collected sources for these directions: {', '.join(uncovered)}"],
        )
    return CheckResult("direction_coverage", "WARN", True)


_FACET_GOAL_TYPE_SETS: dict[str, list[str]] = {
    "panoramic_understanding": [
        "technical_architecture", "model_product_family", "cost_economics",
        "market_industry_impact", "community_ecosystem", "reported_limitations",
    ],
    "exploratory": [
        "technical_architecture", "model_product_family", "cost_economics",
        "market_industry_impact", "community_ecosystem", "reported_limitations",
    ],
}
_FACET_DEFAULT_SET = [
    "technical_architecture", "market_industry_impact",
    "community_ecosystem", "reported_limitations",
]
_LIMITATION_KEYWORDS = (
    "limit", "limitation", "shortcom", "drawback", "weakness",
    "局限", "不足", "缺陷", "短板", "缺点", "限制", "can only", "cannot", "fails to",
)


def _facet_set_for(goal_type: str) -> list[str]:
    return _FACET_GOAL_TYPE_SETS.get(goal_type, _FACET_DEFAULT_SET)


def check_facet_coverage(workdir: Path) -> CheckResult:
    """WARN safety net (ADR 0050): goal_type-aware facet coverage derived from
    source tiers + claim content. Does not block (it is the system safety net,
    orthogonal to the user-declared direction contract in ADR 0052)."""
    scope, err = _read_artifact(workdir / ARTIFACT_SCOPE, "facet_coverage", "WARN")
    if err:
        return err
    goal_type = scope.get("goal_type", "other")
    facets = _facet_set_for(goal_type)
    try:
        collected = read_json(workdir / ARTIFACT_COLLECTED)
    except ArtifactError:
        collected = None
    if not isinstance(collected, list):
        return CheckResult("facet_coverage", "WARN", True, "No collected.json, check skipped")
    tier_entries: dict[int, list[dict]] = {}
    community_hosts: set[str] = set()
    for entry in collected:
        if not isinstance(entry, dict):
            continue
        t = entry.get("source_tier")
        if isinstance(t, int):
            tier_entries.setdefault(t, []).append(entry)
        if t == 4:
            url = entry.get("url", "")
            host = urlparse(url).hostname
            if host:
                community_hosts.add(host)
    has_t12 = bool(tier_entries.get(1) or tier_entries.get(2))
    has_t3 = bool(tier_entries.get(3))
    has_t4 = bool(tier_entries.get(4))
    analysis, err = _read_artifact(workdir / ARTIFACT_ANALYSIS, "facet_coverage", "WARN")
    if err:
        return err
    limitation_claims = 0
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            summary = (claim.get("summary") or "").lower()
            if any(k in summary for k in _LIMITATION_KEYWORDS):
                limitation_claims += 1
    missing: list[str] = []
    repair: list[str] = []
    if not has_t12:
        missing.append("technical_architecture/model_product_family/cost_economics")
        repair.append("Collect Tier 1/2 sources (papers, official docs, repos) for technical/cost facets")
    if not has_t3:
        missing.append("market_industry_impact")
        repair.append("Collect Tier 3 industry/news sources for market/industry impact")
    if not has_t4:
        missing.append("community_ecosystem")
        repair.append("Collect Tier 4 community/UGC sources (Reddit, HN, Zhihu, Weibo) — see config.json sources toolbook for site_query hints")
    elif len(community_hosts) < 2:
        missing.append("community_ecosystem (single platform)")
        repair.append(
            "Community signal is single-platform. Broaden to >=2 distinct platforms "
            "(e.g., HuggingFace + Reddit/HN, or Reddit + Zhihu/Weibo) using config.json sources "
            "toolbook for the missing platform's site_query."
        )
    if limitation_claims == 0:
        missing.append("reported_limitations")
        repair.append("Add a limitations section / claims noting the subject's self-reported shortcomings (Tier 1/2 preferred)")
    if missing:
        return CheckResult(
            "facet_coverage", "WARN", False,
            f"facet coverage gaps (safety net, non-blocking): {', '.join(missing)}",
            repair_hints=repair,
        )
    return CheckResult("facet_coverage", "WARN", True)


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
        check_key_insights_coverage(workdir, goal_type),
        check_subagent_delegation(workdir),
        check_section_deviation(workdir),
        check_table_suggestion(workdir),
        check_direction_coverage(workdir),
        check_facet_coverage(workdir),
    ] + claim_results
