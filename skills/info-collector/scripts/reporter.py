from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .lib.constants import ARTIFACT_COLLECTED, _EXPLORATORY_GOAL_TYPES, _LABELS, _TIER_LABELS
from .lib.utils import build_collected_by_url, normalize_url, read_json
from .report_checks import _find_references_section


def _label(key: str, lang: str) -> str:
    return _LABELS.get((key, lang), _LABELS.get((key, "en"), key))


_REF_MARKER_RE = re.compile(r'\{\{ref:(.*?)\}\}')

_SV_MARKER = {"source_absent": "†", "source_indirect": "‡"}

_SV_ORDER = {"source_confirmed": 0, "source_indirect": 1, "source_absent": 2}


def _resolve_ref_markers(content: str, ref_map: dict[str, int], sv_map: dict[str, str] | None = None) -> str:
    def _replacer(match: re.Match) -> str:
        url = match.group(1).strip()
        norm = normalize_url(url)
        if norm not in ref_map:
            ref_map[norm] = len(ref_map) + 1
        num = ref_map[norm]
        marker = ""
        if sv_map is not None:
            sv = sv_map.get(norm, "source_confirmed")
            marker = _SV_MARKER.get(sv, "")
        return f"[&#91;{num}{marker}&#93;](#refs)"
    return _REF_MARKER_RE.sub(_replacer, content)


def _build_sv_map(analysis: dict) -> dict[str, str]:
    url_worst: dict[str, str] = {}
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            sv = claim.get("source_verification", "source_confirmed")
            for url in claim.get("source_urls", []):
                norm = normalize_url(url)
                current = url_worst.get(norm, "source_confirmed")
                if _SV_ORDER.get(sv, 0) > _SV_ORDER.get(current, 0):
                    url_worst[norm] = sv
    return url_worst


def _render_verification_summary(analysis: dict, lang: str = "en") -> str:
    sv_counts = {"source_confirmed": 0, "source_absent": 0, "source_indirect": 0}
    total = 0
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            sv = claim.get("source_verification")
            if sv and sv in sv_counts:
                sv_counts[sv] += 1
                total += 1
    if total == 0:
        return ""
    lines = [
        "",
        "> **Verification note**: This report is a research starting point, not a citable authority.",
        "> † = data not found in cited source; ‡ = data from indirect source.",
        "",
        f"| Status | Count | Ratio |",
        f"|--------|-------|-------|",
    ]
    for status in ("source_confirmed", "source_indirect", "source_absent"):
        count = sv_counts[status]
        ratio = f"{count/total:.0%}" if total else "0%"
        label = {"source_confirmed": "Confirmed", "source_indirect": "Indirect ‡", "source_absent": "Absent †"}[status]
        lines.append(f"| {label} | {count} | {ratio} |")
    return "\n".join(lines)


def _render_references(reference_map: dict[str, int], collected: list[dict], lang: str = "en") -> str:
    if not reference_map:
        return ""
    parts = [f"\n## {_label('references', lang)}\n"]
    parts.append('\n<a id="refs"></a>\n')
    collected_by_url = build_collected_by_url(collected)
    sorted_refs = sorted(reference_map.items(), key=lambda kv: kv[1])
    for norm_url, num in sorted_refs:
        item = collected_by_url.get(norm_url)
        title = item.get("title", norm_url) if item else norm_url
        tier_str = ""
        vendor_str = ""
        if item is not None:
            tier = item.get("source_tier")
            tier_key = str(tier) if tier is not None else None
            if tier_key and tier_key in _TIER_LABELS:
                tier_str = f" ({_TIER_LABELS[tier_key]})"
            va = item.get("vendor_affiliation", "")
            if isinstance(va, str) and va.strip():
                vendor_str = f" [vendor: {va.strip()}]"
        clean_url = _clean_url(norm_url)
        if title and title != clean_url:
            parts.append(f"- [{num}] [{title}{tier_str}{vendor_str}]({clean_url})")
        else:
            parts.append(f"- [{num}] [{clean_url}]({clean_url})")
    return "\n".join(parts)


def _clean_url(url: str) -> str:
    """Remove preview- prefix and other non-standard URL prefixes."""
    return re.sub(r'^https?://preview-', 'https://', url)


def _post_process(markdown: str) -> str:
    """Fix known rendering issues in the generated Markdown."""
    # Fix literal \n that should be real newlines
    markdown = re.sub(r'(?<!\\)\\n', '\n', markdown)
    # Fix preview- URL prefix
    markdown = re.sub(r'https?://preview-', 'https://', markdown)
    # Fix bare URLs in body (not in reference section) — convert to Markdown links
    ref_idx = _find_references_section(markdown)
    if ref_idx != -1:
        body = markdown[:ref_idx]
        refs = markdown[ref_idx:]
        body = re.sub(
            r'(?<!\]\()https?://(\S+)',
            r'[https://\1](https://\1)',
            body,
        )
        markdown = body + refs
    return markdown


