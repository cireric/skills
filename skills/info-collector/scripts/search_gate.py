"""SearchGate: deep module for the search→analysis phase gate.

Owns all validation logic that determines whether the search phase
produced sufficient material to proceed to analysis. Public interface:

    SearchGate(workdir, config).check() -> list[CheckResult]
"""

from __future__ import annotations

import string
from pathlib import Path
from urllib.parse import urlparse

from .artifact_checks import CheckResult, _read_artifact
from .lib.constants import (
    ARTIFACT_COLLECTED,
    ARTIFACT_SCOPE,
    ARTIFACT_SEARCH_PLAN,
    _CHINESE_STOP_WORDS,
    _COVERAGE_THRESHOLD,
    _DEPTH_MIN_SOURCES_PER_DIRECTION,
    _ENGLISH_STOP_WORDS,
    _MAX_COVERED_DIRECTIONS,
    _SOURCE_FIDELITY_MISSING_RATIO_BLOCKER,
    _SOURCE_FIDELITY_EXEMPT_RATIO_WARN,
)
from .lib.exceptions import ArtifactError
from .lib.source_router import get_default_min_sources, get_route
from .lib.utils import read_json, tokenize_cjk_aware

_STOP_WORDS = _ENGLISH_STOP_WORDS | _CHINESE_STOP_WORDS


