"""Test that importing scripts.gateway does not trigger heavy module loading.

This must run in a subprocess to avoid false positives when other tests
have already loaded modules into sys.modules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent

# Modules that should NOT be loaded when importing scripts.gateway.
# These are either removed dependencies (jieba, superseded by ADR 0012)
# or modules that would indicate an import chain problem.
_FORBIDDEN_MODULES = frozenset({"jieba"})


class TestGatewayImports:
    """Gateway import invariant tests."""

    def test_no_forbidden_imports(self) -> None:
        """Verify importing scripts.gateway does not load forbidden modules."""
        forbidden = ", ".join(repr(m) for m in _FORBIDDEN_MODULES)
        code = (
            "import scripts.gateway; "
            "import sys; "
            f"loaded = [m for m in {{{forbidden}}} if m in sys.modules]; "
            "assert not loaded, "
            "'Forbidden modules loaded by importing scripts.gateway: ' + ', '.join(loaded)"
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
