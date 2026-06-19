"""Hard gate checks: artifact_exists, url_traceability, section_coverage, schema, heuristics,
precision_inflation, claim_metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .lib.constants import (
    _CHINESE_STOP_WORDS,
    _CONCRETENESS_STRICT_GOAL_TYPES,
    _EXPLORATORY_GOAL_TYPES,
    _FETCHED_CONTENT_MIN_BY_TIER,
    _FETCHED_CONTENT_MIN_LENGTH,
    _FETCHED_CONTENT_STUB_RATIO_BLOCKER,
    _METHODOLOGY_MIN_WORDS,
    _MIN_SOURCES,
    _OVERLONG_LINE_THRESHOLD,
    _QUANTITATIVE_GOAL_TYPES,
    _TIER_BALANCE_THRESHOLD,
    _VALID_CONFIDENCE,
    _VALID_EVIDENCE_TYPES,
    _VALID_METRIC_TYPES,
    _VALID_PRECISION,
    _VAGUE_DENSITY_THRESHOLD,
)
from .lib.exceptions import ArtifactError
from .lib.utils import normalize_url, read_json


_VAGUE_PHRASES_ZH = frozenset({
    "比较优秀", "性能良好", "值得关注", "较为突出", "比较突出",
    "相对较好", "较为成熟", "相当不错", "比较强大", "较为完善",
    "比较稳定", "比较丰富",
})
_VAGUE_PHRASES_EN = frozenset({
    "relatively good", "quite impressive", "worth considering", "fairly well",
    "somewhat better", "reasonably good", "fairly strong", "quite capable",
    "generally positive", "relatively mature",
})
_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')


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
    except ArtifactError as e:
        return CheckResult("url_traceability", "BLOCKER", False, str(e))
    collected_urls = {normalize_url(item["url"]) for item in collected if "url" in item}
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
    except ArtifactError as e:
        return CheckResult("section_coverage", "BLOCKER", False, str(e))
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
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError as e:
        return CheckResult("analysis_schema", "BLOCKER", False, str(e))
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


_SINGLE_SOURCE_RATIO = 0.5


def check_quality_heuristics(workdir: Path) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
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
    """WARN if >50% of claims lack evidence_type/confidence/precision."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
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


def _normalize_numbers(text: str) -> set[str]:
    """Extract normalized number strings from text for cross-format matching."""
    numbers: set[str] = set()
    for match in _PRECISE_NUMBER_PATTERN.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            num = float(raw)
        except ValueError:
            continue
        numbers.add(str(int(num)) if num == int(num) else f"{num:.1f}")
        numbers.add(raw)
    for m in re.finditer(r"\$?(\d+(?:\.\d+)?)\s*[Bb](?:illion)?", text):
        try:
            val = float(m.group(1))
            numbers.add(str(int(val * 1_000_000_000)))
            numbers.add(f"{val}B")
        except ValueError:
            pass
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*[-\u2013]\s*(\d+(?:\.\d+)?)\s*%", text):
        numbers.add(m.group(1))
        numbers.add(m.group(2))
    return numbers


def _number_found_in_source(claim_text: str, source_text: str) -> bool:
    """Check if any precise number in claim_text also appears in source_text after normalization."""
    claim_nums = _normalize_numbers(claim_text)
    source_nums = _normalize_numbers(source_text)
    return bool(claim_nums & source_nums)


