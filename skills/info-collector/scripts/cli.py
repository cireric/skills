"""CLI entry: proceed, gateway, report, source, clean subcommands."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import cast

from .lib.exceptions import InfoCollectorError
from .lib.utils import _find_project_root

WORKDIR = _find_project_root() / ".workdir"
_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def _load_config() -> dict | None:
    """Load config.json from the skill directory. Returns None if missing."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def cmd_proceed(args: argparse.Namespace) -> None:
    from .proceed import proceeds

    config = _load_config()
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

    config = _load_config()

    analysis_path = WORKDIR / "analysis.json"
    scope_path = WORKDIR / "scope.json"
    if not analysis_path.exists():
        print("analysis.json not found", file=sys.stderr)
        sys.exit(1)
    if not scope_path.exists():
        print("scope.json not found", file=sys.stderr)
        sys.exit(1)

    from .lib.utils import read_json

    quality = args.quality or _detect_quality()
    scope_data = read_json(scope_path) if scope_path.exists() else {}
    report_language = scope_data.get("report_language")
    if not report_language:
        report_language = (config or {}).get("default_report_language", "zh")
    report = generate_report(
        analysis_path,
        scope_path,
        quality=quality,
        search_rounds=args.search_rounds or 1,
        source_count=args.source_count or _count_sources(),
        report_language=report_language,
    )
    default_output = (config or {}).get("output_dir", "./reports/")
    output_path = Path(args.output) if args.output else _find_project_root() / default_output
    output_path.mkdir(parents=True, exist_ok=True)
    filename = _build_report_filename(scope_data, output_path)
    filename.write_text(report, encoding="utf-8")
    print(f"Report saved: {filename}")


def cmd_source(args: argparse.Namespace) -> None:
    from .lib.source_router import recommend_sources

    config = _load_config()
    result = recommend_sources(args.goal_type, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_clean(args: argparse.Namespace) -> None:
    import shutil

    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
        print(f"Removed {WORKDIR}")
    else:
        print(f"{WORKDIR} does not exist")


_PHASE_ARTIFACTS: dict[str, list[str]] = {
    "scope": ["scope.json", "search_plan.json", "collected.json", "analysis.json", "review_report.md", "pipeline_state.json"],
    "search": ["collected.json", "analysis.json", "review_report.md"],
    "analysis": ["analysis.json", "review_report.md"],
    "review": ["review_report.md"],
}


def cmd_reset(args: argparse.Namespace) -> None:
    phase = args.phase
    if phase not in _PHASE_ARTIFACTS:
        print(f"Invalid phase: {phase}. Must be one of: {', '.join(_PHASE_ARTIFACTS)}", file=sys.stderr)
        sys.exit(1)
    removed = []
    for name in _PHASE_ARTIFACTS[phase]:
        path = WORKDIR / name
        if path.exists():
            path.unlink()
            removed.append(name)
    from .proceed import detect_current_phase, _write_phase_state
    actual_phase = detect_current_phase(WORKDIR)
    state_path = WORKDIR / "pipeline_state.json"
    if state_path.exists():
        state_path.unlink()
        removed.append("pipeline_state.json")
    if actual_phase != "pre_scope":
        _write_phase_state(WORKDIR, actual_phase)
    if removed:
        print(f"Reset from phase '{phase}': removed {', '.join(removed)}")
    else:
        print(f"Reset from phase '{phase}': nothing to remove")


def _detect_quality() -> str:
    review_path = WORKDIR / "review_report.md"
    if not review_path.exists():
        return "unreviewed"
    try:
        content = review_path.read_text(encoding="utf-8")
    except OSError:
        return "unreviewed"
    # Find "## Overall Verdict" section and parse the verdict
    match = re.search(r"##\s*Overall\s+Verdict\s*\n\s*\*\*(pass|pass_with_issues|fail)\*\*", content, re.IGNORECASE)
    if not match:
        verdict_section = re.search(r"##\s*Overall\s+Verdict\s*\n(.{0,200})", content, re.IGNORECASE | re.DOTALL)
        if verdict_section:
            section_text = verdict_section.group(1).lower()
            if re.search(r'\bpass_with_issues\b', section_text):
                return "degraded"
            if re.search(r'\bfail\b', section_text):
                print("Review verdict is FAIL — fix issues before generating report", file=sys.stderr)
                sys.exit(1)
            if re.search(r'\bpass\b', section_text):
                return "passed"
        return "degraded"
    verdict = match.group(1).lower()
    if verdict == "pass":
        return "passed"
    elif verdict == "pass_with_issues":
        return "degraded"
    elif verdict == "fail":
        # Should not generate report for failed review
        print("Review verdict is FAIL — fix issues before generating report", file=sys.stderr)
        sys.exit(1)
    return "degraded"  # unreachable but safe


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


def _build_report_filename(scope_data: dict, output_path: Path) -> Path:
    english_title = scope_data.get("english_title")
    if english_title:
        raw = english_title
    else:
        raw = scope_data.get("topic", "untitled")
    safe_name = "".join(c if c.isascii() and (c.isalnum() or c in ("-", "_")) else "_" for c in raw.lower())
    import re as _re
    safe_name = _re.sub(r"_+", "_", safe_name).strip("_")
    if not safe_name:
        safe_name = "untitled"
    base_path = output_path / f"{safe_name}.md"
    if not base_path.exists():
        return base_path
    report_date = scope_data.get("report_date")
    if not report_date:
        from datetime import date as _date
        report_date = _date.today().isoformat()
    return output_path / f"{safe_name}_{report_date}.md"


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
    p_report.add_argument("--output")
    p_report.set_defaults(func=cmd_report)

    p_source = sub.add_parser("source", help="Recommend sources for a goal_type")
    p_source.add_argument("goal_type")
    p_source.set_defaults(func=cmd_source)

    p_clean = sub.add_parser("clean", help="Remove .workdir")
    p_clean.set_defaults(func=cmd_clean)

    p_reset = sub.add_parser("reset", help="Reset pipeline to a given phase")
    p_reset.add_argument("--phase", required=True, help="Phase to reset to (scope, search, analysis, review)")
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    try:
        args.func(args)
    except InfoCollectorError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
