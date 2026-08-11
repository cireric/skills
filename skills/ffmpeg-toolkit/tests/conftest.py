"""Test fixtures for ffmpeg-toolkit."""
import io
import json
import os
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeBins(NamedTuple):
    """Fixture providing fake ffmpeg/ffprobe binaries for testing."""

    input: Path
    log_path: Path

    def read_log(self) -> List[List[str]]:
        """Read logged ffmpeg argv calls, one list per invocation."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        return [json.loads(line) for line in lines if line]

    def run(
        self, args: Sequence[str]
    ) -> "FakeBins.Result":
        """Run cli.main with args, capturing stdout/stderr/exitcode."""
        import cli  # lazy import so monkeypatch takes effect

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            exitcode = cli.main(list(args))
            return FakeBins.Result(
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
def fake_bins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeBins:
    """Set up fake ffmpeg/ffprobe binaries and monkeypatch CLI paths."""
    import cli

    fake_dir = Path(__file__).resolve().parent / "fake_bin"
    ffmpeg_fake = str(fake_dir / "ffmpeg.py")
    ffprobe_fake = str(fake_dir / "ffprobe.py")

    # Create a real input file
    input_file = tmp_path / "in.mp4"
    input_file.write_text("fake video data")

    # Set FAKE_LOG env
    log_path = tmp_path / "ffmpeg_log.txt"
    monkeypatch.setenv("FAKE_LOG", str(log_path))

    monkeypatch.setattr(cli, "FFMPEG_BIN", ffmpeg_fake)
    monkeypatch.setattr(cli, "FFPROBE_BIN", ffprobe_fake)

    return FakeBins(input=input_file, log_path=log_path)