def check_precision_inflation(workdir: Path, collected: list[dict] | None = None) -> CheckResult:
    """BLOCKER if claim has precision='exact' but evidence_type forbids it.
    WARN if evidence_type='third_party_estimate' and claim text contains precise-looking numbers
    that are NOT found in the source's fetched_content."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("precision_inflation", "BLOCKER", True, "Cannot read analysis.json")
    if collected is None:
        try:
            collected = read_json(workdir / "collected.json") or []
        except ArtifactError:
            collected = []
    collected_by_url: dict[str, dict] = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            collected_by_url[normalize_url(url)] = item
    blockers = []
    warnings = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            text = claim.get("text", "")
            ev = claim.get("evidence_type")
            prec = claim.get("precision")
            if prec == "exact" and ev in ("third_party_estimate", "qualitative_trend", "expert_opinion"):
                blockers.append(
                    f"sections.{sec_id}.claims[{ci}]: precision='exact' with "
                    f"evidence_type='{ev}' — use precision='range' or 'qualitative'"
                )
            if ev == "third_party_estimate" and _PRECISE_NUMBER_PATTERN.search(text):
                source_texts = []
                for url in claim.get("source_urls", []):
                    item = collected_by_url.get(normalize_url(url))
                    if item:
                        source_texts.append(
                            (item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()
                        )
                any_sufficient = any(len(src) >= 200 for src in source_texts)
                if not any_sufficient:
                    continue
                else:
                    numbers_in_source = any(
                        _number_found_in_source(text, src) for src in source_texts
                    )
                    if not numbers_in_source:
                        warnings.append(
                            f"sections.{sec_id}.claims[{ci}]: evidence_type='third_party_estimate' "
                            f"but text contains precise number not found in source — use precision='range' or rephrase qualitatively"
                        )
        # Data variance check: same metric_type, exact precision, conflicting values
        by_metric: dict[str, list[dict]] = {}
        for claim in section.get("claims", []):
            mt = claim.get("metric_type")
            if not mt:
                continue
            by_metric.setdefault(mt, []).append(claim)
        for mt, claims in by_metric.items():
            values = []
            for claim in claims:
                if claim.get("precision") != "exact":
                    continue
                text = claim.get("text", "")
                matches = _PRECISE_NUMBER_PATTERN.findall(text)
                for match in matches:
                    num_str = match[0].replace(",", "")
                    try:
                        values.append(float(num_str))
                    except ValueError:
                        pass
            if len(values) >= 2:
                min_val = min(values)
                max_val = max(values)
                avg = sum(values) / len(values)
                if avg > 0 and (max_val - min_val) / avg > 0.05:
                    blockers.append(
                        f"sections.{sec_id}: same metric_type '{mt}' has conflicting exact values "
                        f"({min_val} vs {max_val}) — use precision='range' and explain variance"
                    )
    if blockers:
        return CheckResult("precision_inflation", "BLOCKER", False, "; ".join(blockers + warnings))
    if warnings:
        return CheckResult("precision_inflation", "WARN", False, "; ".join(warnings))
    return CheckResult("precision_inflation", "BLOCKER", True)


def check_claim_verified(workdir: Path) -> CheckResult:
    """BLOCKER if any claim has verified=False.
    WARN if any claim has verified='unverifiable' (cannot be confirmed but not disproven).
    WARN if claim_verified ratio < 60% (auto-degrade signal).
    Skipped if review has not been done yet."""
    review_report = workdir / "review_report.md"
    if not review_report.exists():
        return CheckResult("claim_verified", "BLOCKER", True, "Skipped (review not yet done)")
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError as e:
        return CheckResult("claim_verified", "BLOCKER", False, str(e))
    warnings = []
    total_claims = 0
    verified_count = 0
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for claim in section.get("claims", []):
            total_claims += 1
            verified = claim.get("verified")
            if verified is True:
                verified_count += 1
            if verified is False:
                text = claim.get("text", "")[:50]
                return CheckResult(
                    "claim_verified",
                    "BLOCKER",
                    False,
                    f"Claim in section '{sec_id}' not verified: {text}",
                )
            if verified == "unverifiable":
                text = claim.get("text", "")[:50]
                warnings.append(f"Claim in section '{sec_id}' unverifiable: {text}")
    if total_claims > 0 and verified_count / total_claims < 0.6:
        warnings.append(
            f"claim_verified ratio: {verified_count}/{total_claims} "
            f"({verified_count / total_claims:.0%}) < 60% — quality should be 'degraded'"
        )
    if warnings:
        return CheckResult("claim_verified", "WARN", True, "; ".join(warnings))
    return CheckResult("claim_verified", "BLOCKER", True)


def check_source_metadata(workdir: Path) -> CheckResult:
    """BLOCKER if official_data/independent_benchmark claims lack source_metadata.test_conditions."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError as e:
        return CheckResult("source_metadata", "BLOCKER", False, str(e))
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            ev = claim.get("evidence_type")
            if ev in ("official_data", "independent_benchmark"):
                meta = claim.get("source_metadata")
                if not meta or not isinstance(meta, dict):
                    return CheckResult(
                        "source_metadata", "BLOCKER", False,
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' requires source_metadata",
                    )
                tc = meta.get("test_conditions", "")
                if not tc or (isinstance(tc, str) and not tc.strip()):
                    return CheckResult(
                        "source_metadata", "BLOCKER", False,
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' requires non-empty source_metadata.test_conditions",
                    )
    return CheckResult("source_metadata", "BLOCKER", True)


