from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import ArtifactError
from .utils import read_json


@dataclass
class CheckResult:
    name: str
    level: str  # "BLOCKER" | "WARN" | "INFO"
    passed: bool
    message: str = ""
    repair_hints: list[str] = field(default_factory=list)


def read_artifact(path: Path, check_name: str, read_error_level: str = "BLOCKER") -> tuple[dict | None, CheckResult | None]:
    """Read a JSON artifact, returning (data, None) on success or (None, CheckResult) on failure.

    On ArtifactError:
      - read_error_level="BLOCKER" → CheckResult(name, "BLOCKER", False, str(e))
      - read_error_level="WARN"    → CheckResult(name, "WARN", True, f"Cannot read {path.name}")
    """
    try:
        data = read_json(path)
    except ArtifactError as e:
        if read_error_level == "BLOCKER":
            return None, CheckResult(check_name, "BLOCKER", False, str(e))
        return None, CheckResult(check_name, "WARN", True, f"Cannot read {path.name}")
    return data, None
