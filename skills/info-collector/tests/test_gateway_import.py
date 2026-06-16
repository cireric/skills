"""Test that importing scripts.gateway does NOT trigger jieba module loading.

This must run in a subprocess to avoid false positives when other tests
(e.g. test_proceed.py) have already loaded jieba into sys.modules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent


class TestGatewayImports:
    """Gateway import invariant tests."""

    def test_no_jieba_import(self) -> None:
        """Verify importing scripts.gateway does not load jieba."""
        code = (
            "import scripts.gateway; "
            "import sys; "
            "assert 'jieba' not in sys.modules, "
            "'jieba was loaded by importing scripts.gateway'"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(SKILL_DIR),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Subprocess failed (exit code {result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