def check_metric_type_homogeneity(workdir: Path) -> CheckResult:
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("metric_type_homogeneity", "BLOCKER", True, "Cannot read analysis.json")
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        types = set()
        for claim in section.get("claims", []):
            mt = claim.get("metric_type")
            if not mt:
                continue
            ev = claim.get("evidence_type")
            if ev in ("official_data", "independent_benchmark"):
                types.add(mt)
        if len(types) > 1:
            return CheckResult(
                "metric_type_homogeneity",
                "BLOCKER",
                False,
                f"Section '{sec_id}' mixes metric_types: {sorted(types)}. "
                "Split into separate sections or tables.",
            )
    return CheckResult("metric_type_homogeneity", "BLOCKER", True)


def _count_words(text: str) -> int:
    if not text:
        return 0
    count = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if '\u4e00' <= ch <= '\u9fff':
            j = i + 1
            while j < len(text) and '\u4e00' <= text[j] <= '\u9fff':
                j += 1
            count += 1
            i = j
        elif ch.isspace() or ('\u3000' <= ch <= '\u303f') or ('\uff00' <= ch <= '\uffef'):
            i += 1
        else:
            j = i + 1
            while j < len(text) and not text[j].isspace() and not ('\u4e00' <= text[j] <= '\u9fff') and not ('\u3000' <= text[j] <= '\u303f') and not ('\uff00' <= text[j] <= '\uffef'):
                j += 1
            token = text[i:j]
            if token.strip():
                count += 1
            i = j
    return count


_VERSION_PATTERN = re.compile(r'\bv\d+\.\d+', re.IGNORECASE)
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
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("content_concreteness", "WARN", True, "Cannot read analysis.json")
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
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("methodology_depth", "WARN", True, "Cannot read analysis.json")
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
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("recommendation_structure", "WARN", True, "Cannot read analysis.json")
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
    try:
        analysis = read_json(workdir / "analysis.json")
        collected = read_json(workdir / "collected.json")
    except Exception as e:
        return CheckResult("source_tier_balance", "WARN", True, str(e))
    if not collected:
        return CheckResult("source_tier_balance", "WARN", True, "Skipped (no collected items)")
    collected_by_url = {}
    for item in collected:
        if "url" in item:
            collected_by_url[normalize_url(item["url"])] = item
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


