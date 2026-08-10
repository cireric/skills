"""Deep-dive gate checks and target identification (ADR 0064).

When scope.json depth is "deep", the analysis→review transition is replaced
by analysis→deep_dive→review. This module provides:
- DeepDiveGate: gate checks for the deep_dive→review transition
- identify_deep_dive_targets: scan analysis.json for deep-dive-worthy targets
- determine_convergence: decide whether the deep-dive loop should continue
- generate_deep_dive_plan: create deep_dive_plan.json from identified targets
"""

from __future__ import annotations

from pathlib import Path

from .lib.check_types import CheckResult
from .lib.constants import (
    ARTIFACT_ANALYSIS,
    ARTIFACT_COLLECTED,
    ARTIFACT_DEEP_DIVE_PLAN,
    ARTIFACT_SCOPE,
    _DEEP_DIVE_MAX_ROUNDS,
    _DEEP_DIVE_MIN_SOURCES_PER_TARGET,
    _DEEP_DIVE_SOFT_CONVERGENCE_ROUNDS,
    _DEEP_DIVE_TRIGGER_INDIRECT_RATIO,
    _DEEP_DIVE_TRIGGER_SINGLE_SOURCE_RATIO,
    _DEEP_DIVE_TRIGGER_SOURCE_ABSENT_COUNT,
    _VALID_DEEP_DIVE_TARGET_STATUSES,
    _VALID_DEEP_DIVE_TRIGGER_REASONS,
)
from .lib.exceptions import ArtifactError
from .lib.utils import build_collected_url_set, read_json, write_json


def _dd_config(config: dict | None) -> dict:
    dd = (config or {}).get("deep_dive_defaults") or {}
    return dd


def _get_threshold(dd: dict, key: str, default: float | int) -> float | int:
    return dd.get(key, default)


