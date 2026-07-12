import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
import learnings as L  # noqa: E402


def test_capture_is_append_only(tmp_path, monkeypatch):
    monkeypatch.setenv("LEARNINGS_ROOT", str(tmp_path / "notepads"))
    assert L.main(["capture", "--scope", "p", "--category", "issues",
                   "--task-id", "t1", "--content", "flaky on windows"]) == 0
    p = tmp_path / "notepads" / "p" / "issues.md"
    assert p.exists()
    L.main(["capture", "--scope", "p", "--category", "issues",
            "--task-id", "t2", "--content", "second pitfall"])
    text = p.read_text()
    assert text.count("## [") == 2
    assert "flaky on windows" in text and "second pitfall" in text


def test_retrieve_filters_by_topic(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LEARNINGS_ROOT", str(tmp_path / "notepads"))
    L.main(["capture", "--scope", "p", "--category", "learnings",
            "--task-id", "t1", "--content", "prefer pathlib over os.path"])
    L.main(["capture", "--scope", "p", "--category", "issues",
            "--task-id", "t2", "--content", "unrelated network timeout"])
    capsys.readouterr()
    L.main(["retrieve", "--scope", "p", "--topic", "pathlib"])
    out = capsys.readouterr().out
    assert "pathlib" in out
    assert "network timeout" not in out


def test_debrief_never_writes_agents_md(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LEARNINGS_ROOT", str(tmp_path / "notepads"))
    L.main(["capture", "--scope", "p", "--category", "issues",
            "--task-id", "t1", "--content", "windows path normalization breaks guard"])
    L.main(["capture", "--scope", "p", "--category", "issues",
            "--task-id", "t2", "--content", "windows path normalization breaks guard again"])
    capsys.readouterr()
    L.main(["debrief", "--scope", "p"])
    out = capsys.readouterr().out
    assert "never writes AGENTS.md" in out
    assert not (tmp_path / "AGENTS.md").exists()
