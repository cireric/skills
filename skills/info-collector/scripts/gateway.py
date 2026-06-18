"""Hard gate checks: artifact_exists, url_traceability, section_coverage, schema, heuristics,
precision_inflation, claim_metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .lib.constants import _CHINESE_STOP_WORDS
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
_VAGUE_DENSITY_THRESHOLD = 0.10
_CONCRETENESS_STRICT_GOAL_TYPES = frozenset({"tech_selection", "competitive_comparison"})
_YEAR_PATTERN = re.compile(r'\b(20[0-9]{2})\b')

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

_TIER_BALANCE_THRESHOLD = 0.30

_VALID_METRIC_TYPES = frozenset({
    "swe_bench_verified",
    "swe_bench_pro",
    "terminal_bench",
    "pr_merge_rate",
    "refactoring_safety",
    "custom",
})


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

_EXPLORATORY_GOAL_TYPES = frozenset({"exploratory", "panoramic_understanding", "background_check", "other"})


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


_MIN_SOURCES = 2
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


_METHODOLOGY_MIN_WORDS = 150


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