def build_front_matter(
    topic: str,
    goal_type: str,
    scope: str,
    review_status: str,
    search_rounds: int,
    source_count: int,
    audience: str | None = None,
    report_language: str | None = None,
) -> str:
    lines = ["---"]
    lines.append(f"topic: {topic}")
    lines.append(f"goal_type: {goal_type}")
    lines.append(f"date: {date.today().isoformat()}")
    if audience:
        lines.append(f"audience: {audience}")
    if report_language:
        lines.append(f"report_language: {report_language}")
    lines.append(f"scope: {scope}")
    lines.append(f"review_status: {review_status}")
    lines.append(f"verification_required: true")
    lines.append(f"search_rounds: {search_rounds}")
    lines.append(f"source_count: {source_count}")
    lines.append("---")
    return "\n".join(lines)


def _render_test_conditions(claims: list[dict], reference_map: dict[str, int] | None = None, lang: str = "en") -> str:
    claims_with_meta = []
    for idx, claim in enumerate(claims):
        meta = claim.get("source_metadata")
        if meta and isinstance(meta, dict):
            conditions = meta.get("test_conditions", "")
            test_date = meta.get("test_date", "")
            source_type = meta.get("source_type", "")
            if not (conditions or test_date or source_type):
                continue
            claims_with_meta.append((idx, claim, meta, conditions, test_date, source_type))

    if not claims_with_meta:
        return ""

    heading = _label("test_conditions", lang)
    col_claim = _label("claim", lang)
    col_conditions = _label("conditions", lang)
    col_date = _label("date", lang)
    col_source_type = _label("source_type", lang)
    lines = [f"\n**{heading}:**\n", f"| {col_claim} | {col_conditions} | {col_date} | {col_source_type} |", "|---|---|---|---|"]

    for idx, claim, meta, conditions, test_date, source_type in claims_with_meta:
        if reference_map is not None:
            claim_ref = _build_claim_ref(claim, reference_map)
        else:
            claim_ref = f"#{idx + 1}"
        lines.append(f"| {claim_ref} | {conditions} | {test_date} | {source_type} |")

    return "\n".join(lines)


def _build_claim_ref(claim: dict, reference_map: dict[str, int]) -> str:
    urls = claim.get("source_urls", [])
    if not urls:
        return ""
    first_url = urls[0]
    ref_num = reference_map.get(normalize_url(first_url))
    if ref_num is not None:
        return f"[{ref_num}]"
    return ""


def sections_to_markdown(analysis: dict, collected: list[dict] | None = None, lang: str = "en") -> str:
    parts = []
    collected = collected or []
    ref_map: dict[str, int] = {}
    goal_type = analysis.get("goal_type", "")
    compact = goal_type in _EXPLORATORY_GOAL_TYPES

    sv_map = _build_sv_map(analysis)
    verification_summary = _render_verification_summary(analysis, lang=lang)
    if verification_summary:
        parts.append(verification_summary)

    resolved_contents: dict[int, str] = {}
    for idx, sec in enumerate(analysis.get("sections", [])):
        content = sec.get("content", "")
        heading = f"## {sec.get('title', sec.get('id', ''))}"
        if content.startswith(heading):
            content = content[len(heading):].lstrip("\n")
        resolved_contents[idx] = _resolve_ref_markers(content, ref_map, sv_map)

    for idx, sec in enumerate(analysis.get("sections", [])):
        title = sec.get("title", sec.get("id", ""))
        parts.append(f"\n## {title}\n")
        parts.append(resolved_contents[idx])
        if not compact:
            claims = sec.get("claims", [])
            if claims:
                parts.append(f"\n**{_label('sources', lang)}:**\n")
                for claim in claims:
                    nums = []
                    for url in claim.get("source_urls", []):
                        norm = normalize_url(url)
                        num = ref_map.get(norm)
                        if num is not None:
                            nums.append(f"[{num}]")
                    nums_str = "".join(nums)
                    parts.append(f"- {claim.get('text', '')} {nums_str}")
                test_conditions = _render_test_conditions(claims, ref_map if ref_map else None, lang=lang)
                if test_conditions:
                    parts.append(test_conditions)
    parts.append(_render_references(ref_map, collected, lang=lang))
    return "\n".join(parts)


def generate_report(
    analysis_path: Path,
    scope_path: Path,
    review_status: str,
    search_rounds: int,
    source_count: int,
    report_language: str | None = None,
) -> str:
    analysis = read_json(analysis_path)
    scope = read_json(scope_path)
    topic = analysis.get("topic", scope.get("topic", "Untitled"))
    goal_type = analysis.get("goal_type", scope.get("goal_type", "other"))
    scope_desc = scope.get("scope_description", "")
    audience = scope.get("audience")
    if report_language is None:
        report_language = scope.get("report_language", "en")
    front = build_front_matter(
        topic,
        goal_type,
        scope_desc,
        review_status,
        search_rounds,
        source_count,
        audience,
        report_language,
    )
    # Try to load collected.json from same directory as analysis.json
    collected = []
    collected_path = analysis_path.parent / ARTIFACT_COLLECTED
    if collected_path.exists():
        collected = read_json(collected_path) or []
    body = sections_to_markdown(analysis, collected, lang=report_language or "en")
    raw = front + "\n" + body + "\n"
    return _post_process(raw)