def check_claim_dedup(workdir: Path) -> CheckResult:
    """WARN if the same claim text appears in multiple sections."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("claim_dedup", "WARN", True, "Cannot read analysis.json")
    claim_sections: dict[str, list[str]] = {}
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for claim in section.get("claims", []):
            text = claim.get("text", "").strip()
            if text:
                claim_sections.setdefault(text, []).append(sec_id)
    duplicates = {text: secs for text, secs in claim_sections.items() if len(secs) > 1}
    if duplicates:
        issues = []
        for text, secs in list(duplicates.items())[:5]:
            issues.append(f"Claim '{text[:40]}...' appears in sections: {', '.join(secs)}")
        return CheckResult(
            "claim_dedup",
            "WARN",
            False,
            f"{len(duplicates)} duplicate claims across sections: " + "; ".join(issues),
        )
    return CheckResult("claim_dedup", "WARN", True)


def check_fetched_content_depth(workdir: Path) -> CheckResult:
    """WARN/BLOCKER if collected entries have missing or stub fetched_content.
    Uses per-tier minimum lengths from _FETCHED_CONTENT_MIN_BY_TIER.
    BLOCKER if >30% of entries are stubs (excluding fetch_failed entries)."""
    try:
        collected = read_json(workdir / "collected.json") or []
    except ArtifactError:
        return CheckResult("fetched_content_depth", "WARN", True, "collected.json not found")
    if not collected:
        return CheckResult("fetched_content_depth", "WARN", True, "collected.json is empty")
    stub_count = 0
    empty_count = 0
    fetch_failed_count = 0
    tier_violations: list[str] = []
    for entry in collected:
        fc = entry.get("fetched_content", "")
        tier = entry.get("source_tier", 0)
        if entry.get("fetch_failed", False):
            fetch_failed_count += 1
            continue  # exempt from depth checks
        if not fc:
            empty_count += 1
        else:
            min_len = _FETCHED_CONTENT_MIN_BY_TIER.get(tier, _FETCHED_CONTENT_MIN_LENGTH)
            if len(fc) < min_len:
                stub_count += 1
                tier_violations.append(f"Tier {tier}: {len(fc)} chars < {min_len} min")
    total = len(collected)
    checked = total - fetch_failed_count
    problem_count = empty_count + stub_count
    ratio = problem_count / checked if checked > 0 else 0
    parts: list[str] = []
    if empty_count > 0:
        parts.append(f"{empty_count}/{total} entries have no fetched_content")
    if stub_count > 0:
        parts.append(
            f"{stub_count}/{total} entries have stub fetched_content (below per-tier minimum)"
        )
    if fetch_failed_count > 0:
        parts.append(f"{fetch_failed_count}/{total} entries have fetch_failed=true (exempt)")
    if tier_violations:
        # Show up to 3 examples
        for v in tier_violations[:3]:
            parts.append(f"  e.g. {v}")
    msg = "; ".join(parts) if parts else "all entries have substantial fetched_content"
    if ratio > _FETCHED_CONTENT_STUB_RATIO_BLOCKER:
        return CheckResult(
            "fetched_content_depth",
            "BLOCKER",
            False,
            f"{problem_count}/{checked} entries ({ratio:.0%}) have missing or stub fetched_content — re-fetch with full content before proceeding",
        )
    if problem_count > 0:
        return CheckResult("fetched_content_depth", "WARN", False, msg)
    return CheckResult("fetched_content_depth", "WARN", True, msg)


def check_search_plan_compliance(workdir: Path) -> CheckResult:
    """WARN if search_plan.json tasks are still pending (plan not followed)."""
    plan_path = workdir / "search_plan.json"
    if not plan_path.exists():
        return CheckResult("search_plan_compliance", "WARN", True, "search_plan.json not found")
    try:
        plan = read_json(plan_path)
    except ArtifactError:
        return CheckResult("search_plan_compliance", "WARN", True, "search_plan.json unreadable")
    tasks = plan.get("tasks", [])
    if not tasks:
        return CheckResult("search_plan_compliance", "WARN", True, "search_plan.json has no tasks")
    pending = [t for t in tasks if t.get("status") == "pending"]
    completed = [t for t in tasks if t.get("status") == "completed"]
    skipped = [t for t in tasks if t.get("status") == "skipped"]
    directions_in_plan = set(t.get("direction", "") for t in tasks)
    directions_completed = set(t.get("direction", "") for t in completed)
    directions_missing = directions_in_plan - directions_completed
    if pending and not completed:
        return CheckResult(
            "search_plan_compliance", "WARN", False,
            f"0/{len(tasks)} tasks completed, {len(pending)} pending — search_plan was not followed. "
            f"Directions without any completed task: {', '.join(sorted(directions_missing))}",
        )
    if directions_missing:
        return CheckResult(
            "search_plan_compliance", "WARN", False,
            f"{len(completed)}/{len(tasks)} tasks completed, but directions without coverage: {', '.join(sorted(directions_missing))}",
        )
    return CheckResult(
        "search_plan_compliance", "WARN", True,
        f"{len(completed)}/{len(tasks)} tasks completed, {len(skipped)} skipped",
    )


def check_claim_source_relevance(workdir: Path, collected: list[dict] | None = None) -> CheckResult:
    """WARN if a claim contains precise numbers not found in its source fetched_content.
    Skips claims with evidence_type='third_party_estimate' (already covered by check_precision_inflation)."""
    try:
        analysis = read_json(workdir / "analysis.json")
    except ArtifactError:
        return CheckResult("claim_source_relevance", "WARN", True, "Cannot read analysis.json")
    if collected is None:
        try:
            collected = read_json(workdir / "collected.json") or []
        except ArtifactError:
            collected = []
    collected_by_url: dict[str, dict] = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            collected_by_url[normalize_url(url)] = item
    warnings: list[str] = []
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "?")
        for ci, claim in enumerate(section.get("claims", [])):
            if claim.get("evidence_type") == "third_party_estimate":
                continue
            text = claim.get("text", "")
            if not _PRECISE_NUMBER_PATTERN.search(text):
                continue
            source_texts = []
            for url in claim.get("source_urls", []):
                item = collected_by_url.get(normalize_url(url))
                if item:
                    source_texts.append(
                        (item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()
                    )
            if not source_texts:
                continue
            any_sufficient = any(len(src) >= 200 for src in source_texts)
            if not any_sufficient:
                continue
            numbers_in_source = any(
                _number_found_in_source(text, src) for src in source_texts
            )
            if not numbers_in_source:
                warnings.append(
                    f"sections.{sec_id}.claims[{ci}]: claim contains precise number(s) "
                    f"not found in source fetched_content — verify source attribution or use range/qualitative precision"
                )
    if warnings:
        msg = f"{len(warnings)} claim(s) with numbers not found in sources: " + "; ".join(warnings[:5])
        if len(warnings) > 5:
            msg += f"; ... and {len(warnings) - 5} more"
        return CheckResult("claim_source_relevance", "WARN", False, msg)
    return CheckResult("claim_source_relevance", "WARN", True, "all numeric claims traceable to sources")


def run_all(workdir: Path, goal_type: str) -> list[CheckResult]:
    collected: list[dict] | None = None
    try:
        collected = read_json(workdir / "collected.json") or []
    except ArtifactError:
        pass
    return [
        check_artifact_exists(workdir),
        check_url_traceability(workdir),
        check_section_coverage(workdir, goal_type),
        check_analysis_schema(workdir),
        check_quality_heuristics(workdir),
        check_precision_inflation(workdir, collected),
        check_claim_source_relevance(workdir, collected),
        check_metric_type_homogeneity(workdir),
        check_claim_metadata(workdir, goal_type),
        check_claim_verified(workdir),
        check_source_metadata(workdir),
        check_content_concreteness(workdir, goal_type),
        check_methodology_depth(workdir, goal_type),
        check_recommendation_structure(workdir, goal_type),
        check_source_tier_balance(workdir, goal_type),
        check_claim_dedup(workdir),
    ]


# ---------------------------------------------------------------------------
# Report-level checks (3d: operate on the generated .md file, not JSON)
# ---------------------------------------------------------------------------

_HIDDEN_REF_DEF = re.compile(r'^\[\d+\]:\s+https?://\S')
_VISIBLE_REF_ITEM = re.compile(r'^-\s+\*\*\[\d+\]\*\*')
_INLINE_CITATION = re.compile(r'\[&#91;(\d+)&#93;\]\([^)]*\)|\[\\?\[(\d+)\\?\]\]\([^)]*\)')
_REF_DEF_NUM = re.compile(r'^\[(\d+)\]:\s+https?://\S')
_FENCED_CODE = re.compile(r'^```')
_HEADING = re.compile(r'^(#{1,6})\s+(.+)$')
_FRONT_MATTER_DELIM = re.compile(r'^---\s*$')
def check_report_dangling_refs(report_path: Path) -> CheckResult:
    """F1: WARN if in-text [N] has no matching definition in References section."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_dangling_refs", "WARN", True, f"Cannot read report: {e}")
    # Find references section
    ref_idx = content.rfind("## 参考文献")
    if ref_idx == -1:
        ref_idx = content.rfind("## References")
    if ref_idx == -1:
        return CheckResult("report_dangling_refs", "WARN", True, "No References section found")
    ref_section = content[ref_idx:]
    defined_nums = set(int(m.group(1)) for m in _REF_DEF_NUM.finditer(ref_section))
    # Also check visible list items for [N]
    visible_nums = set(int(m.group(1)) for m in re.finditer(r'\*\*\[(\d+)\]\*\*', ref_section))
    all_defined = defined_nums | visible_nums
    # Find in-text citations
    cited_nums = set()
    body = content[:ref_idx]
    for m in _INLINE_CITATION.finditer(body):
        num = m.group(1) or m.group(2)
        if num:
            cited_nums.add(int(num))
    # Also check [N][] style
    for m in re.finditer(r'\[(\d{1,2})\]\[\]', body):
        cited_nums.add(int(m.group(1)))
    dangling = cited_nums - all_defined
    if dangling:
        return CheckResult(
            "report_dangling_refs", "WARN", False,
            f"In-text citations with no reference definition: {sorted(dangling)}"
        )
    return CheckResult("report_dangling_refs", "WARN", True)