class DeepDiveGate:
    """Gate checks for the deep_dive→review transition."""

    def __init__(self, workdir: Path, config: dict | None = None):
        self.workdir = workdir
        self.config = config
        self.dd = _dd_config(config)

    def check(self) -> list[CheckResult]:
        return [
            self._check_plan_exists(),
            self._check_target_completion(),
            self._check_source_depth(),
            self._check_verification(),
            self._check_convergence_declared(),
            self._check_round_budget(),
        ]

    def _check_plan_exists(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        if not plan_path.exists():
            return CheckResult(
                "deep_dive_plan_exists", "BLOCKER", False,
                "deep_dive_plan.json not found. Run `deep-dive-plan` to generate it.",
                repair_hints=["Run `python -m scripts.cli deep-dive-plan` to identify deep-dive targets and generate the plan."],
            )
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult(
                "deep_dive_plan_exists", "BLOCKER", False,
                "deep_dive_plan.json is not valid JSON.",
            )
        if not isinstance(plan, dict) or "targets" not in plan:
            return CheckResult(
                "deep_dive_plan_exists", "BLOCKER", False,
                "deep_dive_plan.json missing 'targets' field.",
            )
        return CheckResult("deep_dive_plan_exists", "BLOCKER", True)

    def _check_target_completion(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult("target_completion", "BLOCKER", True)
        targets = plan.get("targets", [])
        incomplete = []
        for t in targets:
            if not isinstance(t, dict):
                continue
            status = t.get("status", "")
            if status not in ("completed", "skipped"):
                tid = t.get("id", "?")
                incomplete.append(f"{tid} (status={status})")
        if incomplete:
            return CheckResult(
                "target_completion", "BLOCKER", False,
                f"Incomplete deep-dive targets: {', '.join(incomplete)}",
                repair_hints=["Complete or skip all deep-dive targets before proceeding to review."],
            )
        skipped_no_reason = []
        for t in targets:
            if not isinstance(t, dict):
                continue
            if t.get("status") == "skipped" and not t.get("skip_reason"):
                skipped_no_reason.append(t.get("id", "?"))
        if skipped_no_reason:
            return CheckResult(
                "target_completion", "BLOCKER", False,
                f"Skipped targets without reason: {', '.join(skipped_no_reason)}",
                repair_hints=["Provide a skip_reason for each skipped target."],
            )
        return CheckResult("target_completion", "BLOCKER", True)

    def _check_source_depth(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        min_sources = _get_threshold(self.dd, "min_sources_per_target", _DEEP_DIVE_MIN_SOURCES_PER_TARGET)
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult("deep_dive_source_depth", "BLOCKER", True)
        targets = plan.get("targets", [])
        insufficient = []
        for t in targets:
            if not isinstance(t, dict):
                continue
            if t.get("status") != "completed":
                continue
            new_sources = t.get("new_sources", [])
            if len(new_sources) < min_sources:
                tid = t.get("id", "?")
                insufficient.append(f"{tid} ({len(new_sources)}/{min_sources})")
        if insufficient:
            return CheckResult(
                "deep_dive_source_depth", "BLOCKER", False,
                f"Completed targets with insufficient new sources: {', '.join(insufficient)}",
                repair_hints=[f"Each completed target needs ≥{min_sources} new sources. Search for more sources for the listed targets."],
            )
        return CheckResult("deep_dive_source_depth", "BLOCKER", True)

    def _check_verification(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult("deep_dive_verification", "BLOCKER", True)
        targets = plan.get("targets", [])
        target_ids = {t.get("id") for t in targets if isinstance(t, dict) and t.get("status") == "completed"}
        if not target_ids:
            return CheckResult("deep_dive_verification", "BLOCKER", True)
        analysis_path = self.workdir / ARTIFACT_ANALYSIS
        try:
            analysis = read_json(analysis_path)
        except ArtifactError:
            return CheckResult("deep_dive_verification", "BLOCKER", True)
        targeted_section_ids = {t.get("section_id") for t in targets if isinstance(t, dict) and t.get("status") == "completed" and t.get("section_id")}
        absent_claims = []
        for section in analysis.get("sections", []):
            sec_id = section.get("id", "")
            if targeted_section_ids and sec_id not in targeted_section_ids:
                continue
            for claim in section.get("claims", []):
                sv = claim.get("source_verification", "")
                if sv == "source_absent":
                    summary = claim.get("summary", "")[:60]
                    absent_claims.append(f"{sec_id}: {summary}")
        if absent_claims:
            return CheckResult(
                "deep_dive_verification", "BLOCKER", False,
                f"source_absent claims remain after deep-dive ({len(absent_claims)} found)",
                repair_hints=["Find and add sources for source_absent claims, or skip the corresponding targets with a reason."],
            )
        return CheckResult("deep_dive_verification", "BLOCKER", True)

    def _check_convergence_declared(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult("convergence_declared", "WARN", True)
        if plan.get("convergence") is None:
            return CheckResult(
                "convergence_declared", "WARN", True,
                "Convergence not yet declared in deep_dive_plan.json.",
            )
        return CheckResult("convergence_declared", "WARN", True)

    def _check_round_budget(self) -> CheckResult:
        plan_path = self.workdir / ARTIFACT_DEEP_DIVE_PLAN
        try:
            plan = read_json(plan_path)
        except ArtifactError:
            return CheckResult("round_budget", "INFO", True)
        current_round = plan.get("round", 0)
        max_rounds = plan.get("max_rounds", _DEEP_DIVE_MAX_ROUNDS)
        return CheckResult(
            "round_budget", "INFO", True,
            f"Deep-dive round {current_round}/{max_rounds}",
        )


def identify_deep_dive_targets(workdir: Path, config: dict | None = None) -> list[dict]:
    """Scan analysis.json for deep-dive-worthy targets.

    Trigger conditions:
    1. source_absent claims (count >= trigger threshold)
    2. source_indirect ratio > threshold
    3. single_source ratio > threshold
    4. unresolved tensions

    Returns list of target dicts for deep_dive_plan.json.
    """
    dd = _dd_config(config)
    analysis_path = workdir / ARTIFACT_ANALYSIS
    try:
        analysis = read_json(analysis_path)
    except ArtifactError:
        return []

    targets = []
    target_counter = 0

    trigger_absent_count = _get_threshold(dd, "trigger_source_absent_count", _DEEP_DIVE_TRIGGER_SOURCE_ABSENT_COUNT)
    trigger_indirect_ratio = _get_threshold(dd, "trigger_indirect_ratio", _DEEP_DIVE_TRIGGER_INDIRECT_RATIO)
    trigger_single_ratio = _get_threshold(dd, "trigger_single_source_ratio", _DEEP_DIVE_TRIGGER_SINGLE_SOURCE_RATIO)

    absent_by_section: dict[str, list[dict]] = {}
    indirect_count = 0
    total_claims = 0
    single_source_count = 0

    for section in analysis.get("sections", []):
        sec_id = section.get("id", "unknown")
        for claim in section.get("claims", []):
            total_claims += 1
            sv = claim.get("source_verification", "")
            sources = claim.get("sources", [])
            if sv == "source_absent":
                absent_by_section.setdefault(sec_id, []).append(claim)
            if sv == "source_indirect":
                indirect_count += 1
            if len(sources) < 2:
                single_source_count += 1

    for sec_id, claims in absent_by_section.items():
        if len(claims) >= trigger_absent_count:
            target_counter += 1
            summaries = [c.get("summary", "")[:80] for c in claims[:3]]
            targets.append({
                "id": f"dd_{target_counter}",
                "section_id": sec_id,
                "claim_summary": "; ".join(summaries),
                "trigger_reason": "source_absent",
                "search_queries": [],
                "target_tiers": [1, 2],
                "status": "pending",
                "skip_reason": None,
                "new_sources": [],
                "round_created": 0,
            })

    if total_claims > 0 and indirect_count / total_claims > trigger_indirect_ratio:
        target_counter += 1
        targets.append({
            "id": f"dd_{target_counter}",
            "section_id": "",
            "claim_summary": f"{indirect_count}/{total_claims} claims have source_indirect verification",
            "trigger_reason": "source_indirect",
            "search_queries": [],
            "target_tiers": [1, 2],
            "status": "pending",
            "skip_reason": None,
            "new_sources": [],
            "round_created": 0,
        })

    if total_claims > 0 and single_source_count / total_claims > trigger_single_ratio:
        target_counter += 1
        targets.append({
            "id": f"dd_{target_counter}",
            "section_id": "",
            "claim_summary": f"{single_source_count}/{total_claims} claims rely on a single source",
            "trigger_reason": "single_source",
            "search_queries": [],
            "target_tiers": [1, 2, 3],
            "status": "pending",
            "skip_reason": None,
            "new_sources": [],
            "round_created": 0,
        })

    tension_by_section: dict[str, list[dict]] = {}
    for section in analysis.get("sections", []):
        sec_id = section.get("id", "unknown")
        for tension in section.get("tensions", []):
            if not tension.get("resolved", False):
                tension_by_section.setdefault(sec_id, []).append(tension)

    for sec_id, tensions in tension_by_section.items():
        target_counter += 1
        summaries = [t.get("summary", "")[:80] for t in tensions[:3]]
        targets.append({
            "id": f"dd_{target_counter}",
            "section_id": sec_id,
            "claim_summary": "; ".join(summaries),
            "trigger_reason": "tension_unresolved",
            "search_queries": [],
            "target_tiers": [1, 2, 3],
            "status": "pending",
            "skip_reason": None,
            "new_sources": [],
            "round_created": 0,
        })

    return targets


def determine_convergence(workdir: Path, config: dict | None = None) -> dict | None:
    """Determine convergence condition for the deep-dive loop.

    Returns {"type": "hard"|"natural"|"soft", "reason": "..."} or None (continue).
    """
    dd = _dd_config(config)
    plan_path = workdir / ARTIFACT_DEEP_DIVE_PLAN
    try:
        plan = read_json(plan_path)
    except ArtifactError:
        return {"type": "hard", "reason": "deep_dive_plan.json missing or unreadable"}

    current_round = plan.get("round", 0)
    max_rounds = plan.get("max_rounds", _get_threshold(dd, "max_rounds", _DEEP_DIVE_MAX_ROUNDS))
    soft_rounds = _get_threshold(dd, "soft_convergence_rounds", _DEEP_DIVE_SOFT_CONVERGENCE_ROUNDS)

    if current_round >= max_rounds:
        return {"type": "hard", "reason": f"round budget exhausted ({current_round}/{max_rounds})"}

    remaining_targets = identify_deep_dive_targets(workdir, config)
    if not remaining_targets:
        return {"type": "natural", "reason": "all trigger conditions resolved"}

    targets = plan.get("targets", [])
    new_sources_this_round = 0
    for t in targets:
        if not isinstance(t, dict):
            continue
        if t.get("status") in ("completed", "in_progress"):
            new_sources_this_round += len(t.get("new_sources", []))

    if new_sources_this_round == 0 and current_round >= soft_rounds:
        return {"type": "soft", "reason": f"no new sources found in round {current_round} (≥{soft_rounds} soft threshold)"}

    return None


def generate_deep_dive_plan(workdir: Path, config: dict | None = None, round_num: int = 1) -> dict:
    """Generate deep_dive_plan.json from identified targets.

    If a plan already exists, increments round and merges new targets.
    """
    dd = _dd_config(config)
    max_rounds = _get_threshold(dd, "max_rounds", _DEEP_DIVE_MAX_ROUNDS)
    plan_path = workdir / ARTIFACT_DEEP_DIVE_PLAN

    existing_plan = None
    if plan_path.exists():
        try:
            existing_plan = read_json(plan_path)
        except ArtifactError:
            pass

    targets = identify_deep_dive_targets(workdir, config)

    if existing_plan and isinstance(existing_plan, dict):
        existing_ids = {t.get("id") for t in existing_plan.get("targets", []) if isinstance(t, dict)}
        max_id = 0
        for t in existing_plan.get("targets", []):
            if isinstance(t, dict):
                tid = t.get("id", "dd_0")
                try:
                    num = int(tid.split("_")[1])
                    max_id = max(max_id, num)
                except (IndexError, ValueError):
                    pass
        for i, t in enumerate(targets):
            new_id = f"dd_{max_id + i + 1}"
            t["id"] = new_id
            t["round_created"] = round_num
        existing_targets = existing_plan.get("targets", [])
        all_targets = existing_targets + targets
        plan = {
            "round": round_num,
            "max_rounds": max_rounds,
            "targets": all_targets,
            "convergence": existing_plan.get("convergence"),
        }
    else:
        for i, t in enumerate(targets):
            t["round_created"] = round_num
        plan = {
            "round": round_num,
            "max_rounds": max_rounds,
            "targets": targets,
            "convergence": None,
        }

    write_json(plan, plan_path)
    return plan
