from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .lib.constants import _VENDOR_SOURCE_TYPES, _INDIRECT_CITATION_PATTERNS
from .lib.utils import normalize_url, build_collected_by_url, read_json, write_json


_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:,\d{3})*|\d+)"
    r"(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?"
    r"(?!\w)"
)


def _normalize_numbers(text: str) -> set[str]:
    numbers: set[str] = set()
    for match in _PRECISE_NUMBER_PATTERN.finditer(text):
        raw = match.group(1).replace(",", "")
        try:
            num = float(raw)
        except ValueError:
            continue
        numbers.add(str(int(num)) if num == int(num) else f"{num:.1f}")
        numbers.add(raw)
    for m in re.finditer(r"\$?(\d+(?:\.\d+)?)\s*[Bb](?:illion)?", text):
        try:
            val = float(m.group(1))
            numbers.add(str(int(val * 1_000_000_000)))
            numbers.add(f"{val}B")
        except ValueError:
            pass
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*[-\u2013]\s*(\d+(?:\.\d+)?)\s*%", text):
        numbers.add(m.group(1))
        numbers.add(m.group(2))
    return numbers


def _number_found_in_source(claim_text: str, source_text: str) -> str:
    claim_nums = _normalize_numbers(claim_text)
    if not claim_nums:
        return "source_confirmed"
    source_nums = _normalize_numbers(source_text)
    if claim_nums & source_nums:
        return "source_confirmed"
    return "source_absent"


def _source_text(item: dict, workdir: Path) -> str:
    sf = item.get("source_file", "")
    if sf and workdir is not None:
        source_path = workdir / sf
        try:
            if source_path.exists() and source_path.stat().st_size > 0:
                content = source_path.read_text(encoding="utf-8")
                return (content + " " + item.get("snippet", "")).lower()
        except OSError:
            pass
    return (item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()


def _is_indirect_source(claim: dict, collected_by_url: dict[str, dict]) -> bool:
    for url in claim.get("sources", []):
        item = collected_by_url.get(normalize_url(url))
        if item:
            tier = item.get("source_tier", 0)
            if isinstance(tier, int) and tier >= 3:
                ev = claim.get("evidence_type", "")
                if ev in ("third_party_estimate", "official_data"):
                    return True

    meta = claim.get("source_metadata", {})
    source_type = meta.get("source_type", "") if isinstance(meta, dict) else ""
    if source_type in _VENDOR_SOURCE_TYPES:
        if claim.get("precision") in ("exact", "range"):
            for url in claim.get("sources", []):
                item = collected_by_url.get(normalize_url(url))
                if item:
                    tier = item.get("source_tier", 0)
                    if isinstance(tier, int) and tier >= 3:
                        return True

    text = claim.get("summary", "")
    source_urls = claim.get("sources", [])
    source_hosts: set[str] = set()
    for url in source_urls:
        try:
            source_hosts.add(urlparse(url).hostname or "")
        except Exception:
            pass
    for pattern in _INDIRECT_CITATION_PATTERNS:
        match = pattern.search(text)
        if match:
            entity = match.group(1).strip()
            if entity and not _entity_matches_host(entity, source_hosts):
                return True

    return False


def _entity_matches_host(entity: str, source_hosts: set[str]) -> bool:
    entity_lower = entity.lower().strip()
    for host in source_hosts:
        host_lower = host.lower()
        if entity_lower == host_lower:
            return True
        if host_lower.endswith("." + entity_lower) or host_lower.startswith(entity_lower + "."):
            return True
    return False


def _compute_source_verification(claim: dict, collected_by_url: dict[str, dict], workdir: Path) -> str:
    if _is_indirect_source(claim, collected_by_url):
        return "source_indirect"

    source_texts = []
    for url in claim.get("sources", []):
        item = collected_by_url.get(normalize_url(url))
        if item:
            source_texts.append(_source_text(item, workdir))

    if not source_texts:
        if _PRECISE_NUMBER_PATTERN.search(claim.get("summary", "")):
            return "source_absent"
        return "source_confirmed"

    results = [_number_found_in_source(claim.get("summary", ""), src) for src in source_texts]
    if any(r == "source_confirmed" for r in results):
        return "source_confirmed"
    return "source_absent"


def verify_claims(workdir: Path) -> dict:
    collected_path = workdir / "collected.json"
    analysis_path = workdir / "analysis.json"

    if not collected_path.exists() or not analysis_path.exists():
        return {"error": "collected.json or analysis.json not found"}

    collected = read_json(collected_path)
    analysis = read_json(analysis_path)
    collected_by_url = build_collected_by_url(collected)

    sv_counts = {"source_confirmed": 0, "source_absent": 0, "source_indirect": 0}
    total = 0

    for section in analysis.get("sections", []):
        for claim in section.get("claims", []):
            total += 1
            sv = _compute_source_verification(claim, collected_by_url, workdir)
            claim["source_verification"] = sv
            sv_counts[sv] += 1

    write_json(analysis, analysis_path)

    return {
        "total": total,
        "source_confirmed": sv_counts["source_confirmed"],
        "source_absent": sv_counts["source_absent"],
        "source_indirect": sv_counts["source_indirect"],
    }