def check_report_orphaned_defs(report_path: Path) -> CheckResult:
    """F2: WARN if reference definition [N] is not cited in body text."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_orphaned_defs", "WARN", True, f"Cannot read report: {e}")
    ref_idx = content.rfind("## 参考文献")
    if ref_idx == -1:
        ref_idx = content.rfind("## References")
    if ref_idx == -1:
        return CheckResult("report_orphaned_defs", "WARN", True, "No References section found")
    ref_section = content[ref_idx:]
    defined_nums = set(int(m.group(1)) for m in _REF_DEF_NUM.finditer(ref_section))
    visible_nums = set(int(m.group(1)) for m in re.finditer(r'\*\*\[(\d+)\]\*\*', ref_section))
    all_defined = defined_nums | visible_nums
    body = content[:ref_idx]
    cited_nums = set()
    for m in _INLINE_CITATION.finditer(body):
        num = m.group(1) or m.group(2)
        if num:
            cited_nums.add(int(num))
    for m in re.finditer(r'\[(\d{1,2})\]\[\]', body):
        cited_nums.add(int(m.group(1)))
    orphaned = all_defined - cited_nums
    if orphaned:
        return CheckResult(
            "report_orphaned_defs", "WARN", False,
            f"Reference definitions not cited in body: {sorted(orphaned)}"
        )
    return CheckResult("report_orphaned_defs", "WARN", True)


def check_report_refs_visibility(report_path: Path) -> CheckResult:
    """A: WARN if References section has only [N]: URL hidden definitions with no visible list."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_refs_visibility", "WARN", True, f"Cannot read report: {e}")
    ref_idx = content.rfind("## 参考文献")
    if ref_idx == -1:
        ref_idx = content.rfind("## References")
    if ref_idx == -1:
        return CheckResult("report_refs_visibility", "WARN", True, "No References section found")
    ref_section = content[ref_idx:]
    ref_lines = ref_section.split("\n")
    has_hidden = any(_HIDDEN_REF_DEF.match(line) for line in ref_lines)
    has_visible = any(_VISIBLE_REF_ITEM.match(line) for line in ref_lines)
    if has_hidden and not has_visible:
        return CheckResult(
            "report_refs_visibility", "WARN", False,
            "References section has only hidden [N]: URL definitions — not visible in rendered output"
        )
    return CheckResult("report_refs_visibility", "WARN", True)


