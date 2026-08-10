from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .lib.constants import _LABELS, _TIER_LABELS
from .lib.utils import build_collected_by_url, normalize_url, read_json


_REF_MARKER_RE = re.compile(r'\{\{ref:(.*?)\}\}')


def _label(key: str, lang: str) -> str:
    return _LABELS.get((key, lang), _LABELS.get((key, "en"), key))


def _render_source_refs(urls: list[str], ref_map: dict[str, int]) -> str:
    nums = []
    for url in urls:
        norm = normalize_url(url)
        num = ref_map.get(norm)
        if num is not None:
            nums.append(f"[{num}]")
    return "".join(nums)


def _resolve_ref_markers(content: str, ref_map: dict[str, int]) -> str:
    def _replacer(match: re.Match) -> str:
        url = match.group(1).strip()
        norm = normalize_url(url)
        if norm not in ref_map:
            ref_map[norm] = len(ref_map) + 1
        num = ref_map[norm]
        return f"[{num}]"
    return _REF_MARKER_RE.sub(_replacer, content)


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
        if item is not None:
            tier = item.get("source_tier")
            tier_key = str(tier) if tier is not None else None
            if tier_key and tier_key in _TIER_LABELS:
                tier_str = f" ({_TIER_LABELS[tier_key]})"
        clean_url = re.sub(r'^https?://preview-', 'https://', norm_url)
        if title and title != clean_url:
            parts.append(f"- [{num}] [{title}{tier_str}]({clean_url})")
        else:
            parts.append(f"- [{num}] [{clean_url}]({clean_url})")
    return "\n".join(parts)


def _render_verification_summary(analysis: dict, lang: str = "en") -> str:
    sv_counts: dict[str, int] = {}
    total = 0
    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            sv = claim.get("source_verification", "")
            if sv:
                sv_counts[sv] = sv_counts.get(sv, 0) + 1
                total += 1
    if total == 0:
        return ""
    lines = [
        "",
        "> **Verification note**: This report is a research starting point, not a citable authority.",
        "> \u2020 = data not found in cited source; \u2021 = data from indirect source.",
        "",
        "| Status | Count | Ratio |",
        "|--------|-------|-------|",
    ]
    for status, label in [("source_confirmed", "Confirmed"), ("source_indirect", "Indirect \u2021"), ("source_absent", "Absent \u2020")]:
        count = sv_counts.get(status, 0)
        ratio = f"{count/total:.0%}" if total else "0%"
        lines.append(f"| {label} | {count} | {ratio} |")
    return "\n".join(lines)


def _render_dq_summary(scope: dict, analysis: dict, lang: str = "en") -> str:
    decision_questions = scope.get("decision_questions", [])
    if not decision_questions:
        return ""
    answered_dqs: set[str] = set()
    for section in analysis.get("sections", []):
        for dq_id in section.get("decision_questions_answered", []):
            answered_dqs.add(dq_id)
    lines = [
        "",
        f"## {_label('decision_questions', lang)}",
        "",
    ]
    for dq in decision_questions:
        dq_id = dq.get("id", "")
        question = dq.get("question", "")
        marker = "\u2713" if dq_id in answered_dqs else "\u2717"
        lines.append(f"- {marker} {question}")
    return "\n".join(lines)


def build_front_matter(
    topic: str,
    goal_type: str,
    scope: str,
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
    lines.append(f"verification_required: true")
    lines.append(f"source_count: {source_count}")
    lines.append("---")
    return "\n".join(lines)


def sections_to_markdown(analysis: dict, collected: list[dict] | None = None, lang: str = "en") -> str:
    parts = []
    collected = collected or []
    ref_map: dict[str, int] = {}

    verification_summary = _render_verification_summary(analysis, lang=lang)
    if verification_summary:
        parts.append(verification_summary)

    resolved_contents: dict[str, str] = {}
    sorted_sections = sorted(analysis.get("sections", []), key=lambda s: s.get("order", 0))
    for sec in sorted_sections:
        content = sec.get("content", "")
        resolved_contents[sec.get("id", "")] = _resolve_ref_markers(content, ref_map)

    for sec in sorted_sections:
        title = sec.get("title", sec.get("id", ""))
        parts.append(f"\n## {title}\n")
        parts.append(resolved_contents[sec.get("id", "")])

        key_insights = sec.get("key_insights")
        if key_insights and isinstance(key_insights, list):
            parts.append(f"\n**{_label('key_insights', lang)}:**\n")
            for insight in key_insights:
                if isinstance(insight, dict):
                    text = insight.get("summary", "")
                    refs = _render_source_refs(insight.get("sources", []), ref_map)
                    parts.append(f"- {text} {refs}".rstrip())

        tensions = sec.get("tensions")
        if tensions and isinstance(tensions, list):
            parts.append(f"\n**{_label('tensions', lang)}:**\n")
            for tension in tensions:
                if isinstance(tension, dict):
                    desc = tension.get("summary", "")
                    refs = _render_source_refs(tension.get("sources", []), ref_map)
                    parts.append(f"- {desc} {refs}".rstrip())

        claims = sec.get("claims", [])
        if claims:
            parts.append(f"\n**Claims:**\n")
            for claim in claims:
                refs = _render_source_refs(claim.get("sources", []), ref_map)
                sv = claim.get("source_verification", "")
                sv_marker = ""
                if sv == "source_absent":
                    sv_marker = " \u2020"
                elif sv == "source_indirect":
                    sv_marker = " \u2021"
                parts.append(f"- {claim.get('summary', '')} {refs}{sv_marker}")

    parts.append(_render_references(ref_map, collected, lang=lang))
    return "\n".join(parts)


def generate_report(
    analysis_path: Path,
    scope_path: Path,
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

    collected_path = analysis_path.parent / "collected.json"
    collected = []
    if collected_path.exists():
        collected = read_json(collected_path) or []

    front = build_front_matter(
        topic, goal_type, scope_desc,
        source_count=len(collected),
        audience=audience,
        report_language=report_language,
    )
    body = sections_to_markdown(analysis, collected, lang=report_language or "en")

    dq_summary = _render_dq_summary(scope, analysis, lang=report_language or "en")
    if dq_summary:
        body += dq_summary

    raw = front + "\n" + body + "\n"
    return _post_process(raw)


def _post_process(markdown: str) -> str:
    markdown = re.sub(r'(?<!\\)\\n', '\n', markdown)
    markdown = re.sub(r'https?://preview-', 'https://', markdown)
    return markdown
