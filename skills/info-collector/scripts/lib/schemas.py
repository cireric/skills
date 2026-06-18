"""Centralized schema validation for info-collector artifacts (ADR 0015).

TypedDict definitions provide type-checker information; validate functions
accept raw dict (from read_json()) and return list[ValidationError].
Schema validation answers "is the structure correct?" — quality gates
answer "is the content good enough?". Claim metadata completeness
(evidence_type/confidence/precision) is a quality concern, not a schema
concern, and remains in gateway.py.
"""

from __future__ import annotations

from typing import TypedDict

from .exceptions import ValidationError


class ScopeDict(TypedDict, total=False):
    topic: str
    goal_type: str
    depth: str
    audience: str
    scope_description: str
    search_directions: list[str]
    report_language: str
    english_title: str


class ClaimDict(TypedDict, total=False):
    text: str
    source_urls: list[str]
    evidence_type: str
    confidence: str
    precision: str
    metric_type: str
    source_metadata: dict
    verified: bool


class SectionDict(TypedDict, total=False):
    id: str
    title: str
    content: str
    claims: list[ClaimDict]


class AnalysisDict(TypedDict, total=False):
    topic: str
    goal_type: str
    sections: list[SectionDict]


class CollectedEntryDict(TypedDict, total=False):
    url: str
    title: str
    snippet: str
    source_tier: int
    fetched_content: str
    covered_directions: list[str]


_VALID_GOAL_TYPES = frozenset({
    "exploratory", "panoramic_understanding", "tech_selection",
    "feasibility_assessment", "competitive_comparison", "academic_research",
    "fact_check", "background_check", "market_analysis", "other",
})
_VALID_DEPTHS = frozenset({"quick", "standard", "deep"})
_VALID_AUDIENCES = frozenset({"CTO", "engineer", "researcher", "general"})
_VALID_METRIC_TYPES = frozenset({
    "swe_bench_verified", "swe_bench_pro", "terminal_bench",
    "pr_merge_rate", "refactoring_safety", "custom",
})
_SCOPE_REQUIRED_FIELDS = (
    "topic", "goal_type", "depth", "audience",
    "scope_description", "search_directions",
)
_ANALYSIS_REQUIRED_FIELDS = ("topic", "goal_type")
_SECTION_REQUIRED_FIELDS = ("id", "title", "content")
_CLAIM_REQUIRED_FIELDS = ("text", "source_urls")
_COLLECTED_REQUIRED_FIELDS = ("url", "title", "snippet")


def _err(field: str, message: str) -> ValidationError:
    return ValidationError(field, message)


