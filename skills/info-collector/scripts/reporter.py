from __future__ import annotations

from datetime import date
from pathlib import Path

from .lib.utils import normalize_url, read_json

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
}


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
    collected_by_url = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            collected_by_url[normalize_url(url)] = item
    sorted_refs = sorted(reference_map.items(), key=lambda kv: kv[1])
    for norm_url, num in sorted_refs:
        item = collected_by_url.get(norm_url)
        title = item.get("title", norm_url) if item else norm_url
        parts.append(f"[{num}]: {norm_url} — {title}")
    return "\n".join(parts)


def build_front_matter(
    topic: str,
    goal_type: str,
    scope: str,
    quality: str,
    search_rounds: int,
    source_count: int,
    version: int = 1,
    parent: str | None = None,
    audience: str | None = None,
    report_language: str | None = None,
) -> str:
    lines = ["---"]
    lines.append(f"topic: {topic}")
    lines.append(f"goal_type: {goal_type}")
    lines.append(f"date: {date.today().isoformat()}")
    lines.append(f"version: {version}")
    if parent:
        lines.append(f"parent: {parent}")
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
            claims_with_meta.append((idx, claim, meta))

    if not claims_with_meta:
        return ""

    heading = _label("test_conditions", lang)
    col_claim = _label("claim", lang)
    col_conditions = _label("conditions", lang)
    col_date = _label("date", lang)
    col_source_type = _label("source_type", lang)
    lines = [f"\n**{heading}:**\n", f"| {col_claim} | {col_conditions} | {col_date} | {col_source_type} |", "|---|---|---|---|"]

    for idx, claim, meta in claims_with_meta:
        if reference_map is not None:
            claim_ref = _build_claim_ref(claim, reference_map)
        else:
            claim_ref = f"#{idx + 1}"
        conditions = meta.get("test_conditions", "")
        test_date = meta.get("test_date", "")
        source_type = meta.get("source_type", "")
        lines.append(f"| {claim_ref} | {conditions} | {test_date} | {source_type} |")

    return "\n".join(lines)


def _build_claim_ref(claim: dict, reference_map: dict[str, int]) -> str:
    urls = claim.get("source_urls", [])
    if not urls:
        return ""
    first_url = urls[0]
    ref_num = reference_map.get(first_url)
    if ref_num is not None:
        return f"[{ref_num}]"
    return ""


def sections_to_markdown(analysis: dict, collected: list[dict] | None = None, lang: str = "en") -> str:
    parts = []
    collected = collected or []
    ref_map = _build_reference_map(analysis, collected)
    for sec in analysis.get("sections", []):
        parts.append(f"\n## {sec.get('title', sec.get('id', ''))}\n")
        parts.append(sec.get("content", ""))
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
    version: int = 1,
    parent: str | None = None,
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
        version,
        parent,
        audience,
        report_language,
    )
    # Try to load collected.json from same directory as analysis.json
    collected = []
    collected_path = analysis_path.parent / "collected.json"
    if collected_path.exists():
        collected = read_json(collected_path) or []
    body = sections_to_markdown(analysis, collected, lang=report_language or "en")
    return front + "\n" + body + "\n"
