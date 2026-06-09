#!/usr/bin/env python3
"""Info-collector CLI: generate Markdown reports from analysis JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parent

from scripts.config import ResearchConfig, load_config, resolve_output_path, save_config
from scripts.models import (
    SECTION_IDS_DEEP,
    SECTION_IDS_STANDARD,
    AnalysisResult,
    Claim,
    Comparison,
    ConclusionData,
    ConfidenceAssessment,
    DataPoint,
    Section,
    Source,
    TimelineEvent,
)


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: lower scheme+host, strip trailing slash, sort params, remove www."""
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(url.lower())
    host = parsed.hostname or ""
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    params = parsed.params
    qsl = sorted(parse_qsl(parsed.query))
    query = urlencode(qsl) if qsl else ""
    return urlunparse(
        (parsed.scheme, f"{host}:{parsed.port}" if parsed.port else host, path, params, query, "")
    )


# ---------------------------------------------------------------------------
# Validation & parsing
# ---------------------------------------------------------------------------


_VALID_DEPTHS = {"standard", "deep"}
_VALID_SECTION_IDS = set(SECTION_IDS_STANDARD) | set(SECTION_IDS_DEEP)
_REQUIRED_SOURCE_FIELDS = {"url", "title", "content"}
_REQUIRED_SECTION_FIELDS = {"id", "title", "content"}


def validate_analysis(data: dict) -> list[str]:
    errors: list[str] = []
    if "topic" not in data:
        errors.append("Missing required field: topic")
    if "depth" not in data:
        errors.append("Missing required field: depth")
    elif data["depth"] not in _VALID_DEPTHS:
        errors.append(f"Invalid depth: {data['depth']!r}. Must be one of {sorted(_VALID_DEPTHS)}")
    if "sections" not in data or not isinstance(data["sections"], list):
        errors.append("Missing required field: sections (must be a list)")
    elif not data["sections"]:
        errors.append("sections list is empty")
    else:
        for i, s in enumerate(data["sections"]):
            if not isinstance(s, dict):
                errors.append(f"sections[{i}] must be an object")
                continue
            missing = _REQUIRED_SECTION_FIELDS - s.keys()
            if missing:
                errors.append(f"sections[{i}] missing required fields: {sorted(missing)}")
            elif s.get("id") not in _VALID_SECTION_IDS:
                errors.append(
                    f"sections[{i}].id={s['id']!r} is not a valid section ID. "
                    f"Must be one of: {sorted(_VALID_SECTION_IDS)}"
                )
    for field in ("sources", "data_points", "comparisons"):
        val = data.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"Field '{field}' must be a list if present")
    if isinstance(data.get("sources"), list):
        for i, s in enumerate(data["sources"]):
            if not isinstance(s, dict):
                continue
            missing = _REQUIRED_SOURCE_FIELDS - s.keys()
            if missing:
                errors.append(f"sources[{i}] missing required fields: {sorted(missing)}")
    return errors


def parse_analysis(data: dict) -> AnalysisResult:
    sources = [
        Source(
            url=s["url"],
            title=s.get("title", ""),
            source_type=s.get("source_type", "web"),
            source_lang=s.get("source_lang", "en"),
            content=s.get("content", ""),
            confidence=s.get("confidence", "medium"),
            quality=s.get("quality", "medium"),
            published_date=s.get("published_date"),
            duplicate_of=s.get("duplicate_of"),
            filter_note=s.get("filter_note", ""),
        )
        for s in data.get("sources", [])
    ]

    sections = [
        Section(
            id=s["id"],
            title=s["title"],
            content=s["content"],
            confidence=s.get("confidence", "medium"),
        )
        for s in data.get("sections", [])
    ]

    comparisons = [
        Comparison(
            dimension=c["dimension"],
            values=c.get("values", {}),
            winner=c.get("winner"),
        )
        for c in data.get("comparisons", [])
    ]

    data_points = [
        DataPoint(key=dp["key"], value=dp["value"], source_url=dp.get("source_url", ""))
        for dp in data.get("data_points", [])
    ]

    timelines = [
        TimelineEvent(date=t["date"], event=t["event"], source_url=t.get("source_url", ""))
        for t in data.get("timelines", [])
    ]

    claims = [
        Claim(
            statement=c["statement"],
            sources=c.get("sources", []),
            type=c.get("type", "fact"),
            confidence=c.get("confidence", "medium"),
            contradicted_by=c.get("contradicted_by", []),
            section_id=c.get("section_id", ""),
        )
        for c in data.get("claims", [])
    ]

    conclusion_raw = data.get("conclusion_data")
    conclusion_data = None
    if conclusion_raw and isinstance(conclusion_raw, dict):
        ca_list = [
            ConfidenceAssessment(
                conclusion=ca.get("conclusion", ""),
                confidence=ca.get("confidence", ""),
                evidence_strength=ca.get("evidence_strength", ""),
            )
            for ca in conclusion_raw.get("confidence_assessments", [])
        ]
        conclusion_data = ConclusionData(
            recommendation=conclusion_raw.get("recommendation", ""),
            reasoning=conclusion_raw.get("reasoning", ""),
            confidence_assessments=ca_list,
            action_items=conclusion_raw.get("action_items", []),
            open_questions=conclusion_raw.get("open_questions", []),
        )

    return AnalysisResult(
        topic=data["topic"],
        lang=data.get("lang", "zh"),
        depth=data.get("depth", "standard"),
        summary=data.get("summary", ""),
        sources=sources,
        sections=sections,
        data_points=data_points,
        comparisons=comparisons,
        contradictions=data.get("contradictions", []),
        timelines=timelines,
        claims=claims,
        conclusion_data=conclusion_data,
    )


