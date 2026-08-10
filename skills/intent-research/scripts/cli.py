from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .gates import run_all_checks
from .lib.utils import compute_url_hash, find_project_root, read_json, write_json, infer_tier_from_url, build_domain_tier_map
from .reporter import generate_report
from .verify import verify_claims


def _workdir(args) -> Path:
    if args.workdir:
        return Path(args.workdir).resolve()
    return find_project_root() / ".workdir"


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    if config_path.exists():
        return read_json(config_path)
    return {}


def cmd_scope_check(args) -> None:
    workdir = _workdir(args)
    if not workdir.exists():
        print(f"  .workdir not found: {workdir}")
        sys.exit(1)

    results = run_all_checks(workdir)
    has_blocker = False
    for r in results:
        prefix = r.prefix
        print(f"{prefix} {r.name}: {r.message}")
        if r.level == "BLOCKER":
            has_blocker = True

    if has_blocker:
        print("\nChecks FAILED")
        sys.exit(1)
    else:
        print("\nChecks passed")


def cmd_fetch(args) -> None:
    workdir = _workdir(args)
    config = _load_config()
    domain_tier_map = build_domain_tier_map(config)

    if args.from_stdin:
        raw = sys.stdin.read()
    elif getattr(args, "from_file", None):
        try:
            raw = Path(args.from_file).read_text(encoding="utf-8-sig")
        except OSError as e:
            print(f"  Cannot read file: {e}")
            sys.exit(1)
    else:
        print("  Use --from-stdin or --from-file")
        sys.exit(1)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON: {e}")
        sys.exit(1)
    if not isinstance(items, list):
        items = [items]

    collected_path = workdir / "collected.json"
    collected = []
    if collected_path.exists():
        collected = read_json(collected_path) or []

    sources_dir = workdir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    for item in items:
        url = item.get("url", "")
        content = item.get("content", "")
        tier = item.get("tier")
        title = item.get("title", "")

        if not url:
            continue

        if tier is None:
            tier = infer_tier_from_url(url, domain_tier_map)

        url_hash = compute_url_hash(url)
        source_file = f"sources/{url_hash}.md"
        (workdir / source_file).write_text(content, encoding="utf-8")

        collected_entry = {
            "url": url,
            "title": title or url,
            "source_tier": tier,
            "source_file": source_file,
            "direction": item.get("direction", "other"),
        }
        if item.get("snippet"):
            collected_entry["snippet"] = item["snippet"]
        if content:
            collected_entry["fetched_content"] = content[:200]
        if item.get("tier_override_reason"):
            collected_entry["tier_override_reason"] = item["tier_override_reason"]

        collected.append(collected_entry)
        print(f"  Fetched: {url[:80]}... ({len(content)} chars, tier={tier})")

    write_json(collected, collected_path)
    print(f"  Total sources: {len(collected)}")


def cmd_verify(args) -> None:
    workdir = _workdir(args)
    result = verify_claims(workdir)

    if "error" in result:
        print(f"  Verify failed: {result['error']}")
        sys.exit(1)

    total = result["total"]
    confirmed = result["source_confirmed"]
    absent = result["source_absent"]
    indirect = result["source_indirect"]

    print(f"  Verified {total} claims:")
    print(f"    Confirmed: {confirmed} ({confirmed/total:.0%})" if total else "    No claims")
    print(f"    Indirect \u2021: {indirect} ({indirect/total:.0%})" if total else "")
    print(f"    Absent \u2020: {absent} ({absent/total:.0%})" if total else "")
    print(f"  Results written back to analysis.json")


def cmd_report(args) -> None:
    workdir = _workdir(args)
    scope_path = workdir / "scope.json"
    analysis_path = workdir / "analysis.json"

    if not scope_path.exists():
        print("  scope.json not found")
        sys.exit(1)
    if not analysis_path.exists():
        print("  analysis.json not found")
        sys.exit(1)

    scope = read_json(scope_path)
    english_title = scope.get("english_title", scope.get("topic", "report")).replace(" ", "_").lower()
    safe_name = re.sub(r'[^\w\-]', '_', english_title)

    report = generate_report(analysis_path, scope_path)

    output_dir = Path(args.output_dir) if args.output_dir else find_project_root() / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{safe_name}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="intent-research CLI")
    parser.add_argument("--workdir", help="Path to .workdir/ (defaults to <project_root>/.workdir)")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("scope-check", help="Check scope + collected + analysis quality")

    fetch_p = subparsers.add_parser("fetch", help="Fetch sources from a JSON file or stdin")
    fetch_p.add_argument("--from-stdin", action="store_true", help="Read JSON array from stdin")
    fetch_p.add_argument("--from-file", help="Read JSON array from a local UTF-8 file")

    subparsers.add_parser("verify", help="Run deterministic source verification")

    report_p = subparsers.add_parser("report", help="Generate final report")
    report_p.add_argument("--output-dir", help="Output directory for report")

    args = parser.parse_args()

    if args.command == "scope-check":
        cmd_scope_check(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
