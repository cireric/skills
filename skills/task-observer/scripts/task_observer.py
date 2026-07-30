#!/usr/bin/env python3
"""task_observer.py — skill improvement observation log manager.

Adapted from rebelytics/one-skill-to-rule-them-all (CC BY 4.0).

Observation log lives under .omo/skill-observations/ by default.
Subcommands: init, append, archive, status, mark, next-review, stage.

Discipline:
- All mutations go through filelock for concurrency safety.
- append never overwrites (append-only).
- archive follows read-verify-merge-write-back protocol.
- mark updates only the Status line of a single entry.
- Agent never modifies log.md or last-review-date.txt directly.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from filelock import FileLock
except ImportError:
    print("ERROR: filelock not installed. Run: pip install filelock", file=sys.stderr)
    sys.exit(1)

DEFAULT_OBS_DIR = ".omo/skill-observations"
LOG_FILENAME = "log.md"
REVIEW_DATE_FILENAME = "last-review-date.txt"
ARCHIVE_DIRNAME = "archive"
CONFIG_FILENAME = "config.json"
PRINCIPLES_FILENAME = "cross-cutting-principles.md"
SKILL_UPDATES_DIRNAME = "skill-updates"
REVIEW_DATE_NEVER = "never"

_LOG_HEADER = (
    "# Skill Observation Log\n\n"
    "Observations captured during task-oriented work.\n\n"
    "**Status key:** OPEN = not yet actioned | "
    "ACTIONED (YYYY-MM-DD) = skill updated/created | "
    "DECLINED (YYYY-MM-DD) = user decided not to pursue — "
    "resolved statuses always carry their resolution date\n\n---\n"
)

_OBS_HEADER_RE = re.compile(r"^### Observation (\d+):", re.MULTILINE)
_STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.MULTILINE)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict:
    cfg_path = _skill_dir() / CONFIG_FILENAME
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _cfg(key: str, default):
    return _load_config().get(key, default)


def obs_dir() -> Path:
    env = os.environ.get("TASK_OBSERVER_DIR")
    if env:
        return Path(env)
    return Path(_cfg("observation_dir", DEFAULT_OBS_DIR))


def lock_path() -> Path:
    return obs_dir() / (LOG_FILENAME + ".lock")


def log_path() -> Path:
    return obs_dir() / LOG_FILENAME


def review_date_path() -> Path:
    return obs_dir() / REVIEW_DATE_FILENAME


def archive_dir() -> Path:
    return obs_dir() / ARCHIVE_DIRNAME


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return date.today().isoformat()


def _parse_entries(text: str) -> list[dict]:
    headers = list(_OBS_HEADER_RE.finditer(text))
    entries = []
    for i, m in enumerate(headers):
        num = int(m.group(1))
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[start:end]
        status_match = _STATUS_LINE_RE.search(body)
        status = status_match.group(1).strip() if status_match else "OPEN"
        entries.append({"num": num, "start": start, "end": end, "body": body, "status": status})
    return entries


def _highest_number(text: str) -> int:
    nums = [int(m.group(1)) for m in _OBS_HEADER_RE.finditer(text)]
    return max(nums) if nums else 0


def _count_headers(text: str) -> int:
    return len(_OBS_HEADER_RE.findall(text))


def _is_resolved(status: str) -> bool:
    return status.startswith("ACTIONED") or status.startswith("DECLINED")


def _resolved_date(status: str) -> str | None:
    m = _DATE_RE.search(status)
    return m.group(0) if m else None


def _format_observation(num: int, session_context: str, skill: str,
                        obs_type: str, phase: str,
                        issue: str, improvement: str, principle: str,
                        reference_file: str | None = None) -> str:
    today = _today()
    ref_line = f"\n**Reference file:** {reference_file}" if reference_file else ""
    return (
        f"\n### Observation {num}: {issue.split(chr(10))[0][:80]}\n\n"
        f"**Status:** OPEN\n"
        f"**Date:** {today}\n"
        f"**Session context:** {session_context}\n"
        f"**Skill:** {skill}\n"
        f"**Type:** {obs_type}\n"
        f"**Phase/Area:** {phase}\n\n"
        f"**Issue:** {issue}\n\n"
        f"**Suggested improvement:** {improvement}\n\n"
        f"**Principle:** {principle}\n"
        f"{ref_line}"
    )


def cmd_init(args: argparse.Namespace) -> int:
    d = obs_dir()
    d.mkdir(parents=True, exist_ok=True)
    archive_dir().mkdir(parents=True, exist_ok=True)

    lp = log_path()
    if not lp.exists():
        lp.write_text(_LOG_HEADER, encoding="utf-8")

    rdp = review_date_path()
    if not rdp.exists():
        rdp.write_text(REVIEW_DATE_NEVER, encoding="utf-8")

    cp = _skill_dir() / CONFIG_FILENAME
    if not cp.exists():
        default_cfg = {
            "observation_dir": DEFAULT_OBS_DIR,
            "review_interval_days": 7,
            "default_type": "internal",
            "lock_timeout_seconds": 5,
            "archive_after_days": 0,
        }
        cp.write_text(json.dumps(default_cfg, indent=2) + "\n", encoding="utf-8")

    principles = d.parent / PRINCIPLES_FILENAME
    if not principles.exists():
        principles.write_text(
            "# Cross-Cutting Principles\n\n"
            "Principles that apply across multiple skills, discovered during observation.\n\n---\n",
            encoding="utf-8",
        )

    print(f"initialized {d}")
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    timeout = _cfg("lock_timeout_seconds", 5)
    obs_type = args.type or _cfg("default_type", "internal")
    lp = log_path()

    if not lp.exists():
        print("ERROR: log.md not found. Run init first.", file=sys.stderr)
        return 1

    lock = FileLock(str(lock_path()), timeout=timeout)
    try:
        with lock:
            text = lp.read_text(encoding="utf-8")
            proposed = _highest_number(text) + 1
            existing_nums = {int(m.group(1)) for m in _OBS_HEADER_RE.finditer(text)}
            while proposed in existing_nums:
                proposed += 1

            entry = _format_observation(
                proposed, args.session_context, args.skill,
                obs_type, args.phase, args.issue,
                args.improvement, args.principle,
                getattr(args, "reference_file", None),
            )
            pre_count = _count_headers(text)
            with lp.open("a", encoding="utf-8") as f:
                f.write(entry)
            post_text = lp.read_text(encoding="utf-8")
            post_count = _count_headers(post_text)

            if post_count != pre_count + 1:
                print(f"WARNING: header count mismatch after append: "
                      f"pre={pre_count} post={post_count} expected={pre_count + 1}",
                      file=sys.stderr)

            occ = len(_OBS_HEADER_RE.findall(post_text))
            proposed_pattern = f"### Observation {proposed}:"
            occ_proposed = post_text.count(proposed_pattern)
            if occ_proposed > 1:
                print(f"WARNING: collision detected on observation {proposed} "
                      f"({occ_proposed} occurrences)", file=sys.stderr)

            print(f"appended observation {proposed}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    timeout = _cfg("lock_timeout_seconds", 5)
    lp = log_path()

    if not lp.exists():
        print("ERROR: log.md not found.", file=sys.stderr)
        return 1

    status_value = f"{args.new_status} ({_today()}) — {args.reason}"
    lock = FileLock(str(lock_path()), timeout=timeout)
    try:
        with lock:
            text = lp.read_text(encoding="utf-8")
            pre_count = _count_headers(text)
            backup = obs_dir() / f"{LOG_FILENAME}.bak-{_today()}"
            shutil.copy2(str(lp), str(backup))

            entries = _parse_entries(text)
            target = None
            for e in entries:
                if e["num"] == args.number:
                    target = e
                    break

            if target is None:
                print(f"ERROR: observation {args.number} not found.", file=sys.stderr)
                return 1

            lines = text.splitlines(True)
            header_line_idx = None
            for i, line in enumerate(lines):
                if re.match(rf"^### Observation {args.number}:", line):
                    header_line_idx = i
                    break

            if header_line_idx is None:
                print(f"ERROR: header line for observation {args.number} not found.", file=sys.stderr)
                return 1

            search_end = len(lines)
            for i in range(header_line_idx + 1, len(lines)):
                if re.match(r"^### Observation \d+:", lines[i]):
                    search_end = i
                    break

            replaced = False
            for i in range(header_line_idx, search_end):
                m = re.match(r"^(\*\*Status:\*\*)\s+.+$", lines[i])
                if m:
                    lines[i] = f"{m.group(1)} {status_value}\n"
                    replaced = True
                    break

            if not replaced:
                insert_idx = header_line_idx + 1
                lines.insert(insert_idx, f"**Status:** {status_value}\n")

            new_text = "".join(lines)
            post_count = _count_headers(new_text)
            if post_count != pre_count:
                print(f"ERROR: header count changed during mark: "
                      f"pre={pre_count} post={post_count}. "
                      f"Backup at {backup}", file=sys.stderr)
                return 1

            lp.write_text(new_text, encoding="utf-8")
            print(f"marked observation {args.number} as {status_value}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    timeout = _cfg("lock_timeout_seconds", 5)
    archive_after = _cfg("archive_after_days", 0)
    lp = log_path()

    if not lp.exists():
        print("ERROR: log.md not found.", file=sys.stderr)
        return 1

    today = _today()
    lock = FileLock(str(lock_path()), timeout=timeout)
    try:
        with lock:
            text = lp.read_text(encoding="utf-8")
            pre_count = _count_headers(text)
            backup = obs_dir() / f"{LOG_FILENAME}.bak-{today}"
            shutil.copy2(str(lp), str(backup))

            entries = _parse_entries(text)
            to_archive = []
            to_keep = []
            for e in entries:
                if _is_resolved(e["status"]):
                    rd = _resolved_date(e["status"])
                    if rd and rd < today:
                        to_archive.append(e)
                        continue
                to_keep.append(e)

            if not to_archive:
                print("no entries to archive")
                return 0

            archive_text = _LOG_HEADER
            for e in to_archive:
                archive_text += e["body"]

            ad = archive_dir()
            ad.mkdir(parents=True, exist_ok=True)
            archive_file = ad / f"{LOG_FILENAME.replace('.md', '')}-{today}.md"
            if archive_file.exists():
                existing = archive_file.read_text(encoding="utf-8")
                archive_text = existing + "\n" + archive_text[len(_LOG_HEADER):]
            archive_file.write_text(archive_text, encoding="utf-8")

            new_text = _LOG_HEADER
            for e in to_keep:
                new_text += e["body"]
            lp.write_text(new_text, encoding="utf-8")

            post_count = _count_headers(new_text)
            expected = pre_count - len(to_archive)
            if post_count != expected:
                print(f"ERROR: header count mismatch after archive: "
                      f"pre={pre_count} post={post_count} expected={expected}. "
                      f"Backup at {backup}", file=sys.stderr)
                return 1

            print(f"archived {len(to_archive)} entries to {archive_file}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    review_interval = _cfg("review_interval_days", 7)
    lp = log_path()

    if not lp.exists():
        print("log.md not found. Run init first.")
        return 0

    text = lp.read_text(encoding="utf-8")
    entries = _parse_entries(text)

    open_count = 0
    actioned_count = 0
    declined_count = 0
    no_status_count = 0

    for e in entries:
        s = e["status"]
        if s == "OPEN":
            open_count += 1
        elif s.startswith("ACTIONED"):
            actioned_count += 1
        elif s.startswith("DECLINED"):
            declined_count += 1
        else:
            no_status_count += 1

    rdp = review_date_path()
    review_date = rdp.read_text(encoding="utf-8").strip() if rdp.exists() else "unknown"

    review_due = False
    if review_date == REVIEW_DATE_NEVER:
        review_due = open_count > 0
    else:
        try:
            last = date.fromisoformat(review_date)
            if (date.today() - last).days >= review_interval and open_count > 0:
                review_due = True
        except ValueError:
            review_due = open_count > 0

    print(f"Observations: {len(entries)} total")
    print(f"  OPEN: {open_count}  ACTIONED: {actioned_count}  "
          f"DECLINED: {declined_count}  NO STATUS: {no_status_count}")
    print(f"Last review: {review_date}")
    if review_due:
        print(f"REVIEW DUE — {review_interval} days since last review with {open_count} open observations")
    else:
        print("No review due")
    return 0


def cmd_next_review(args: argparse.Namespace) -> int:
    rdp = review_date_path()
    obs_dir().mkdir(parents=True, exist_ok=True)
    rdp.write_text(_today(), encoding="utf-8")
    print(f"set last-review-date to {_today()}")
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    src = Path(args.skill_path)
    if not src.exists():
        print(f"ERROR: {args.skill_path} not found.", file=sys.stderr)
        return 1

    dest_base = obs_dir().parent / SKILL_UPDATES_DIRNAME / _today() / src.name
    dest_base.mkdir(parents=True, exist_ok=True)

    shutil.copytree(str(src), str(dest_base), dirs_exist_ok=True)

    if (dest_base / "SKILL.md").exists():
        original = (src / "SKILL.md").read_text(encoding="utf-8")
        staged = (dest_base / "SKILL.md").read_text(encoding="utf-8")
        diff_lines = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            staged.splitlines(keepends=True),
            fromfile=f"live/{src.name}/SKILL.md",
            tofile=f"staged/{src.name}/SKILL.md",
        ))
        if diff_lines:
            print("".join(diff_lines))
        else:
            print("(no differences between live and staged)")
    else:
        print(f"WARNING: staged copy has no SKILL.md", file=sys.stderr)

    print(f"staged to {dest_base}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="task-observer skill improvement log")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="initialize observation log directory")
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append", help="append a new observation")
    pa.add_argument("--session-context", required=True)
    pa.add_argument("--skill", required=True)
    pa.add_argument("--type", default=None)
    pa.add_argument("--phase", default="unspecified")
    pa.add_argument("--issue", required=True)
    pa.add_argument("--improvement", required=True)
    pa.add_argument("--principle", required=True)
    pa.add_argument("--reference-file", default=None,
                    help="optional path to saved context file")
    pa.set_defaults(func=cmd_append)

    pm = sub.add_parser("mark", help="update status of an observation")
    pm.add_argument("--number", type=int, required=True)
    pm.add_argument("--new-status", required=True, choices=["ACTIONED", "DECLINED"])
    pm.add_argument("--reason", required=True)
    pm.set_defaults(func=cmd_mark)

    parc = sub.add_parser("archive", help="archive resolved observations")
    parc.set_defaults(func=cmd_archive)

    ps = sub.add_parser("status", help="show observation statistics")
    ps.set_defaults(func=cmd_status)

    pnr = sub.add_parser("next-review", help="record today as last review date")
    pnr.set_defaults(func=cmd_next_review)

    pst = sub.add_parser("stage", help="stage a skill file for review")
    pst.add_argument("skill_path", help="path to skill directory")
    pst.set_defaults(func=cmd_stage)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
