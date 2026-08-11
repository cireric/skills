"""Test fixtures for video-download."""
import io
import json
import sys
from pathlib import Path
from typing import List, NamedTuple, Sequence

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeYtDlp(NamedTuple):
    """Fixture providing a fake yt-dlp binary for testing."""

    log_path: Path

    def read_log(self) -> List[List[str]]:
        """Read logged yt-dlp argv calls, one list per invocation."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(line) for line in lines if line]

    def run(self, args: Sequence[str]) -> "FakeYtDlp.Result":
        """Run cli.main with args, capturing stdout/stderr/exitcode."""
        import cli  # lazy import so monkeypatch takes effect

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            exitcode = cli.main(list(args))
            return FakeYtDlp.Result(
                exitcode=exitcode,
                stdout=sys.stdout.getvalue(),
                stderr=sys.stderr.getvalue(),
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    class Result(NamedTuple):
        exitcode: int
        stdout: str
        stderr: str


@pytest.fixture
def fake_ytdlp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeYtDlp:
    """Point the CLI at the fake yt-dlp binary."""
    import cli

    fake_bin = str(Path(__file__).resolve().parent / "fake_bin" / "yt-dlp.py")
    log_path = tmp_path / "ytdlp_log.txt"
    monkeypatch.setenv("FAKE_LOG", str(log_path))
    monkeypatch.setattr(cli, "YTDLP_BIN", fake_bin)
    return FakeYtDlp(log_path=log_path)
