"""batch_fetch: Process multiple fetched URLs in one CLI call.

Reads collected.json, accepts batch content via --from-stdin, writes source
files, and updates collected.json. Eliminates the agent's opportunity to
summarize instead of storing full text (ADR 0041).
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from .fetcher import Fetcher
from .lib.constants import ARTIFACT_COLLECTED, _SOURCES_DIR
from .lib.utils import compute_url_hash


def cmd_batch_fetch(args: "argparse.Namespace") -> None:  # noqa: F821
    """Entry point for `cli batch-fetch` subcommand."""
    workdir = Path(args.workdir) if args.workdir else _default_workdir()
    config = _load_config(workdir)

    collected_path = workdir / ARTIFACT_COLLECTED
    if not collected_path.exists():
        print("Error: collected.json not found", file=sys.stderr)
        sys.exit(1)

    try:
        collected = json.loads(collected_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading collected.json: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(collected, list):
        print("Error: collected.json must be a JSON array", file=sys.stderr)
        sys.exit(1)

    fetcher = Fetcher(workdir, config)

    if args.from_stdin:
        raw = sys.stdin.read()
        results = _process_batch_stdin(collected, raw, fetcher, workdir, args)
    elif args.pending:
        results = _report_pending(collected, workdir)
    else:
        print("Error: specify --from-stdin or --pending", file=sys.stderr)
        sys.exit(1)

    if args.from_stdin and results is not None:
        _update_collected(collected, results, collected_path)
        print(json.dumps({"processed": len(results)}, ensure_ascii=False))


def _default_workdir() -> Path:
    from .lib.utils import find_project_root
    return find_project_root() / ".workdir"


def _load_config(workdir: Path) -> dict | None:
    from .lib.utils import config_path
    cp = config_path()
    if cp.exists():
        with open(cp, encoding="utf-8") as f:
            return json.load(f)
    return None


def _report_pending(collected: list, workdir: Path) -> None:
    """Print URLs that still need fetching, grouped by tier."""
    pending: dict[int, list[dict]] = {}
    for entry in collected:
        if entry.get("fetch_failed", False):
            continue
        sf = entry.get("source_file")
        if sf:
            source_path = workdir / sf
            if source_path.exists() and source_path.stat().st_size > 0:
                continue
        tier = entry.get("source_tier", 3)
        pending.setdefault(tier, []).append({
            "url": entry.get("url", ""),
            "title": entry.get("title", ""),
        })

    if not pending:
        print("All entries have source files. No pending fetches.")
        return

    for tier in sorted(pending):
        entries = pending[tier]
        print(f"\nTier {tier} ({len(entries)} pending):")
        for e in entries:
            print(f"  {e['url']}  — {e['title']}")

    print(f"\nTotal: {sum(len(v) for v in pending.values())} URLs need fetching.")
    print("Usage: exa_web_fetch_exa(urls) → pipe result to: cli batch-fetch --from-stdin")


def _process_batch_stdin(
    collected: list,
    raw: str,
    fetcher: Fetcher,
    workdir: Path,
    args: "argparse.Namespace",  # noqa: F821
) -> list[dict] | None:
    """Parse batch input, save each URL's content, return results."""
    batch = _parse_batch_input(raw)
    if not batch:
        print("Error: no parseable content in stdin input", file=sys.stderr)
        sys.exit(1)

    url_to_entry = {}
    for entry in collected:
        url = entry.get("url", "")
        if url:
            url_to_entry[url] = entry

    results = []
    for item in batch:
        url = item["url"]
        content = item["content"]
        tier = item.get("tier")

        entry = url_to_entry.get(url)
        if not entry:
            print(f"  [WARN] URL not in collected.json, skipping: {url}", file=sys.stderr)
            continue

        if tier is None:
            tier = entry.get("source_tier") or fetcher.infer_tier(url) or 3

        result = fetcher.save_piped(url, content, tier=tier)
        result_dict = asdict(result)
        results.append(result_dict)

        status = "OK" if not result.fetch_failed else "FAILED"
        char_info = f"{result.char_count} chars" if not result.fetch_failed else ""
        insuf = " (insufficient)" if result.content_insufficient and not result.fetch_failed else ""
        print(f"  [{status}] {url} → {result.source_file} ({char_info}{insuf})", file=sys.stderr)

    return results


def _parse_batch_input(raw: str) -> list[dict]:
    """Parse stdin input into list of {url, content, tier?}.

    Accepts two formats:
    1. JSON array: [{"url": "...", "content": "...", "tier": N}, ...]
    2. JSON object with "items" key: {"items": [...]}
    3. Single JSON object: {"url": "...", "content": "..."}
    """
    stripped = raw.strip()
    if not stripped:
        return []

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        print("Error: stdin is not valid JSON. Expected array of {url, content, tier?}", file=sys.stderr)
        sys.exit(1)

    if isinstance(data, dict):
        if "items" in data:
            items = data["items"]
        elif "url" in data and "content" in data:
            items = [data]
        else:
            return []
    elif isinstance(data, list):
        items = data
    else:
        return []

    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        content = item.get("content", "")
        if url and content:
            valid.append({
                "url": url,
                "content": content,
                "tier": item.get("tier"),
            })
    return valid


def _update_collected(
    collected: list,
    results: list[dict],
    collected_path: Path,
) -> None:
    """Update collected.json entries with fetch results."""
    url_to_result = {}
    for r in results:
        url_to_result[r["url"]] = r

    updated = False
    for entry in collected:
        url = entry.get("url", "")
        result = url_to_result.get(url)
        if not result:
            continue

        if result.get("fetch_failed", False):
            entry["fetch_failed"] = True
            entry["source_file"] = None
            entry["fetched_content"] = ""
            updated = True
            continue

        entry["source_file"] = result.get("source_file")
        entry["fetched_content"] = result.get("fetched_content", "")
        if result.get("source_tier") is not None:
            entry["source_tier"] = result["source_tier"]
        entry["fetch_failed"] = False
        updated = True

    if updated:
        collected_path.write_text(
            json.dumps(collected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
