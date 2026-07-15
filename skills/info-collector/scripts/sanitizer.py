from __future__ import annotations

from .lib.constants import (
    _CLAIM_KEYS,
    _EVIDENCE_TYPE_ALIASES,
    _NON_EXACT_EVIDENCE_TYPES,
    _SECTION_KEYS,
    _SOURCE_TYPE_ALIASES,
    _VALID_CONFIDENCE,
    _VALID_EVIDENCE_TYPES,
    _VALID_PRECISION,
    _VALID_SOURCE_TYPES,
)

__all__ = ["sanitize_sections"]


def sanitize_sections(analysis: dict, collected_urls: set[str] | None = None) -> dict:
    """Clean subagent output before schema validation."""
    result = dict(analysis)
    sections = result.get("sections")
    if not isinstance(sections, list):
        return result

    cleaned_sections = []
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            cleaned_sections.append(section)
            continue
        sec = dict(section)
        if "section_id" in sec and "id" not in sec:
            sec["id"] = sec.pop("section_id")
        if "claims" not in sec:
            sec["claims"] = []
        for field in ("key_insights", "tensions"):
            items = sec.get(field)
            if isinstance(items, list):
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        raise ValueError(
                            f"sections[{i}].{field}[{j}] is a {type(item).__name__}, "
                            f"not an object. Expected {{summary, sources}}. "
                            f"Wrap each item as {{\"summary\": <text>, \"sources\": [<url>]}}."
                        )
        claims = sec.get("claims")
        if isinstance(claims, list):
            cleaned_claims = []
            for claim in claims:
                if not isinstance(claim, dict):
                    cleaned_claims.append(claim)
                    continue
                cl = dict(claim)
                if "text" in cl and "summary" not in cl:
                    cl["summary"] = cl.pop("text")
                if "source_urls" in cl and "sources" not in cl:
                    cl["sources"] = cl.pop("source_urls")
                if "evidence_type" in cl:
                    et = cl["evidence_type"]
                    if et not in _VALID_EVIDENCE_TYPES:
                        cl["evidence_type"] = _EVIDENCE_TYPE_ALIASES.get(et, "qualitative_trend")
                if "confidence" in cl and cl["confidence"] not in _VALID_CONFIDENCE:
                    cl["confidence"] = "medium"
                if "precision" in cl and cl["precision"] not in _VALID_PRECISION:
                    cl["precision"] = "qualitative"
                if (
                    cl.get("precision") == "exact"
                    and cl.get("evidence_type") in _NON_EXACT_EVIDENCE_TYPES
                ):
                    cl["precision"] = "range"
                meta = cl.get("source_metadata")
                if isinstance(meta, dict) and "source_type" in meta:
                    st = meta["source_type"]
                    if st not in _VALID_SOURCE_TYPES:
                        meta["source_type"] = _SOURCE_TYPE_ALIASES.get(st, "survey")
                if collected_urls is not None and "sources" in cl:
                    valid = [u for u in cl["sources"] if u in collected_urls]
                    if valid:
                        cl["sources"] = valid
                cleaned_claims.append({k: v for k, v in cl.items() if k in _CLAIM_KEYS})
            sec["claims"] = cleaned_claims
        cleaned_sections.append({k: v for k, v in sec.items() if k in _SECTION_KEYS})
    result["sections"] = cleaned_sections
    return result
