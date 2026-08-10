"""Tests for task_observer.py — covers init, append, mark, archive, status, stage."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_DIR / "scripts"))


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Redirect observation dir to tmp_path for isolation."""
    obs_root = tmp_path / ".omo"
    monkeypatch.setenv("TASK_OBSERVER_DIR", str(obs_root / "skill-observations"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(_SKILL_DIR / "scripts"))
    import task_observer
    monkeypatch.setattr(task_observer, "_skill_dir", lambda: _SKILL_DIR)
    return task_observer


def test_init_creates_structure(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    assert to.log_path().exists()
    assert to.review_date_path().exists()
    assert to.archive_dir().exists()
    assert to.review_date_path().read_text(encoding="utf-8").strip() == "never"
    assert "Skill Observation Log" in to.log_path().read_text(encoding="utf-8")


def test_init_creates_cross_cutting_principles(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    principles = to.obs_dir().parent / "cross-cutting-principles.md"
    assert principles.exists()
    assert "Cross-Cutting Principles" in principles.read_text(encoding="utf-8")


def test_append_type_falls_back_to_config(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "append",
        "--session-context", "testing type fallback",
        "--skill", "tdd",
        "--issue", "test issue",
        "--improvement", "test fix",
        "--principle", "test p",
    ])
    result = to.cmd_append(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "**Type:** internal" in log


def test_append_type_overrides_config(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "append",
        "--session-context", "testing type override",
        "--skill", "tdd",
        "--type", "open-source",
        "--issue", "test issue",
        "--improvement", "test fix",
        "--principle", "test p",
    ])
    result = to.cmd_append(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "**Type:** open-source" in log


def test_append_creates_first_observation(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "append",
        "--session-context", "testing feature X",
        "--skill", "tdd",
        "--type", "internal",
        "--phase", "trigger",
        "--issue", "Red step description is ambiguous",
        "--improvement", "Add explicit example of red state",
        "--principle", "Ambiguity in procedural steps compounds across sessions",
    ])
    result = to.cmd_append(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "### Observation 1:" in log
    assert "**Status:** OPEN" in log
    assert "**Skill:** tdd" in log
    assert "**Issue:** Red step description is ambiguous" in log


def test_append_increments_number(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    for i in range(3):
        args = to.build_parser().parse_args([
            "append",
            "--session-context", f"task {i}",
            "--skill", "tdd",
            "--issue", f"issue {i}",
            "--improvement", f"fix {i}",
            "--principle", f"principle {i}",
        ])
        to.cmd_append(args)

    log = to.log_path().read_text(encoding="utf-8")
    assert "### Observation 1:" in log
    assert "### Observation 2:" in log
    assert "### Observation 3:" in log


def test_mark_changes_status(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "test issue", "--improvement", "test fix", "--principle", "test p",
    ]))

    args = to.build_parser().parse_args([
        "mark", "--number", "1", "--new-status", "ACTIONED", "--reason", "fixed",
    ])
    result = to.cmd_mark(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "ACTIONED" in log
    assert "fixed" in log


def test_mark_nonexistent_observation(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "mark", "--number", "999", "--new-status", "DECLINED", "--reason", "n/a",
    ])
    result = to.cmd_mark(args)
    assert result == 1


def test_archive_moves_resolved(isolated_env, monkeypatch):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "issue 1", "--improvement", "fix 1", "--principle", "p 1",
    ]))
    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "issue 2", "--improvement", "fix 2", "--principle", "p 2",
    ]))

    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=2)).isoformat()
    log = to.log_path().read_text(encoding="utf-8")
    log = log.replace("**Status:** OPEN", f"**Status:** ACTIONED ({old_date}) — resolved", 1)
    to.log_path().write_text(log, encoding="utf-8")

    result = to.cmd_archive(to.build_parser().parse_args(["archive"]))
    assert result == 0

    active_log = to.log_path().read_text(encoding="utf-8")
    assert "### Observation 2:" in active_log
    assert "### Observation 1:" not in active_log

    archive_files = list(to.archive_dir().glob("log-*.md"))
    assert len(archive_files) == 1
    assert "### Observation 1:" in archive_files[0].read_text(encoding="utf-8")


def test_archive_keeps_same_day_resolved(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "issue", "--improvement", "fix", "--principle", "p",
    ]))
    to.cmd_mark(to.build_parser().parse_args([
        "mark", "--number", "1", "--new-status", "ACTIONED", "--reason", "resolved today",
    ]))

    to.cmd_archive(to.build_parser().parse_args(["archive"]))

    log = to.log_path().read_text(encoding="utf-8")
    assert "### Observation 1:" in log, "same-day resolved should stay in active log"


def test_status_reports_counts(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "issue 1", "--improvement", "fix 1", "--principle", "p 1",
    ]))
    to.cmd_append(to.build_parser().parse_args([
        "append", "--session-context", "test", "--skill", "tdd",
        "--issue", "issue 2", "--improvement", "fix 2", "--principle", "p 2",
    ]))
    to.cmd_mark(to.build_parser().parse_args([
        "mark", "--number", "1", "--new-status", "DECLINED", "--reason", "not needed",
    ]))

    result = to.cmd_status(to.build_parser().parse_args(["status"]))
    assert result == 0


def test_next_review_sets_date(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    to.cmd_next_review(to.build_parser().parse_args(["next-review"]))

    from datetime import date
    assert to.review_date_path().read_text(encoding="utf-8").strip() == date.today().isoformat()


def test_stage_copies_skill(isolated_env, tmp_path):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    src = tmp_path / "fake-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("# Fake Skill\n\ncontent\n", encoding="utf-8")

    result = to.cmd_stage(to.build_parser().parse_args(["stage", str(src)]))
    assert result == 0

    from datetime import date
    staged = to.obs_dir().parent / "skill-updates" / date.today().isoformat() / "fake-skill"
    assert (staged / "SKILL.md").exists()
    assert "# Fake Skill" in (staged / "SKILL.md").read_text(encoding="utf-8")


def test_append_with_reference_file(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "append",
        "--session-context", "test",
        "--skill", "tdd",
        "--issue", "test issue",
        "--improvement", "test fix",
        "--principle", "test p",
        "--reference-file", "logs/session-2026-07-29.md",
    ])
    result = to.cmd_append(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "**Reference file:** logs/session-2026-07-29.md" in log


def test_append_without_reference_file(isolated_env):
    to = isolated_env
    to.cmd_init(to.build_parser().parse_args(["init"]))

    args = to.build_parser().parse_args([
        "append",
        "--session-context", "test",
        "--skill", "tdd",
        "--issue", "test issue",
        "--improvement", "test fix",
        "--principle", "test p",
    ])
    result = to.cmd_append(args)
    assert result == 0

    log = to.log_path().read_text(encoding="utf-8")
    assert "Reference file" not in log