# ---------------------------------------------------------------------------
# Workfiles management
# ---------------------------------------------------------------------------

_WORKFILES = {"scope.json", "collected.json", "analysis.json"}


def _clean_workfiles(skill_dir: Path) -> list[str]:
    """Remove workfiles (scope.json, collected.json, analysis.json).

    Returns list of filenames that were actually removed.
    """
    removed: list[str] = []
    for name in _WORKFILES:
        path = skill_dir / name
        if path.exists():
            path.unlink()
            removed.append(name)
    return removed


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> None:
    from scripts.reporter import Reporter

    input_path = Path(args.analysis_json)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if not args.no_validate:
        errors = validate_analysis(data)
        if errors:
            msg = "Validation failed: " + "; ".join(errors)
            print(msg, file=sys.stderr)
            print(msg)
            print("Run with --no-validate to skip validation.")
            sys.exit(1)

    analysis = parse_analysis(data)
    reporter = Reporter()
    markdown = reporter.generate(analysis, template=args.template, draft=args.draft)

    config = load_config(_SKILL_DIR) or ResearchConfig()
    if args.output_dir:
        config.output_dir = args.output_dir

    project_root = _find_project_root(_SKILL_DIR)
    output_path = resolve_output_path(analysis.topic, config, project_root)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Report saved to: {output_path}")


def cmd_filter(args: argparse.Namespace) -> None:
    """URL-normalize and deduplicate sources in collected.json."""
    collected_path = _SKILL_DIR / "collected.json"
    if not collected_path.exists():
        print("Error: collected.json not found. Run search+collect first.", file=sys.stderr)
        sys.exit(1)

    with open(collected_path, encoding="utf-8") as f:
        collected = json.load(f)

    sources = collected.get("sources", [])
    if not sources:
        print("No sources to filter.")
        return

    normalized_map: dict[str, list[int]] = {}
    for idx, src in enumerate(sources):
        norm = _normalize_url(src.get("url", ""))
        normalized_map.setdefault(norm, []).append(idx)

    duplicates_found = 0
    for norm, indices in normalized_map.items():
        if len(indices) > 1:
            keep = indices[0]
            for dup_idx in indices[1:]:
                sources[dup_idx]["duplicate_of"] = sources[keep].get("url", "")
                sources[dup_idx]["filter_note"] = (
                    f"Duplicate of {sources[keep].get('url', '')} (normalized: {norm})"
                )
                duplicates_found += 1

    collected["sources"] = sources
    with open(collected_path, "w", encoding="utf-8") as f:
        json.dump(collected, f, indent=2, ensure_ascii=False)

    total = len(sources)
    unique = sum(1 for s in sources if not s.get("duplicate_of"))
    print(
        f"Filter complete: {total} sources, {unique} unique, {duplicates_found} duplicates marked."
    )


def cmd_collect(args: argparse.Namespace) -> None:
    """Add sources to collected.json from a JSON file or URL list."""
    collected_path = _SKILL_DIR / "collected.json"
    if collected_path.exists():
        with open(collected_path, encoding="utf-8") as f:
            collected = json.load(f)
    else:
        collected = {"topic": "", "sources": [], "errors": []}

    if args.topic:
        collected["topic"] = args.topic

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        new_data = json.load(f)

    if isinstance(new_data, list):
        for item in new_data:
            if "url" in item:
                collected["sources"].append(item)
    elif isinstance(new_data, dict) and "sources" in new_data:
        collected["sources"].extend(new_data["sources"])
        if new_data.get("errors"):
            collected["errors"].extend(new_data["errors"])

    with open(collected_path, "w", encoding="utf-8") as f:
        json.dump(collected, f, indent=2, ensure_ascii=False)
    print(f"Collected {len(collected['sources'])} sources → {collected_path}")