def check_report_table_delimiters(report_path: Path) -> CheckResult:
    """D: WARN if table delimiter row | count differs from header row."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_table_delimiters", "WARN", True, f"Cannot read report: {e}")
    issues = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Detect table header: line with | that is not a delimiter
        if "|" in line and not re.match(r'^[\s|:-]+$', line):
            header_pipes = line.count("|")
            # Next non-empty line should be delimiter
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                delim_line = lines[j].strip()
                if re.match(r'^[\s|:-]+$', delim_line):
                    delim_pipes = delim_line.count("|")
                    if header_pipes != delim_pipes:
                        issues.append(f"Line {j + 1}: delimiter has {delim_pipes} pipes, header has {header_pipes}")
        i += 1
    if issues:
        return CheckResult("report_table_delimiters", "WARN", False, "; ".join(issues))
    return CheckResult("report_table_delimiters", "WARN", True)


def check_report_front_matter(report_path: Path) -> CheckResult:
    """9: WARN if YAML front matter is malformed or missing required fields."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_front_matter", "WARN", True, f"Cannot read report: {e}")
    if not content.startswith("---"):
        return CheckResult("report_front_matter", "WARN", False, "No YAML front matter delimiter found")
    # Find closing ---
    end_match = re.search(r'^---\s*$', content[3:], re.MULTILINE)
    if not end_match:
        return CheckResult("report_front_matter", "WARN", False, "YAML front matter not properly closed")
    yaml_text = content[3:3 + end_match.start()]
    required_fields = {"topic", "goal_type", "date", "quality"}
    missing = []
    for field in required_fields:
        if not re.search(rf'^{field}\s*:', yaml_text, re.MULTILINE):
            missing.append(field)
    if missing:
        return CheckResult(
            "report_front_matter", "WARN", False,
            f"Front matter missing required fields: {', '.join(missing)}"
        )
    return CheckResult("report_front_matter", "WARN", True)


