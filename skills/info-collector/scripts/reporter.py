"""analysis.json -> Markdown report with YAML front matter."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .lib.utils import read_json


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
    lines.append(f"scope: {scope}")
    lines.append(f"quality: {quality}")
    lines.append(f"search_rounds: {search_rounds}")
    lines.append(f"source_count: {source_count}")
    lines.append("---")
    return "\n".join(lines)


def sections_to_markdown(analysis: dict) -> str:
    parts = []
    for sec in analysis.get("sections", []):
        parts.append(f"\n## {sec.get('title', sec.get('id', ''))}\n")
        parts.append(sec.get("content", ""))
        claims = sec.get("claims", [])
        if claims:
            parts.append("\n**Sources:**\n")
            for claim in claims:
                urls = ", ".join(claim.get("source_urls", []))
                parts.append(f"- {claim.get('text', '')} ({urls})")
    return "\n".join(parts)


def generate_report(
    analysis_path: Path,
    scope_path: Path,
    quality: str,
    search_rounds: int,
    source_count: int,
    version: int = 1,
    parent: str | None = None,
) -> str:
    analysis = read_json(analysis_path)
    scope = read_json(scope_path)
    topic = analysis.get("topic", scope.get("topic", "Untitled"))
    goal_type = analysis.get("goal_type", scope.get("goal_type", "other"))
    scope_desc = scope.get("scope_description", "")
    audience = scope.get("audience")
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
    )
    body = sections_to_markdown(analysis)
    return front + "\n" + body + "\n"
