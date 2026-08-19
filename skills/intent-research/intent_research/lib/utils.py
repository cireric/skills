from __future__ import annotations

import hashlib
import json
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


def read_json(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ArtifactError(str(path), f"Invalid JSON: {e}") from e
    except OSError as e:
        raise ArtifactError(str(path), str(e)) from e


def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    return current


def build_collected_by_url(collected: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in collected:
        url = item.get("url", "")
        if url:
            result[normalize_url(url)] = item
    return result


def build_collected_url_set(collected: list[dict]) -> set[str]:
    return {normalize_url(item.get("url", "")) for item in collected if isinstance(item, dict)}


def infer_tier_from_url(url: str, domain_tier_map: dict[str, int] | None = None) -> int:
    if not domain_tier_map:
        return 3
    try:
        netloc = urlparse(url.strip()).netloc.lower().removeprefix("www.")
    except Exception:
        return 3
    for domain, tier in domain_tier_map.items():
        if netloc == domain or netloc.endswith("." + domain):
            return tier
    return 3


def build_domain_tier_map(config: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for tier_str, tier_data in config.get("sources", {}).items():
        try:
            tier = int(tier_str)
        except (ValueError, TypeError):
            continue
        for source in tier_data.get("sources", []):
            domain = source.get("domain", "")
            if domain:
                result[domain] = tier
    return result
