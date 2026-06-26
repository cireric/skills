"""ClaimValidator: deep module for claim-level quality checks.

Validates claim metadata, precision, verification, source attribution,
deduplication, and metric consistency in analysis.json against collected.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .artifact_checks import CheckResult, _read_artifact
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_REVIEW_REPORT,
    _QUANTITATIVE_GOAL_TYPES,
    _SINGLE_SOURCE_RATIO,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_by_url, normalize_url, read_json

_PRECISE_NUMBER_PATTERN = re.compile(
    r"(?<!\w)"
    r"(\d{1,3}(?:,\d{3})*|\d+)"
    r"(\s*(%|ms|req/s|req\/sec|MB|GB|x|times faster))?"
    r"(?!\w)"
)


def _source_text(item: dict) -> str:
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


def _number_found_in_source(claim_text: str, source_text: str) -> bool:
    claim_nums = _normalize_numbers(claim_text)
    source_nums = _normalize_numbers(source_text)
    return bool(claim_nums & source_nums)


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
            text = claim.get("text", "")
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
        self._review_exists: bool = (workdir / ARTIFACT_REVIEW_REPORT).exists()
        self._sections: list[dict] = []
        self._all_claims: list[tuple[str, int, dict]] = []
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
        except ArtifactError:
            pass

    def check(self) -> list[CheckResult]:
        if self._analysis_err:
            return [self._analysis_err]
        return [
            self._check_claim_metadata(),
            self._check_precision_inflation(),
            self._check_claim_verified(),
            self._check_source_metadata(),
            self._check_metric_type_homogeneity(),
            self._check_claim_dedup(),
            self._check_claim_source_relevance(),
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
        blockers: list[str] = []
        warnings: list[str] = []
        for sec_id, si, claim in self._all_claims:
            text = claim.get("text", "")
            ev = claim.get("evidence_type")
            prec = claim.get("precision")
            if prec == "exact" and ev in ("third_party_estimate", "qualitative_trend", "expert_opinion"):
                blockers.append(
                    f"sections.{sec_id}.claims[{si}]: precision='exact' with "
                    f"evidence_type='{ev}' — use precision='range' or 'qualitative'"
                )
            if ev == "third_party_estimate" and _PRECISE_NUMBER_PATTERN.search(text):
                source_texts = []
                for url in claim.get("source_urls", []):
                    item = self._collected_by_url.get(normalize_url(url))
                    if item:
                        source_texts.append(_source_text(item))
                any_sufficient = any(len(src) >= 200 for src in source_texts)
                if not any_sufficient:
                    continue
                else:
                    numbers_in_source = any(
                        _number_found_in_source(text, src) for src in source_texts
                    )
                    if not numbers_in_source:
                        warnings.append(
                            f"sections.{sec_id}.claims[{si}]: evidence_type='third_party_estimate' "
                            f"but text contains precise number not found in source — use precision='range' or rephrase qualitatively"
                        )
        for section in self._sections:
            blockers.extend(_check_data_variance(section))
        if blockers:
            return CheckResult("precision_inflation", "BLOCKER", False, "; ".join(blockers + warnings))
        if warnings:
            return CheckResult("precision_inflation", "WARN", False, "; ".join(warnings))
        return CheckResult("precision_inflation", "BLOCKER", True)

    def _check_claim_verified(self) -> CheckResult:
        if not self._review_exists:
            return CheckResult("claim_verified", "BLOCKER", True, "Skipped (review not yet done)")
        warnings: list[str] = []
        total_claims = 0
        verified_count = 0
        for sec_id, _si, claim in self._all_claims:
            total_claims += 1
            verified = claim.get("verified")
            if verified is True:
                verified_count += 1
            if verified is False:
                text = claim.get("text", "")[:50]
                return CheckResult(
                    "claim_verified",
                    "BLOCKER",
                    False,
                    f"Claim in section '{sec_id}' not verified: {text}",
                )
            if verified == "unverifiable":
                text = claim.get("text", "")[:50]
                warnings.append(f"Claim in section '{sec_id}' unverifiable: {text}")
        if total_claims > 0 and verified_count / total_claims < 0.6:
            warnings.append(
                f"claim_verified ratio: {verified_count}/{total_claims} "
                f"({verified_count / total_claims:.0%}) < 60% — quality should be 'degraded'"
            )
        if warnings:
            return CheckResult("claim_verified", "WARN", True, "; ".join(warnings))
        return CheckResult("claim_verified", "BLOCKER", True)

    def _check_source_metadata(self) -> CheckResult:
        for sec_id, ci, claim in self._all_claims:
            ev = claim.get("evidence_type")
            if ev in ("official_data", "independent_benchmark"):
                meta = claim.get("source_metadata")
                if not meta or not isinstance(meta, dict):
                    return CheckResult(
                        "source_metadata", "BLOCKER", False,
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' requires source_metadata",
                    )
                tc = meta.get("test_conditions", "")
                if not tc or (isinstance(tc, str) and not tc.strip()):
                    return CheckResult(
                        "source_metadata", "BLOCKER", False,
                        f"sections.{sec_id}.claims[{ci}]: evidence_type='{ev}' requires non-empty source_metadata.test_conditions",
                    )
        return CheckResult("source_metadata", "BLOCKER", True)

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
                    "BLOCKER",
                    False,
                    f"Section '{sec_id}' mixes metric_types: {sorted(types)}. "
                    "Split into separate sections or tables.",
                )
        return CheckResult("metric_type_homogeneity", "BLOCKER", True)

    def _check_claim_dedup(self) -> CheckResult:
        claim_sections: dict[str, list[str]] = {}
        for sec_id, _si, claim in self._all_claims:
            text = claim.get("text", "").strip()
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

    def _check_claim_source_relevance(self) -> CheckResult:
        warnings: list[str] = []
        for sec_id, ci, claim in self._all_claims:
            if claim.get("evidence_type") == "third_party_estimate":
                continue
            text = claim.get("text", "")
            if not _PRECISE_NUMBER_PATTERN.search(text):
                continue
            source_texts = []
            for url in claim.get("source_urls", []):
                item = self._collected_by_url.get(normalize_url(url))
                if item:
                    source_texts.append(
                        (item.get("fetched_content", "") + " " + item.get("snippet", "")).lower()
                    )
            if not source_texts:
                continue
            any_sufficient = any(len(src) >= 200 for src in source_texts)
            if not any_sufficient:
                continue
            numbers_in_source = any(
                _number_found_in_source(text, src) for src in source_texts
            )
            if not numbers_in_source:
                warnings.append(
                    f"sections.{sec_id}.claims[{ci}]: claim contains precise number(s) "
                    f"not found in source fetched_content — verify source attribution or use range/qualitative precision"
                )
        if warnings:
            msg = f"{len(warnings)} claim(s) with numbers not found in sources: " + "; ".join(warnings[:5])
            if len(warnings) > 5:
                msg += f"; ... and {len(warnings) - 5} more"
            return CheckResult("claim_source_relevance", "WARN", False, msg)
        return CheckResult("claim_source_relevance", "WARN", True, "all numeric claims traceable to sources")