def check_report_heading_levels(report_path: Path) -> CheckResult:
    """10: WARN if heading levels skip (e.g., ## directly to ####)."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_heading_levels", "WARN", True, f"Cannot read report: {e}")
    # Skip front matter
    if content.startswith("---"):
        end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
        if end:
            content = content[3 + end.end():]
    headings = []
    for m in _HEADING.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        headings.append((level, text))
    issues = []
    for i in range(1, len(headings)):
        prev_level = headings[i - 1][0]
        curr_level = headings[i][0]
        if curr_level > prev_level + 1:
            issues.append(
                f"'{'#' * curr_level} {headings[i][1]}' (level {curr_level}) "
                f"follows '{'#' * prev_level} {headings[i - 1][1]}' (level {prev_level})"
            )
    if issues:
        return CheckResult("report_heading_levels", "WARN", False, "; ".join(issues[:5]))
    return CheckResult("report_heading_levels", "WARN", True)


def check_report_duplicate_headings(report_path: Path) -> CheckResult:
    """12: WARN if same-level headings with identical text appear more than once."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_duplicate_headings", "WARN", True, f"Cannot read report: {e}")
    if content.startswith("---"):
        end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
        if end:
            content = content[3 + end.end():]
    seen: dict[str, list[int]] = {}
    for m in _HEADING.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        key = f"L{level}:{text}"
        seen.setdefault(key, []).append(m.start())
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        items = [f"'{k.split(':', 1)[1]}' appears {len(v)} times" for k, v in list(duplicates.items())[:5]]
        return CheckResult("report_duplicate_headings", "WARN", False, "; ".join(items))
    return CheckResult("report_duplicate_headings", "WARN", True)


def check_report_unclosed_code_blocks(report_path: Path) -> CheckResult:
    """13: WARN if fenced code block markers appear an odd number of times."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_unclosed_code_blocks", "WARN", True, f"Cannot read report: {e}")
    # Skip front matter
    if content.startswith("---"):
        end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
        if end:
            content = content[3 + end.end():]
    count = len(_FENCED_CODE.findall(content))
    if count % 2 != 0:
        return CheckResult(
            "report_unclosed_code_blocks", "WARN", False,
            f"Found {count} fenced code block markers (odd number — likely unclosed)"
        )
    return CheckResult("report_unclosed_code_blocks", "WARN", True)


def check_report_empty_sections(report_path: Path) -> CheckResult:
    """15: WARN if a section heading exists but has no content before the next heading."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_empty_sections", "WARN", True, f"Cannot read report: {e}")
    if content.startswith("---"):
        end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
        if end:
            content = content[3 + end.end():]
    headings = [(m.start(), m.group(1), m.group(2).strip()) for m in _HEADING.finditer(content)]
    issues = []
    for i, (pos, level_text, heading_text) in enumerate(headings):
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(content)
        between = content[pos + len(level_text) + len(heading_text):next_pos].strip()
        if not between:
            issues.append(f"'{heading_text}' has no content")
    if issues:
        return CheckResult("report_empty_sections", "WARN", False, "; ".join(issues[:5]))
    return CheckResult("report_empty_sections", "WARN", True)


def check_report_overlong_lines(report_path: Path) -> CheckResult:
    """16: WARN if any line exceeds 500 characters."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_overlong_lines", "WARN", True, f"Cannot read report: {e}")
    overlong = []
    for i, line in enumerate(content.split("\n"), 1):
        if len(line) > _OVERLONG_LINE_THRESHOLD:
            overlong.append(f"Line {i}: {len(line)} chars")
    if overlong:
        return CheckResult(
            "report_overlong_lines", "WARN", False,
            f"{len(overlong)} line(s) over {_OVERLONG_LINE_THRESHOLD} chars: " + "; ".join(overlong[:5])
        )
    return CheckResult("report_overlong_lines", "WARN", True)


def run_report_checks(report_path: Path) -> list[CheckResult]:
    """Run all 10 report-level checks on the generated .md file."""
    return [
        check_report_dangling_refs(report_path),
        check_report_orphaned_defs(report_path),
        check_report_refs_visibility(report_path),
        check_report_table_delimiters(report_path),
        check_report_front_matter(report_path),
        check_report_heading_levels(report_path),
        check_report_duplicate_headings(report_path),
        check_report_unclosed_code_blocks(report_path),
        check_report_empty_sections(report_path),
        check_report_overlong_lines(report_path),
    ]
