"""CLI entry: proceed, gateway, report, source, clean subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

WORKDIR = Path(".workdir")


def cmd_proceed(args: argparse.Namespace) -> None:
    from .proceed import proceeds

    config_path = Path(__file__).parent.parent / "config.json"
    config = None
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    ok, errors = proceeds(WORKDIR, args.from_phase, args.to_phase, config)
    for err in errors:
        print(f"  {err}", file=sys.stderr)
    if ok:
        print(f"Gate passed: --from {args.from_phase} --to {args.to_phase}")
        sys.exit(0)
    else:
        print(f"Gate FAILED: --from {args.from_phase} --to {args.to_phase}", file=sys.stderr)
        sys.exit(1)


def cmd_gateway(args: argparse.Namespace) -> None:
    from .proceed import get_gateway_results

    results = get_gateway_results(WORKDIR)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{r.level:7s}] {r.name}: {status}  {r.message}")
    if any(not r.passed for r in results if r.level == "BLOCKER"):
        sys.exit(1)


def cmd_report(args: argparse.Namespace) -> None:
    from .reporter import generate_report

    config_path = Path(__file__).parent.parent / "config.json"
    config = None
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    analysis_path = WORKDIR / "analysis.json"
    scope_path = WORKDIR / "scope.json"
    if not analysis_path.exists():
        print("analysis.json not found", file=sys.stderr)
        sys.exit(1)
    if not scope_path.exists():
        print("scope.json not found", file=sys.stderr)
        sys.exit(1)

    quality = args.quality or _detect_quality()
    report = generate_report(
        analysis_path,
        scope_path,
        quality=quality,
        search_rounds=args.search_rounds or 1,
        source_count=args.source_count or _count_sources(),
        version=args.version or 1,
        parent=args.parent,
    )
    default_output = (config or {}).get("output_dir", "output/research")
    output_path = Path(args.output) if args.output else Path(default_output)
    output_path.mkdir(parents=True, exist_ok=True)
    topic = _read_topic(scope_path)
    safe_topic = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in topic.lower())
    filename = output_path / f"{safe_topic}_v{args.version or 1}.md"
    filename.write_text(report, encoding="utf-8")
    print(f"Report saved: {filename}")


def cmd_source(args: argparse.Namespace) -> None:
    from .lib.source_router import recommend_sources

    config_path = Path(__file__).parent.parent / "config.json"
    config = None
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

    result = recommend_sources(args.goal_type, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_clean(args: argparse.Namespace) -> None:
    import shutil

    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
        print(f"Removed {WORKDIR}")
    else:
        print(f"{WORKDIR} does not exist")


def _detect_quality() -> str:
    if (WORKDIR / "review_report.md").exists():
        return "passed"
    return "unreviewed"


def _count_sources() -> int:
    try:
        from .lib.utils import read_json

        collected = read_json(WORKDIR / "collected.json")
        return len(collected) if collected else 0
    except Exception:
        return 0


def _read_topic(scope_path: Path) -> str:
    try:
        from .lib.utils import read_json

        return cast(str, read_json(scope_path).get("topic", "untitled"))
    except Exception:
        return "untitled"


def main() -> None:
    parser = argparse.ArgumentParser(description="Info-Collector Skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_proceed = sub.add_parser("proceed", help="Run phase transition gate")
    p_proceed.add_argument("--from", dest="from_phase", required=True)
    p_proceed.add_argument("--to", dest="to_phase", required=True)
    p_proceed.set_defaults(func=cmd_proceed)

    p_gateway = sub.add_parser("gateway", help="Run gateway checks standalone")
    p_gateway.set_defaults(func=cmd_gateway)

    p_report = sub.add_parser("report", help="Generate report from analysis.json")
    p_report.add_argument("--quality", choices=["passed", "degraded", "unreviewed"])
    p_report.add_argument("--search-rounds", type=int)
    p_report.add_argument("--source-count", type=int)
    p_report.add_argument("--version", type=int, default=1)
    p_report.add_argument("--parent")
    p_report.add_argument("--output")
    p_report.set_defaults(func=cmd_report)

    p_source = sub.add_parser("source", help="Recommend sources for a goal_type")
    p_source.add_argument("goal_type")
    p_source.set_defaults(func=cmd_source)

    p_clean = sub.add_parser("clean", help="Remove .workdir")
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
