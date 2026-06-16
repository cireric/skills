from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .exceptions import ArtifactError


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower().rstrip("/") or "/"
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(params.items()), doseq=True)
    else:
        sorted_query = ""
    return urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))


def read_json(path: Path, retries: int = 2, delay: float = 0.5) -> Any:
    for attempt in range(retries + 1):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ArtifactError(str(path), f"Invalid JSON: {e}") from e
        except OSError:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise ArtifactError(str(path), f"Failed after {retries + 1} attempts") from None


def write_json(data, path: Path, retries: int = 2, delay: float = 0.5) -> None:
    for attempt in range(retries + 1):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return
        except OSError:
            if attempt < retries:
                time.sleep(delay)
                continue
            raise ArtifactError(str(path), f"Failed after {retries + 1} attempts") from None


def _find_project_root() -> Path:
    """Walk up from CWD to find the first directory containing .git."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return current


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