class SearchGate:
    """Validates search-phase artifacts before proceeding to analysis."""

    def __init__(self, workdir: Path, config: dict | None = None):
        self.workdir = workdir
        self.config = config
        self._scope: dict | None = None
        self._collected: list | None = None
        self._search_plan: dict | None = None

        try:
            self._scope = read_json(workdir / ARTIFACT_SCOPE)
        except ArtifactError:
            pass

        try:
            self._collected = read_json(workdir / ARTIFACT_COLLECTED)
            if not isinstance(self._collected, list):
                self._collected = None
        except ArtifactError:
            pass

        try:
            self._search_plan = read_json(workdir / ARTIFACT_SEARCH_PLAN)
        except ArtifactError:
            pass

    _DOMAIN_CONCENTRATION_WARN = 0.50
    _TIER_COMPLETED_WARN_RATIO = 0.50

    def check(self) -> list[CheckResult]:
        """Run all search-gate checks. Returns list of CheckResult."""
        return [
            self._check_collected_exists(),
            self._check_collected_schema(),
            self._check_min_sources(),
            self._check_tier_coverage(),
            self._check_topic_coverage(),
            self._check_source_fidelity(),
            self._check_search_plan_compliance(),
            self._check_domain_concentration(),
            self._check_tier_task_completion(),
        ]

    @property
    def _goal_type(self) -> str:
        if self._scope:
            return self._scope.get("goal_type", "other")
        return "other"

    @property
    def _search_directions(self) -> set[str]:
        if self._scope:
            return set(self._scope.get("search_directions", []))
        return set()

    def _check_collected_exists(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("collected_exists", "BLOCKER", False, "Cannot read collected.json")
        if len(self._collected) < 1:
            return CheckResult("collected_exists", "BLOCKER", False, "collected.json must have at least 1 entry")
        return CheckResult("collected_exists", "BLOCKER", True)

    def _check_collected_schema(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("collected_schema", "BLOCKER", True, "Skipped (no collected.json)")
        from .lib.schemas import validate_collected
        errors = validate_collected(self._collected)
        if errors:
            detail = "; ".join(f"{e.field}: {e.message}" for e in errors)
            return CheckResult("collected_schema", "BLOCKER", False, detail)
        return CheckResult("collected_schema", "BLOCKER", True)

    def _check_min_sources(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("min_sources", "WARN", True, "Skipped (no collected.json)")
        goal_type = self._goal_type
        min_src = get_default_min_sources(goal_type, self.config)
        if len(self._collected) < min_src:
            return CheckResult(
                "min_sources", "WARN", False,
                f"min_sources warning: {len(self._collected)} < {min_src} (configurable WARN)",
            )
        return CheckResult("min_sources", "WARN", True)

    def _check_tier_coverage(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("tier_coverage", "WARN", True, "Skipped (no collected.json)")
        goal_type = self._goal_type
        route = get_route(goal_type, self.config)
        route_path = route.get("path", [])
        optional_tiers = route.get("optional_tiers", [])
        if route_path and self._collected:
            covered_tiers = {entry.get("source_tier") for entry in self._collected if entry.get("source_tier")}
            missing_required = [t for t in route_path if t not in covered_tiers]
            if missing_required:
                return CheckResult(
                    "tier_coverage", "WARN", False,
                    f"tier_coverage WARN: route requires tiers {route_path}, "
                    f"but tiers {missing_required} have no sources in collected.json",
                )
            missing_optional = [t for t in optional_tiers if t not in covered_tiers]
            if missing_optional:
                print(
                    f"  [INFO] tier_coverage: optional tiers {missing_optional} have no sources (non-blocking)",
                    file=__import__("sys").stderr,
                )
        return CheckResult("tier_coverage", "WARN", True)

    def _check_topic_coverage(self) -> CheckResult:
        if self._collected is None or self._scope is None:
            return CheckResult("topic_coverage", "BLOCKER", False, "Cannot read collected.json or scope.json")
        needed = self._search_directions
        if not needed:
            return CheckResult("topic_coverage", "BLOCKER", True)

        covered: set[str] = set()
        direction_counts: dict[str, int] = {d: 0 for d in needed}

        for entry in self._collected:
            cd = entry.get("covered_directions")
            if cd is None:
                continue
            if not isinstance(cd, list):
                continue
            if len(cd) > _MAX_COVERED_DIRECTIONS:
                continue
            invalid = [d for d in cd if d not in needed]
            if invalid:
                continue
            for d in cd:
                covered.add(d)
                direction_counts[d] += 1

        for entry in self._collected:
            if entry.get("covered_directions") is not None:
                continue
            combined_text = (
                entry.get("title", "")
                + " " + entry.get("snippet", "")
                + " " + entry.get("fetched_content", "")[:500]
            ).lower()
            for direction in needed:
                tokens = self._tokenize_direction(direction)
                if not tokens:
                    continue
                matched = sum(1 for t in tokens if t in combined_text)
                if matched / len(tokens) >= _COVERAGE_THRESHOLD:
                    covered.add(direction)
                    direction_counts[direction] += 1

        depth = self._scope.get("depth", "standard")
        min_per_direction = _DEPTH_MIN_SOURCES_PER_DIRECTION.get(depth, 3)

        messages: list[str] = []
        for direction in needed:
            count = direction_counts.get(direction, 0)
            if count < min_per_direction:
                messages.append(
                    f"per_direction_min_sources WARN: direction '{direction}' "
                    f"has {count} sources, depth='{depth}' requires {min_per_direction}"
                )

        missing = needed - covered
        if missing:
            for d in missing:
                if self._has_cjk_tokens([d]):
                    messages.append(
                        f"topic_coverage WARN (CJK direction): search direction not covered: {d}"
                    )
                else:
                    return CheckResult(
                        "topic_coverage", "BLOCKER", False,
                        f"topic_coverage BLOCKER: search direction not covered: {d}",
                    )
                tokens = self._tokenize_direction(d)
                if tokens:
                    suggestions = [t for t in tokens if not self._is_stop_word(t)]
                    if suggestions:
                        messages.append(
                            f"  Suggestion: try searching for '{d}' with keywords: {', '.join(suggestions[:5])}"
                        )

        if messages:
            has_blocker = any("BLOCKER" in m for m in messages)
            level = "BLOCKER" if has_blocker else "WARN"
            return CheckResult("topic_coverage", level, False, "; ".join(messages))
        return CheckResult("topic_coverage", "BLOCKER", True)

    def _check_source_fidelity(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("source_fidelity", "BLOCKER", True, "Cannot read collected.json")
        if not self._collected:
            return CheckResult("source_fidelity", "BLOCKER", True, "collected.json is empty")
        missing_count = 0
        fetch_failed_count = 0
        total = len(self._collected)
        for entry in self._collected:
            if entry.get("fetch_failed", False):
                fetch_failed_count += 1
                continue
            sf = entry.get("source_file", "")
            if not sf:
                missing_count += 1
                continue
            source_path = self.workdir / sf
            if not source_path.exists() or source_path.stat().st_size == 0:
                missing_count += 1
        checked = total - fetch_failed_count
        ratio = missing_count / checked if checked > 0 else 0
        exempt_ratio = fetch_failed_count / total if total > 0 else 0
        parts = []
        if missing_count > 0:
            parts.append(f"{missing_count}/{checked} entries have no source file")
        if fetch_failed_count > 0:
            parts.append(f"{fetch_failed_count}/{total} entries have fetch_failed=true (exempt)")
        msg = "; ".join(parts) if parts else "all entries have source files"
        if checked == 0:
            return CheckResult("source_fidelity", "BLOCKER", True, msg)
        if ratio > _SOURCE_FIDELITY_MISSING_RATIO_BLOCKER:
            return CheckResult("source_fidelity", "BLOCKER", False, f"{missing_count}/{checked} entries ({ratio:.0%}) lack source files — re-fetch with full content before proceeding")
        if exempt_ratio > _SOURCE_FIDELITY_EXEMPT_RATIO_WARN:
            parts.append(f"high exempt ratio: {exempt_ratio:.0%}")
            return CheckResult("source_fidelity", "WARN", False, "; ".join(parts))
        if missing_count > 0:
            return CheckResult("source_fidelity", "WARN", False, msg)
        return CheckResult("source_fidelity", "BLOCKER", True, msg)

    def _check_search_plan_compliance(self) -> CheckResult:
        if self._search_plan is None:
            return CheckResult("search_plan_compliance", "WARN", True, "search_plan.json not found")
        tasks = self._search_plan.get("tasks", [])
        if not tasks:
            return CheckResult("search_plan_compliance", "WARN", True, "search_plan.json has no tasks")
        pending = [t for t in tasks if t.get("status") == "pending"]
        completed = [t for t in tasks if t.get("status") == "completed"]
        skipped = [t for t in tasks if t.get("status") == "skipped"]
        directions_in_plan = set(t.get("direction", "") for t in tasks)
        directions_completed = set(t.get("direction", "") for t in completed)
        directions_missing = directions_in_plan - directions_completed
        if pending and not completed:
            return CheckResult(
                "search_plan_compliance", "WARN", False,
                f"0/{len(tasks)} tasks completed, {len(pending)} pending — search_plan was not followed. "
                f"Directions without any completed task: {', '.join(sorted(directions_missing))}",
            )
        if pending:
            return CheckResult(
                "search_plan_compliance", "WARN", False,
                f"{len(completed)}/{len(tasks)} tasks completed, {len(pending)} pending — search_plan incomplete. "
                f"Directions without coverage: {', '.join(sorted(directions_missing))}",
            )
        if directions_missing:
            return CheckResult(
                "search_plan_compliance", "WARN", False,
                f"{len(completed)}/{len(tasks)} tasks completed, but directions without coverage: {', '.join(sorted(directions_missing))}",
            )
        return CheckResult(
            "search_plan_compliance", "WARN", True,
            f"{len(completed)}/{len(tasks)} tasks completed, {len(skipped)} skipped",
        )

    def _check_domain_concentration(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("domain_concentration", "WARN", True, "Skipped (no collected.json)")
        domain_counts: dict[str, int] = {}
        for entry in self._collected:
            url = entry.get("url", "")
            try:
                domain = urlparse(url).hostname or ""
            except Exception:
                domain = ""
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if not domain_counts:
            return CheckResult("domain_concentration", "WARN", True, "No domains found")
        total = sum(domain_counts.values())
        top_domain = max(domain_counts, key=domain_counts.get)
        top_ratio = domain_counts[top_domain] / total
        if top_ratio > self._DOMAIN_CONCENTRATION_WARN:
            return CheckResult(
                "domain_concentration", "WARN", False,
                f"{domain_counts[top_domain]}/{total} sources ({top_ratio:.0%}) from {top_domain} "
                f"— consider diversifying sources across domains",
            )
        return CheckResult("domain_concentration", "WARN", True)

    def _check_tier_task_completion(self) -> CheckResult:
        if self._search_plan is None:
            return CheckResult("tier_task_completion", "WARN", True, "search_plan.json not found")
        tasks = self._search_plan.get("tasks", [])
        if not tasks:
            return CheckResult("tier_task_completion", "WARN", True, "No tasks in search_plan.json")
        tier_stats: dict[int, dict[str, int]] = {}
        for task in tasks:
            tier = task.get("tier", 0)
            status = task.get("status", "pending")
            stats = tier_stats.setdefault(tier, {"completed": 0, "total": 0})
            stats["total"] += 1
            if status == "completed":
                stats["completed"] += 1
        low_completion: list[str] = []
        for tier in sorted(tier_stats):
            stats = tier_stats[tier]
            if stats["total"] > 0:
                ratio = stats["completed"] / stats["total"]
                if ratio < self._TIER_COMPLETED_WARN_RATIO and tier <= 2:
                    low_completion.append(
                        f"Tier {tier}: {stats['completed']}/{stats['total']} tasks completed ({ratio:.0%})"
                    )
        if low_completion:
            return CheckResult(
                "tier_task_completion", "WARN", False,
                f"Low Tier 1-2 task completion: {'; '.join(low_completion)} — "
                f"consider retrying with alternative search queries or platform-native APIs",
            )
        return CheckResult("tier_task_completion", "WARN", True)

    @staticmethod
    def _is_stop_word(token: str) -> bool:
        if len(token) <= 1:
            return True
        if all(c in string.punctuation for c in token):
            return True
        if token in _STOP_WORDS:
            return True
        return False

    @staticmethod
    def _tokenize_direction(direction: str) -> list[str]:
        return [t for t in tokenize_cjk_aware(direction, lowercase=True) if not SearchGate._is_stop_word(t)]

    @staticmethod
    def _has_cjk_tokens(directions: list[str]) -> bool:
        for d in directions:
            for ch in d:
                if '\u4e00' <= ch <= '\u9fff':
                    return True
        return False