def validate_scope(data: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for field in _SCOPE_REQUIRED_FIELDS:
        if field not in data:
            errors.append(_err(field, f"missing required field: {field}"))
    # Type checks for present fields
    if "topic" in data and not isinstance(data["topic"], str):
        errors.append(_err("topic", f"expected str, got {type(data['topic']).__name__}"))
    if "goal_type" in data:
        if not isinstance(data["goal_type"], str):
            errors.append(_err("goal_type", f"expected str, got {type(data['goal_type']).__name__}"))
        elif data["goal_type"] not in _VALID_GOAL_TYPES:
            errors.append(_err("goal_type", f"Invalid goal_type: {data['goal_type']}"))
    if "depth" in data:
        if not isinstance(data["depth"], str):
            errors.append(_err("depth", f"expected str, got {type(data['depth']).__name__}"))
        elif data["depth"] not in _VALID_DEPTHS:
            errors.append(_err("depth", f"Invalid depth: {data['depth']}"))
    if "audience" in data:
        if not isinstance(data["audience"], str):
            errors.append(_err("audience", f"expected str, got {type(data['audience']).__name__}"))
        elif data["audience"] not in _VALID_AUDIENCES:
            errors.append(_err("audience", f"Invalid audience: {data['audience']} (must be CTO, engineer, researcher, or general)"))
    if "scope_description" in data and not isinstance(data["scope_description"], str):
        errors.append(_err("scope_description", f"expected str, got {type(data['scope_description']).__name__}"))
    if "search_directions" in data:
        if not isinstance(data["search_directions"], list):
            errors.append(_err("search_directions", f"expected list, got {type(data['search_directions']).__name__}"))
        elif not data["search_directions"]:
            errors.append(_err("search_directions", "search_directions must be a non-empty list"))
        elif not all(isinstance(d, str) for d in data["search_directions"]):
            errors.append(_err("search_directions", "search_directions must contain only strings"))
    if "report_language" in data:
        rl = data["report_language"]
        if not isinstance(rl, str) or not rl:
            errors.append(_err("report_language", "report_language must be a non-empty string if present"))
    if "english_title" in data:
        et = data["english_title"]
        if not isinstance(et, str) or not et:
            errors.append(_err("english_title", "english_title must be a non-empty string if present"))
    _check_english_title_required(data, errors)
    return errors


def _has_non_ascii(s: str) -> bool:
    return any(ord(c) > 127 for c in s)


def _check_english_title_required(data: dict, errors: list[ValidationError]) -> None:
    topic = data.get("topic")
    if isinstance(topic, str) and _has_non_ascii(topic) and "english_title" not in data:
        errors.append(_err("english_title", "english_title is required when topic contains non-ASCII characters"))


def validate_analysis(data: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for field in _ANALYSIS_REQUIRED_FIELDS:
        if field not in data:
            errors.append(_err(field, f"missing required field: {field}"))
    if "topic" in data and not isinstance(data["topic"], str):
        errors.append(_err("topic", f"expected str, got {type(data['topic']).__name__}"))
    if "goal_type" in data and not isinstance(data["goal_type"], str):
        errors.append(_err("goal_type", f"expected str, got {type(data['goal_type']).__name__}"))
    sections = data.get("sections")
    if sections is None:
        errors.append(_err("sections", "missing required field: sections"))
    elif not isinstance(sections, list):
        errors.append(_err("sections", f"expected list, got {type(sections).__name__}"))
    elif not sections:
        errors.append(_err("sections", "sections must be a non-empty list"))
    else:
        _validate_sections(sections, errors)
    return errors


def _validate_sections(sections: list, errors: list[ValidationError]) -> None:
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            errors.append(_err(f"sections[{i}]", f"expected dict, got {type(sec).__name__}"))
            continue
        for field in _SECTION_REQUIRED_FIELDS:
            if field not in sec:
                errors.append(_err(f"sections[{i}].{field}", f"missing required field: {field}"))
        if "id" in sec and not isinstance(sec["id"], str):
            errors.append(_err(f"sections[{i}].id", f"expected str, got {type(sec['id']).__name__}"))
        if "title" in sec and not isinstance(sec["title"], str):
            errors.append(_err(f"sections[{i}].title", f"expected str, got {type(sec['title']).__name__}"))
        if "content" in sec and not isinstance(sec["content"], str):
            errors.append(_err(f"sections[{i}].content", f"expected str, got {type(sec['content']).__name__}"))
        claims = sec.get("claims")
        if claims is not None:
            if not isinstance(claims, list):
                errors.append(_err(f"sections[{i}].claims", f"expected list, got {type(claims).__name__}"))
            else:
                _validate_claims(i, claims, errors)


def _validate_claims(sec_idx: int, claims: list, errors: list[ValidationError]) -> None:
    for j, claim in enumerate(claims):
        prefix = f"sections[{sec_idx}].claims[{j}]"
        if not isinstance(claim, dict):
            errors.append(_err(prefix, f"expected dict, got {type(claim).__name__}"))
            continue
        for field in _CLAIM_REQUIRED_FIELDS:
            if field not in claim:
                errors.append(_err(f"{prefix}.{field}", f"missing required field: {field}"))
        if "source_urls" in claim:
            urls = claim["source_urls"]
            if not isinstance(urls, list):
                errors.append(_err(f"{prefix}.source_urls", f"expected list, got {type(urls).__name__}"))
            elif not urls:
                errors.append(_err(f"{prefix}.source_urls", "source_urls is empty"))
            elif not all(isinstance(u, str) for u in urls):
                errors.append(_err(f"{prefix}.source_urls", "source_urls must contain only strings"))
        if "metric_type" in claim and claim["metric_type"] not in _VALID_METRIC_TYPES:
            errors.append(_err(f"{prefix}.metric_type", f"invalid metric_type '{claim['metric_type']}'"))


def validate_collected(data: list) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not isinstance(data, list):
        errors.append(_err("collected", f"expected list, got {type(data).__name__}"))
        return errors
    for i, entry in enumerate(data):
        prefix = f"entry[{i}]"
        if not isinstance(entry, dict):
            errors.append(_err(prefix, f"expected dict, got {type(entry).__name__}"))
            continue
        for field in _COLLECTED_REQUIRED_FIELDS:
            if field not in entry:
                errors.append(_err(f"{prefix}.{field}", f"missing required field: {field}"))
        if "url" in entry and not isinstance(entry["url"], str):
            errors.append(_err(f"{prefix}.url", f"expected str, got {type(entry['url']).__name__}"))
        if "source_tier" in entry and not isinstance(entry["source_tier"], int):
            errors.append(_err(f"{prefix}.source_tier", f"expected int, got {type(entry['source_tier']).__name__}"))
        if "covered_directions" in entry:
            cd = entry["covered_directions"]
            if not isinstance(cd, list):
                errors.append(_err(f"{prefix}.covered_directions", f"expected list, got {type(cd).__name__}"))
            else:
                if len(cd) > 3:
                    errors.append(_err(f"{prefix}.covered_directions", "at most 3 items allowed"))
                for k, direction in enumerate(cd):
                    if not isinstance(direction, str) or not direction:
                        errors.append(_err(f"{prefix}.covered_directions[{k}]", "each item must be a non-empty string"))
    return errors
