#!/usr/bin/env python3
"""learnings.py — cross-session engineering experience memory.

Notepad store lives under .omo/notepads/{scope}/{category}.md (append-only).
Subcommands: init, retrieve, capture, debrief.

Discipline:
- Never overwrites notepad files (append-only via `capture`).
- Never edits AGENTS.md. `debrief` only prints a PROPOSAL for the user to approve.
- Upcycle (promoting a pitfall to a rule) happens only when the USER asks,
  and only after the same pitfall recurs across tasks.

Self-contained — stdlib only, zero project imports.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path(".omo") / "notepads"
CATEGORIES = ["learnings", "decisions", "issues", "problems", "verification"]
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "was", "were",
    "when", "then", "into", "your", "will", "not", "but", "are", "been", "they",
    "them", "task", "done", "need", "use", "used", "has", "had", "you", "our",
}


def root() -> Path:
    env = os.environ.get("LEARNINGS_ROOT")
    return Path(env) if env else DEFAULT_ROOT


def default_scope() -> str:
    """Fallback scope when --scope is omitted: the current working directory's name.

    This makes `/learnings` robust even if the agent forgets to pass a scope — the
    notepad lands in the current project's bucket instead of erroring out.
    """
    return Path.cwd().name


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _display(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(root().resolve()))
    except ValueError:
        return str(p)


def cmd_init(args: argparse.Namespace) -> int:
    base = root() / args.scope
    base.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES:
        p = base / f"{cat}.md"
        if not p.exists():
            p.write_text(f"# {cat}\n\n", encoding="utf-8")
    print(f"initialized {base}")
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    base = root()
    if args.scope:
        base = base / args.scope
    files = sorted(glob.glob(str(base / "**" / "*.md"), recursive=True))
    blocks = []
    for f in files:
        text = Path(f).read_text(encoding="utf-8", errors="ignore")
        if args.category and Path(f).stem != args.category:
            continue
        if args.topic and args.topic.lower() not in text.lower():
            continue
        blocks.append(f"# {_display(Path(f))}\n\n{text.strip()}")
    print("\n\n---\n\n".join(blocks) if blocks else "(no notepad entries found)")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    base = root() / args.scope
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{args.category}.md"
    block = f"\n## [{_now()}] Task: {args.task_id}\n\n{args.content.strip()}\n"
    with p.open("a", encoding="utf-8") as fh:  # append-only, never truncates
        fh.write(block)
    print(f"appended to {p}")
    return 0


def _entries(scope: str | None):
    base = root()
    if scope:
        base = base / scope
    for f in sorted(glob.glob(str(base / "**" / "*.md"), recursive=True)):
        text = Path(f).read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"## \[(.*?)\] Task: (.*?)\n(.*?)(?=\n## \[|$)", text, re.S):
            yield {
                "file": _display(Path(f)),
                "category": Path(f).stem,
                "task_id": m.group(2).strip(),
                "body": m.group(3).strip(),
            }


def cmd_debrief(args: argparse.Namespace) -> int:
    entries = list(_entries(args.scope))
    print("# Debrief proposal — DO NOT auto-apply, user approval required\n")
    if not entries:
        print("(no entries to debrief)")
        return 0
    words: Counter[str] = Counter()
    for e in entries:
        for w in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", e["body"].lower()):
            words[w] += 1
    recurring = [(w, c) for w, c in words.most_common() if c >= 2 and w not in STOPWORDS]
    print(f"Scanned {len(entries)} entries across notepads.\n")
    if recurring:
        print("## Recurring keywords (candidates for a promoted rule):")
        for w, c in recurring[:20]:
            print(f"- `{w}` x{c}")
    print("\n## Next step")
    print("If a pitfall recurs across >=2 tasks, ASK the user to promote it to an AGENTS.md rule.")
    print("This script never writes AGENTS.md.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="learnings notepad memory")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("--scope", default=default_scope(),
                    help="notepad bucket; defaults to the current directory name")
    pi.set_defaults(func=cmd_init)

    pr = sub.add_parser("retrieve")
    pr.add_argument("--scope", default=default_scope(),
                   help="notepad bucket; defaults to the current directory name")
    pr.add_argument("--category")
    pr.add_argument("--topic")
    pr.set_defaults(func=cmd_retrieve)

    pc = sub.add_parser("capture")
    pc.add_argument("--scope", default=default_scope(),
                   help="notepad bucket; defaults to the current directory name")
    pc.add_argument("--category", required=True, choices=CATEGORIES)
    pc.add_argument("--task-id", required=True)
    pc.add_argument("--content", required=True)
    pc.set_defaults(func=cmd_capture)

    pd = sub.add_parser("debrief")
    pd.add_argument("--scope", default=default_scope(),
                   help="notepad bucket; defaults to the current directory name")
    pd.set_defaults(func=cmd_debrief)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
