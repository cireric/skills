from __future__ import annotations

import hashlib
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


def compute_url_hash(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def read_json(path: Path, retries: int = 2, delay: float = 0.5) -> Any:
    for attempt in range(retries + 1):
        try:
            with open(path, encoding="utf-8-sig") as f:
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


from .constants import ARTIFACT_CONFIG


def config_path() -> Path:
    """Return the absolute path to config.json in the skill root directory."""
    return Path(__file__).parent.parent.parent / ARTIFACT_CONFIG


def find_project_root() -> Path:
    """Walk up from CWD to find the first directory containing .git."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return current


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def tokenize_cjk_aware(text: str, *, lowercase: bool = False) -> list[str]:
    """Tokenize text with CJK character segmentation.

    Splits on whitespace and CJK/fullwidth punctuation boundaries.
    CJK runs become single tokens; Latin runs are split on whitespace.
    Returns non-empty tokens only. Does NOT filter stop words.
    """
    if lowercase:
        text = text.lower()
    tokens: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if '\u4e00' <= ch <= '\u9fff':
            j = i + 1
            while j < len(text) and '\u4e00' <= text[j] <= '\u9fff':
                j += 1
            tokens.append(text[i:j])
            i = j
        elif ch.isspace() or ('\u3000' <= ch <= '\u303f') or ('\uff00' <= ch <= '\uffef'):
            i += 1
        else:
            j = i + 1
            while j < len(text) and not text[j].isspace() and not ('\u4e00' <= text[j] <= '\u9fff') and not ('\u3000' <= text[j] <= '\u303f') and not ('\uff00' <= text[j] <= '\uffef'):
                j += 1
            token = text[i:j]
            if token.strip():
                tokens.append(token)
            i = j
    return tokens


def build_collected_by_url(collected: list[dict]) -> dict[str, dict]:
    """Build a {normalized_url: entry} lookup dict from a collected list."""
    result: dict[str, dict] = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            result[normalize_url(url)] = item
    return result


def build_collected_url_set(collected: list[dict]) -> set[str]:
    """Build a set of normalized URLs from a collected list."""
    return {normalize_url(item.get("url", "")) for item in collected if isinstance(item, dict)}
