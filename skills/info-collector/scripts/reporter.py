from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .lib.utils import normalize_url, read_json

_TIER_LABELS: dict[str, str] = {
    "1": "★★★☆ Tier 1",
    "2": "★★☆☆ Tier 2",
    "3": "★☆☆☆ Tier 3",
    "4": "☆☆☆☆ Tier 4",
}

_LABELS: dict[tuple[str, str], str] = {
    ("sources", "en"): "Sources",
    ("sources", "zh"): "数据来源",
    ("references", "en"): "References",
    ("references", "zh"): "参考文献",
    ("test_conditions", "en"): "Test Conditions",
    ("test_conditions", "zh"): "测试环境",
    ("claim", "en"): "Claim",
    ("claim", "zh"): "声明",
    ("conditions", "en"): "Conditions",
    ("conditions", "zh"): "条件",
    ("date", "en"): "Date",
    ("date", "zh"): "日期",
    ("source_type", "en"): "Source Type",
    ("source_type", "zh"): "来源类型",
    ("methodology", "en"): "Methodology",
    ("methodology", "zh"): "方法论",
}


_EXPLORATORY_GOAL_TYPES = frozenset({"exploratory", "panoramic_understanding", "background_check", "other"})


def _label(key: str, lang: str) -> str:
    return _LABELS.get((key, lang), _LABELS.get((key, "en"), key))


def _build_reference_map(analysis: dict, collected: list[dict]) -> dict[str, int]:
    ref_map = {}
    next_num = 1
    for sec in analysis.get("sections", []):
        for claim in sec.get("claims", []):
            for url in claim.get("source_urls", []):
                norm = normalize_url(url)
                if norm not in ref_map:
                    ref_map[norm] = next_num
                    next_num += 1
    return ref_map


def _render_references(reference_map: dict[str, int], collected: list[dict], lang: str = "en") -> str:
    if not reference_map:
        return ""
    parts = [f"\n## {_label('references', lang)}\n"]
    parts.append('\n<a id="refs"></a>\n')
    collected_by_url = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            collected_by_url[normalize_url(url)] = item
    sorted_refs = sorted(reference_map.items(), key=lambda kv: kv[1])
    for norm_url, num in sorted_refs:
        item = collected_by_url.get(norm_url)
        title = item.get("title", norm_url) if item else norm_url
        tier_str = ""
        if item is not None:
            tier = item.get("source_tier")
            tier_key = str(tier) if tier is not None else None
            if tier_key and tier_key in _TIER_LABELS:
                tier_str = f" ({_TIER_LABELS[tier_key]})"
        clean_url = _clean_url(norm_url)
        if title and title != clean_url:
            parts.append(f"- **[{num}]** {title}{tier_str} — [{clean_url}]({clean_url})")
        else:
            parts.append(f"- **[{num}]** [{clean_url}]({clean_url})")
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
    ref_idx = markdown.rfind('## 参考文献')
    if ref_idx == -1:
        ref_idx = markdown.rfind('## References')
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
    quality: str,
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
    lines.append(f"quality: {quality}")
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
    ref_map = _build_reference_map(analysis, collected)
    goal_type = analysis.get("goal_type", "")
    compact = goal_type in _EXPLORATORY_GOAL_TYPES
    for sec in analysis.get("sections", []):
        title = sec.get("title", sec.get("id", ""))
        parts.append(f"\n## {title}\n")
        content = sec.get("content", "")
        heading = f"## {title}"
        if content.startswith(heading):
            content = content[len(heading) :].lstrip("\n")
        parts.append(content)
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
    quality: str,
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
        quality,
        search_rounds,
        source_count,
        audience,
        report_language,
    )
    # Try to load collected.json from same directory as analysis.json
    collected = []
    collected_path = analysis_path.parent / "collected.json"
    if collected_path.exists():
        collected = read_json(collected_path) or []
    body = sections_to_markdown(analysis, collected, lang=report_language or "en")
    raw = front + "\n" + body + "\n"
    return _post_process(raw)
