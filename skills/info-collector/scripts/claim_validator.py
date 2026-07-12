"""ClaimValidator: deep module for claim-level quality checks.

Validates claim metadata, precision, verification, source attribution,
deduplication, and metric consistency in analysis.json against collected.json.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .artifact_checks import CheckResult, _read_artifact
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    _ENGLISH_STOP_WORDS,
    _INDIRECT_CITATION_PATTERNS,
    _QUANTITATIVE_GOAL_TYPES,
    _SINGLE_SOURCE_RATIO,
    _VENDOR_SOURCE_TYPES,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_by_url, build_collected_url_set, normalize_url, read_json

_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:,\d{3})*|\d+)"
    r"(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?"
    r"(?!\w)"
)

_REF_MARKER_RE = re.compile(r'\{\{ref:(.*?)\}\}')


def _source_text(item: dict, workdir: Path | None = None) -> str:
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
            entity = _extract_indirect_entity(match, text)
            if entity and not _entity_matches_host(entity, source_hosts):
                return True

    return False


def _extract_indirect_entity(match: re.Match, text: str) -> str | None:
    group = match.group(0)
    if group.startswith("据"):
        for keyword in ("报告", "预测", "发现", "统计", "调查", "研究", "分析"):
            if keyword in group:
                return group[1:].split(keyword)[0].strip()
    for keyword in ("报告", "预测", "发现", "统计", "调查", "研究", "分析"):
        if keyword in group:
            return group.split(keyword)[0].strip()
    for prefix in ("according to ", "based on ", "cited in ", "reported by "):
        if group.lower().startswith(prefix):
            return group[len(prefix):].strip()
    return None


def _entity_matches_host(entity: str, source_hosts: set[str]) -> bool:
    entity_lower = entity.lower().rstrip(".,;:)")
    for host in source_hosts:
        if not host:
            continue
        host_lower = host.lower()
        parts = host_lower.split(".")
        if entity_lower in parts:
            return True
        if len(parts) >= 2 and entity_lower == parts[-2]:
            return True
    return False


def _check_data_variance(section: dict) -> list[str]:
    blockers: list[str] = []
    sec_id = section.get("id", "?")
    by_metric: dict[str, list[dict]] = {}
    for claim in section.get("claims", []):
        mt = claim.get("metric_type")
        if not mt:
            continue
        by_metric.setdefault(mt, []).append(claim)
    for mt, claims in by_metric.items():
        values = []
        for claim in claims:
            if claim.get("precision") != "exact":
                continue
            text = claim.get("summary", "")
            matches = _PRECISE_NUMBER_PATTERN.findall(text)
            for match in matches:
                num_str = match[0].replace(",", "")
                try:
                    values.append(float(num_str))
                except ValueError:
                    pass
        if len(values) >= 2:
            min_val = min(values)
            max_val = max(values)
            avg = sum(values) / len(values)
            if avg > 0 and (max_val - min_val) / avg > 0.05:
                blockers.append(
                    f"sections.{sec_id}: same metric_type '{mt}' has conflicting exact values "
                    f"({min_val} vs {max_val}) — use precision='range' and explain variance"
                )
    return blockers


class ClaimValidator:
    """Validates claim quality in analysis.json against collected.json.

    Reads both artifacts once in __init__, then check() runs all
    claim-level validations and returns a flat list of CheckResult.
    """

    def __init__(self, workdir: Path, goal_type: str) -> None:
        self._workdir = workdir
        self._goal_type = goal_type
        self._analysis: dict | None = None
        self._analysis_err: CheckResult | None = None
        self._collected: list[dict] = []
        self._collected_by_url: dict[str, dict] = {}
        self._collected_urls: set[str] = set()
        self._sections: list[dict] = []
        self._all_claims: list[tuple[str, int, dict]] = []
        self._sv_data: list | None = None
        self._load_data()

    def _load_data(self) -> None:
        analysis, err = _read_artifact(
            self._workdir / ARTIFACT_ANALYSIS, "claim_validator", "WARN"
        )
        if err:
            self._analysis_err = err
            return
        self._analysis = analysis
        self._sections = analysis.get("sections", []) if analysis else []
        for section in self._sections:
            sec_id = section.get("id", "?")
            for ci, claim in enumerate(section.get("claims", [])):
                self._all_claims.append((sec_id, ci, claim))
        try:
            collected = read_json(self._workdir / ARTIFACT_COLLECTED)
            if isinstance(collected, list):
                self._collected = collected
                self._collected_by_url = build_collected_by_url(collected)
                self._collected_urls = build_collected_url_set(collected)
        except ArtifactError:
            pass

    def check(self) -> list[CheckResult]:
        if self._analysis_err:
            return [self._analysis_err]
        return [
            self._check_claim_metadata(),
            self._check_precision_inflation(),
            self._check_source_metadata(),
            self._check_metric_type_homogeneity(),
            self._check_claim_dedup(),
            self._check_entity_number_conflict(),
            self._check_ref_marker_validity(),
            self._check_claim_source_ref_coverage(),
            self._check_source_verification(),
        ]

    def _check_claim_metadata(self) -> CheckResult:
        total = 0
        missing = 0
        for _sec_id, _si, claim in self._all_claims:
            total += 1
            if not all(k in claim for k in ("evidence_type", "confidence", "precision")):
                missing += 1
        if total == 0:
            return CheckResult("claim_metadata", "WARN", True)
        ratio = missing / total
        if ratio > _SINGLE_SOURCE_RATIO:
            return CheckResult(
                "claim_metadata",
                "WARN",
                False,
                f"{missing}/{total} claims lack evidence_type/confidence/precision metadata "
                f"(ratio={ratio:.0%})",
            )
        return CheckResult("claim_metadata", "WARN", True)

    def _check_precision_inflation(self) -> CheckResult:
        warnings: list[str] = []
        for sec_id, si, claim in self._all_claims:
            text = claim.get("summary", "")
            ev = claim.get("evidence_type")
            prec = claim.get("precision")
            if prec == "exact" and ev in ("third_party_estimate", "qualitative_trend", "expert_opinion"):
                warnings.append(
                    f"sections.{sec_id}.claims[{si}]: precision='exact' with "
                    f"evidence_type='{ev}' — auto-downgraded to 'range' by sanitize; "
                    f"use precision='range' or 'qualitative'"
                )
            if ev == "third_party_estimate" and _PRECISE_NUMBER_PATTERN.search(text):
                source_texts = []
                for url in claim.get("sources", []):
                    item = self._collected_by_url.get(normalize_url(url))
                    if item:
                        source_texts.append(_source_text(item, self._workdir))
                any_sufficient = any(len(src) >= 200 for src in source_texts)
                if not any_sufficient:
                    continue
                else:
                    numbers_in_source = any(
                        _number_found_in_source(text, src) == "source_confirmed" for src in source_texts
                    )
                    if not numbers_in_source:
                        warnings.append(
                            f"sections.{sec_id}.claims[{si}]: evidence_type='third_party_estimate' "
                            f"but text contains precise number not found in source — use precision='range' or rephrase qualitatively"
                        )
        for section in self._sections:
            warnings.extend(_check_data_variance(section))
        if warnings:
            return CheckResult("precision_inflation", "WARN", False, "; ".join(warnings))
        return CheckResult("precision_inflation", "WARN", True)

    _GENERIC_TEST_CONDITIONS = frozenset({
        "various environments and survey methodologies",
        "various environments",
        "n/a",
        "not specified",
        "see source",
    })

    def _check_source_metadata(self) -> CheckResult:
        warnings: list[str] = []
        for sec_id, ci, claim in self._all_claims:
            ev = claim.get("evidence_type")
            if ev in ("official_data", "independent_benchmark"):
                meta = claim.get("source_metadata")
                if not meta or not isinstance(meta, dict):
                    warnings.append(
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' missing source_metadata"
                    )
                    continue
                tc = meta.get("test_conditions", "")
                if not tc or (isinstance(tc, str) and not tc.strip()):
                    warnings.append(
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' has empty source_metadata.test_conditions"
                    )
                elif isinstance(tc, str) and tc.strip().lower() in self._GENERIC_TEST_CONDITIONS:
                    warnings.append(
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' has generic placeholder test_conditions '{tc.strip()}'"
                    )
                elif isinstance(tc, str) and len(tc.strip()) < 10:
                    warnings.append(
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' has suspiciously short test_conditions '{tc.strip()}'"
                    )
        if warnings:
            return CheckResult("source_metadata", "WARN", False, "; ".join(warnings))
        return CheckResult("source_metadata", "WARN", True)

    def _check_metric_type_homogeneity(self) -> CheckResult:
        for section in self._sections:
            sec_id = section.get("id", "?")
            types: set[str] = set()
            for claim in section.get("claims", []):
                mt = claim.get("metric_type")
                if not mt:
                    continue
                ev = claim.get("evidence_type")
                if ev in ("official_data", "independent_benchmark"):
                    types.add(mt)
            if len(types) > 1:
                return CheckResult(
                    "metric_type_homogeneity",
                    "WARN",
                    False,
                    f"Section '{sec_id}' mixes metric_types: {sorted(types)}. "
                    "Consider splitting into separate sections or tables.",
                )
        return CheckResult("metric_type_homogeneity", "WARN", True)

    def _check_claim_dedup(self) -> CheckResult:
        claim_sections: dict[str, list[str]] = {}
        for sec_id, _si, claim in self._all_claims:
            text = claim.get("summary", "").strip()
            if text:
                claim_sections.setdefault(text, []).append(sec_id)
        duplicates = {text: secs for text, secs in claim_sections.items() if len(secs) > 1}
        if duplicates:
            issues = []
            for text, secs in list(duplicates.items())[:5]:
                issues.append(f"Claim '{text[:40]}...' appears in sections: {', '.join(secs)}")
            return CheckResult(
                "claim_dedup",
                "WARN",
                False,
                f"{len(duplicates)} duplicate claims across sections: " + "; ".join(issues),
            )
        return CheckResult("claim_dedup", "WARN", True)

    _ENTITY_NUMBER_PATTERN = re.compile(
        r"([\w\u4e00-\u9fff][\w\s\u4e00-\u9fff\-\.]{1,40}?)"
        r"\s+"
        r"(\$?\d[\d,]*\.?\d*\s*(?:%|ms|req/s|req/sec|MB|GB|B|x|times|K|万|亿)?)"
    )

    _ENTITY_STOP_WORDS = _ENGLISH_STOP_WORDS | frozenset({
        "an", "been", "being", "could", "does", "have", "its",
        "might", "shall", "should", "these", "those", "were", "would",
    })

    def _check_entity_number_conflict(self) -> CheckResult:
        entity_numbers: dict[str, dict[str, list[str]]] = {}
        for sec_id, _si, claim in self._all_claims:
            text = claim.get("summary", "")
            for match in self._ENTITY_NUMBER_PATTERN.finditer(text):
                entity = match.group(1).strip()
                number = match.group(2).strip()
                if len(entity) < 3 or len(number) < 2:
                    continue
                if entity.lower() in self._ENTITY_STOP_WORDS:
                    continue
                entity_numbers.setdefault(entity, {}).setdefault(number, []).append(sec_id)
        conflicts: list[str] = []
        for entity, numbers in entity_numbers.items():
            if len(numbers) > 1:
                parts = [f"{num} (in {', '.join(secs)})" for num, secs in numbers.items()]
                conflicts.append(f"Entity '{entity}' has conflicting numbers: {'; '.join(parts)}")
        if conflicts:
            shown = conflicts[:5]
            return CheckResult(
                "entity_number_conflict",
                "WARN",
                False,
                f"{len(conflicts)} entity-number conflicts found: "
                + "; ".join(shown)
                + ("..." if len(conflicts) > 5 else ""),
            )
        return CheckResult("entity_number_conflict", "WARN", True)

    def _check_source_verification(self) -> CheckResult:
        if not self._collected_by_url:
            return CheckResult("source_verification_check", "INFO", True, "No collected sources to verify against")

        sv_counts = {"source_confirmed": 0, "source_absent": 0, "source_indirect": 0}
        total = 0
        sv_data: list[tuple[int, int, str]] = []

        for sec_idx, section in enumerate(self._sections):
            for ci, claim in enumerate(section.get("claims", [])):
                total += 1
                sv = self._compute_source_verification(claim)
                sv_data.append((sec_idx, ci, sv))
                sv_counts[sv] += 1

        self._sv_data = sv_data

        parts = [f"{k}: {v}" for k, v in sv_counts.items() if v > 0]
        msg = f"Source verification: {', '.join(parts)}"

        return CheckResult("source_verification_check", "INFO", True, msg)

    def _compute_source_verification(self, claim: dict) -> str:
        if _is_indirect_source(claim, self._collected_by_url):
            return "source_indirect"

        source_texts = []
        for url in claim.get("sources", []):
            item = self._collected_by_url.get(normalize_url(url))
            if item:
                source_texts.append(_source_text(item, self._workdir))

        if not source_texts:
            if _PRECISE_NUMBER_PATTERN.search(claim.get("summary", "")):
                return "source_absent"
            return "source_confirmed"

        results = [_number_found_in_source(claim.get("summary", ""), src) for src in source_texts]
        if any(r == "source_confirmed" for r in results):
            return "source_confirmed"
        return "source_absent"

    def _check_ref_marker_validity(self) -> CheckResult:
        all_refs = []
        for sec in self._sections:
            content = sec.get("content", "")
            for match in _REF_MARKER_RE.finditer(content):
                all_refs.append(normalize_url(match.group(1).strip()))
        if not all_refs:
            return CheckResult("ref_marker_validity", "WARN", True,
                               "No {{ref:URL}} markers found in analysis content")
        missing = [u for u in all_refs if u not in self._collected_urls]
        if missing:
            details = []
            for u in missing[:3]:
                msg = u
                suggestions = []
                for known in self._collected_urls:
                    if known.startswith(u[:40]) or u.startswith(known[:40]):
                        suggestions.append(known)
                        break
                if suggestions:
                    msg += f" (did you mean {suggestions[0]}?)"
                details.append(msg)
            return CheckResult("ref_marker_validity", "BLOCKER", False,
                                f"{len(missing)} {{ref:URL}} markers reference URLs not in collected.json: "
                                f"{'; '.join(details)}{'...' if len(missing) > 3 else ''}",
                                repair_hints=[
                                    f"The following {{ref:URL}} markers are not in collected.json: "
                                    f"{', '.join(missing)}. Remove or replace these markers, ensuring all referenced URLs exist in collected.json"
                                ])
        return CheckResult("ref_marker_validity", "BLOCKER", True,
                           f"All {len(all_refs)} {{ref:URL}} markers reference valid collected.json URLs")

    def _check_claim_source_ref_coverage(self) -> CheckResult:
        violations = []
        for sec in self._sections:
            sec_id = sec.get("id", "?")
            content = sec.get("content", "")
            content_urls = set()
            for match in _REF_MARKER_RE.finditer(content):
                content_urls.add(normalize_url(match.group(1).strip()))
            for ci, claim in enumerate(sec.get("claims", [])):
                for url in claim.get("sources", []):
                    norm = normalize_url(url)
                    if norm not in content_urls:
                        violations.append(f"sections.{sec_id}.claims[{ci}]: {norm}")
        if violations:
            claim_texts = []
            for sec in self._sections:
                sec_id = sec.get("id", "?")
                content = sec.get("content", "")
                content_urls = set()
                for match in _REF_MARKER_RE.finditer(content):
                    content_urls.add(normalize_url(match.group(1).strip()))
                for ci, claim in enumerate(sec.get("claims", [])):
                    for url in claim.get("sources", []):
                        norm = normalize_url(url)
                        if norm not in content_urls:
                            claim_texts.append(claim.get("summary", "")[:40])
            return CheckResult("claim_source_ref_coverage", "BLOCKER", False,
                                f"{len(violations)} claim sources not referenced in content: "
                                f"{violations[:3]}{'...' if len(violations) > 3 else ''}",
                                repair_hints=[
                                    f"The following claims have sources not appearing as {{ref:URL}} markers in their section's content: "
                                    f"{', '.join(claim_texts[:5])}{'...' if len(claim_texts) > 5 else ''}. "
                                    f"Add {{ref:URL}} markers for these source URLs in the section content"
                                ])
        return CheckResult("claim_source_ref_coverage", "BLOCKER", True,
                           "All claim sources are referenced in section content")


def apply_source_verification(workdir: Path) -> None:
    from .lib.constants import ARTIFACT_SCOPE
    from .lib.utils import read_json as _rj, write_json as _wj
    goal_type = "other"
    try:
        scope = _rj(workdir / ARTIFACT_SCOPE)
        goal_type = scope.get("goal_type", "other")
    except Exception:
        pass
    validator = ClaimValidator(workdir, goal_type)
    validator._check_source_verification()
    if validator._sv_data is None:
        return
    try:
        analysis = _rj(workdir / ARTIFACT_ANALYSIS)
    except ArtifactError:
        return
    for sec_idx, ci, sv in validator._sv_data:
        try:
            analysis["sections"][sec_idx]["claims"][ci]["source_verification"] = sv
            analysis["sections"][sec_idx]["claims"][ci]["verified"] = (sv != "source_absent")
        except (IndexError, KeyError):
            pass
    _wj(analysis, workdir / ARTIFACT_ANALYSIS)