def cmd_validate_scope(args: argparse.Namespace) -> None:
    from scripts.scope_validator import validate_scope

    scope_path = Path(args.scope_json)
    if not scope_path.exists():
        print(f"Error: file not found: {scope_path}", file=sys.stderr)
        sys.exit(1)

    with open(scope_path, encoding="utf-8") as f:
        data = json.load(f)

    errors = validate_scope(data)
    if errors:
        msg = "Scope validation failed: " + "; ".join(errors)
        print(msg, file=sys.stderr)
        print(msg)
        sys.exit(1)
    std = data.get("standardized", {})
    field_count = len(std)
    print(
        f"Scope validation passed. Found {field_count} standardized fields. Proceeding to Phase 2."
    )


def cmd_init_config(args: argparse.Namespace) -> None:
    output_dir = args.output_dir or "reports"
    lang = args.lang or "zh"
    config = ResearchConfig(
        output_dir=output_dir,
        lang=lang,
    )
    path = save_config(config, _SKILL_DIR)
    print(f"Config saved to: {path}")
    print(f"  output_dir: {config.output_dir}")
    print(f"  lang: {config.lang}")


def cmd_show_config(args: argparse.Namespace) -> None:
    config = load_config(_SKILL_DIR)
    if config is None:
        print("No config found. Run `research.py init-config` to create one.")
        return
    path = _SKILL_DIR / "config.json"
    print(f"Config loaded from: {path}")
    print(f"  output_dir: {config.output_dir}")
    print(f"  lang: {config.lang}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Info-collector: generate Markdown reports from analysis JSON."
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    gen = subparsers.add_parser("generate", help="Generate report from analysis JSON")
    gen.add_argument("analysis_json", help="Path to analysis.json")
    gen.add_argument(
        "--template",
        choices=["standard", "deep"],
        default="deep",
        help="Report template",
    )
    gen.add_argument("--output-dir", help="Override configured output directory")
    gen.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip JSON structure validation",
    )
    gen.add_argument(
        "--keep-files",
        action="store_true",
        help="No-op (kept for backward compatibility)",
    )
    gen.add_argument(
        "--draft",
        action="store_true",
        help="Mark report as draft in front matter",
    )
    gen.set_defaults(func=cmd_generate)

    init = subparsers.add_parser("init-config", help="Initialize config.json")
    init.add_argument(
        "--output-dir", default="reports", help="Report output directory (relative to project root)"
    )
    init.add_argument("--lang", default="zh", help="Default language")
    init.set_defaults(func=cmd_init_config)

    show = subparsers.add_parser("show-config", help="Show current config")
    show.set_defaults(func=cmd_show_config)

    vscope = subparsers.add_parser("validate-scope", help="Validate scope.json")
    vscope.add_argument("scope_json", help="Path to scope.json")
    vscope.set_defaults(func=cmd_validate_scope)

    coll = subparsers.add_parser("collect", help="Add sources to collected.json")
    coll.add_argument("input_file", help="JSON file with sources to add")
    coll.add_argument("--topic", help="Set or update the topic")
    coll.set_defaults(func=cmd_collect)

    filt = subparsers.add_parser("filter", help="Deduplicate sources in collected.json")
    filt.set_defaults(func=cmd_filter)

    clean = subparsers.add_parser("clean", help="Remove workfiles")
    clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


def _find_project_root(skill_dir: Path) -> Path:
    """Walk up from skill_dir to find project root (containing .git or AGENTS.md).

    Resolves symlinks and handles case-sensitive (Linux/macOS) and
    case-insensitive (Windows/macOS) filesystems by checking both
    ``.git`` and ``AGENTS.md`` with ``exists()`` which respects the
    underlying filesystem semantics.
    """
    resolved = skill_dir.resolve()
    for parent in resolved.parents:
        if (parent / ".git").exists() or (parent / "AGENTS.md").exists():
            return parent
    return Path.cwd().resolve()


def cmd_clean(args: argparse.Namespace) -> None:
    removed = _clean_workfiles(_SKILL_DIR)
    if removed:
        print(f"Cleaned up: {', '.join(removed)}")
    else:
        print("No workfiles found to clean.")


if __name__ == "__main__":
    main()
