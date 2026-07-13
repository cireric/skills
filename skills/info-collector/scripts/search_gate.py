"""SearchGate: deep module for the search→analysis phase gate.

Owns all validation logic that determines whether the search phase
produced sufficient material to proceed to analysis. Public interface:

    SearchGate(workdir, config).check() -> list[CheckResult]

ADR 0042: Removed topic_coverage, search_plan_compliance,
domain_concentration, tier_task_completion. min_sources and
tier_coverage upgraded to BLOCKER with repair hints from config.
"""

from __future__ import annotations

from pathlib import Path

from .artifact_checks import CheckResult
from .lib.constants import (
    ARTIFACT_COLLECTED,
    ARTIFACT_SCOPE,
    _DEPTH_MIN_SOURCES,
    _SOURCE_FIDELITY_MISSING_RATIO_BLOCKER,
    _SOURCE_FIDELITY_EXEMPT_RATIO_WARN,
    _SOURCE_FIDELITY_SHALLOW_RATIO_BLOCKER,
    _SOURCE_FIDELITY_SHALLOW_CHARS,
    _SOURCE_FIDELITY_THIN_RATIO_WARN,
    _SOURCE_FIDELITY_THIN_CHARS,
    _SOURCE_FIDELITY_SNIPPET_OVERLAP_RATIO_BLOCKER,
    _SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD,
)
from .lib.exceptions import ArtifactError
from .lib.source_router import get_route
from .lib.utils import read_json


class SearchGate:
    """Validates search-phase artifacts before proceeding to analysis."""

    def __init__(self, workdir: Path, config: dict | None = None):
        self.workdir = workdir
        self.config = config
        self._scope: dict | None = None
        self._collected: list | None = None

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

    def check(self) -> list[CheckResult]:
        """Run all search-gate checks. Returns list of CheckResult."""
        return [
            self._check_collected_exists(),
            self._check_collected_schema(),
            self._check_min_sources(),
            self._check_tier_coverage(),
            self._check_source_fidelity(),
            self._check_direction_tagging(),
            self._check_direction_coverage(),
        ]

    @staticmethod
    def _normalized_directions(scope: dict | None) -> list[str]:
        if not scope:
            return []
        sds = scope.get("search_directions")
        if not isinstance(sds, list):
            return []
        return [str(d).strip().lower() for d in sds if isinstance(d, str) and d.strip()]

    def _check_direction_tagging(self) -> CheckResult:
        """ADR 0052: every collected entry must declare a `direction` when the
        scope declares search_directions. BLOCKER — enforces the user's breadth
        contract at the search→analysis gate."""
        directions = self._normalized_directions(self._scope)
        if not directions:
            return CheckResult("direction_tagging", "BLOCKER", True, "Skipped (no search_directions in scope)")
        if self._collected is None:
            return CheckResult("direction_tagging", "BLOCKER", True, "Skipped (no collected.json)")
        untagged = [
            entry.get("url", f"entry[{i}]")
            for i, entry in enumerate(self._collected)
            if not isinstance(entry, dict) or not isinstance(entry.get("direction"), str) or not entry["direction"].strip()
        ]
        if untagged:
            return CheckResult(
                "direction_tagging", "BLOCKER", False,
                f"direction_tagging BLOCKER: {len(untagged)} collected entries lack a `direction` field "
                f"(scope declares search_directions). Tag each source with the search_direction it serves, or 'other'.",
                repair_hints=[
                    f"Add a `direction` field to each collected entry: the matching scope.search_directions value, or 'other' for discoveries outside declared directions."
                ],
            )
        return CheckResult("direction_tagging", "BLOCKER", True)

    def _check_direction_coverage(self) -> CheckResult:
        """ADR 0052: every declared search_direction must have >=1 collected entry
        tagged with it. BLOCKER — the user's declared directions are the breadth floor."""
        directions = self._normalized_directions(self._scope)
        if not directions:
            return CheckResult("direction_coverage", "BLOCKER", True, "Skipped (no search_directions in scope)")
        if self._collected is None:
            return CheckResult("direction_coverage", "BLOCKER", True, "Skipped (no collected.json)")
        tagged = {
            str(entry.get("direction", "")).strip().lower()
            for entry in self._collected
            if isinstance(entry, dict) and isinstance(entry.get("direction"), str) and entry["direction"].strip()
        }
        missing = [d for d in directions if d not in tagged]
        if missing:
            return CheckResult(
                "direction_coverage", "BLOCKER", False,
                f"direction_coverage BLOCKER: declared directions with no matching collected source: {', '.join(missing)}",
                repair_hints=[
                    f"Search for and collect sources serving these directions, tagging them with `direction`: {', '.join(missing)}"
                ],
            )
        return CheckResult("direction_coverage", "BLOCKER", True)

    @property
    def _goal_type(self) -> str:
        if self._scope:
            return self._scope.get("goal_type", "other")
        return "other"

    def _check_collected_exists(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("collected_exists", "BLOCKER", False, "Cannot read collected.json", repair_hints=["Search for sources and build collected.json with at least one entry"])
        if len(self._collected) < 1:
            return CheckResult("collected_exists", "BLOCKER", False, "collected.json must have at least 1 entry", repair_hints=["Search for sources and build collected.json with at least one entry"])
        return CheckResult("collected_exists", "BLOCKER", True)

    def _check_collected_schema(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("collected_schema", "BLOCKER", True, "Skipped (no collected.json)")
        from .lib.schemas import validate_collected
        errors = validate_collected(self._collected)
        if errors:
            detail = "; ".join(f"{e.field}: {e.message}" for e in errors)
            return CheckResult("collected_schema", "BLOCKER", False, detail, repair_hints=["Fix collected.json schema: each entry needs url, title, snippet, source_tier fields"])
        return CheckResult("collected_schema", "BLOCKER", True)

    def _check_min_sources(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("min_sources", "BLOCKER", True, "Skipped (no collected.json)")
        depth = self._scope.get("depth", "standard") if self._scope else "standard"
        min_src = _DEPTH_MIN_SOURCES.get(depth, 5)
        if len(self._collected) < min_src:
            repair_hints = self._build_all_tier_repair_hints()
            return CheckResult(
                "min_sources", "BLOCKER", False,
                f"min_sources BLOCKER: {len(self._collected)} < {min_src} (depth='{depth}')",
                repair_hints=repair_hints,
            )
        return CheckResult("min_sources", "BLOCKER", True)

    def _check_tier_coverage(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("tier_coverage", "BLOCKER", True, "Skipped (no collected.json)")
        goal_type = self._goal_type
        route = get_route(goal_type, self.config)
        route_path = route.get("path", [])
        optional_tiers = route.get("optional_tiers", [])
        if route_path and self._collected:
            covered_tiers = {entry.get("source_tier") for entry in self._collected if entry.get("source_tier")}
            missing_required = [t for t in route_path if t not in covered_tiers]
            if missing_required:
                repair_hints = self._build_tier_repair_hints(missing_required)
                return CheckResult(
                    "tier_coverage", "BLOCKER", False,
                    f"tier_coverage BLOCKER: route requires tiers {route_path}, "
                    f"but tiers {missing_required} have no sources in collected.json",
                    repair_hints=repair_hints,
                )
            missing_optional = [t for t in optional_tiers if t not in covered_tiers]
            if missing_optional:
                print(
                    f"  [INFO] tier_coverage: optional tiers {missing_optional} have no sources (non-blocking)",
                    file=__import__("sys").stderr,
                )
        return CheckResult("tier_coverage", "BLOCKER", True)

    def _check_source_fidelity(self) -> CheckResult:
        if self._collected is None:
            return CheckResult("source_fidelity", "BLOCKER", True, "Cannot read collected.json")
        if not self._collected:
            return CheckResult("source_fidelity", "BLOCKER", True, "collected.json is empty")
        missing_count = 0
        shallow_count = 0
        thin_count = 0
        fetch_failed_count = 0
        snippet_overlap_count = 0
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
                continue
            try:
                file_content = source_path.read_text(encoding="utf-8")
                content_len = len(file_content)
            except OSError:
                missing_count += 1
                continue
            if content_len < _SOURCE_FIDELITY_SHALLOW_CHARS:
                shallow_count += 1
            elif content_len < _SOURCE_FIDELITY_THIN_CHARS:
                thin_count += 1
            snippet = entry.get("snippet", "")
            if snippet and content_len >= _SOURCE_FIDELITY_SHALLOW_CHARS:
                if self._snippet_overlap_ratio(file_content, snippet) > _SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD:
                    snippet_overlap_count += 1
        checked = total - fetch_failed_count
        ratio = missing_count / checked if checked > 0 else 0
        exempt_ratio = fetch_failed_count / total if total > 0 else 0
        shallow_ratio = shallow_count / checked if checked > 0 else 0
        thin_ratio = thin_count / checked if checked > 0 else 0
        snippet_overlap_ratio = snippet_overlap_count / checked if checked > 0 else 0
        parts = []
        if missing_count > 0:
            parts.append(f"{missing_count}/{checked} entries have no source file")
        if shallow_count > 0:
            parts.append(f"{shallow_count}/{checked} entries have source files < {_SOURCE_FIDELITY_SHALLOW_CHARS} chars (summary-only, not full content)")
        if thin_count > 0:
            parts.append(f"{thin_count}/{checked} entries have source files < {_SOURCE_FIDELITY_THIN_CHARS} chars")
        if snippet_overlap_count > 0:
            parts.append(f"{snippet_overlap_count}/{checked} entries have source files with >{_SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD:.0%} snippet overlap (likely summary, not full text)")
        if fetch_failed_count > 0:
            parts.append(f"{fetch_failed_count}/{total} entries have fetch_failed=true (exempt)")
        msg = "; ".join(parts) if parts else "all entries have source files with sufficient depth"
        if checked == 0:
            return CheckResult("source_fidelity", "BLOCKER", True, msg)
        if ratio > _SOURCE_FIDELITY_MISSING_RATIO_BLOCKER:
            pct = f"{ratio:.0%}"
            return CheckResult("source_fidelity", "BLOCKER", False, f"{missing_count}/{checked} entries ({ratio:.0%}) lack source files — re-fetch with full content before proceeding", repair_hints=[f"{pct} of source files are missing. Re-fetch full content using fetch tools for the URLs without source files"])
        if shallow_ratio > _SOURCE_FIDELITY_SHALLOW_RATIO_BLOCKER:
            pct = f"{shallow_ratio:.0%}"
            return CheckResult("source_fidelity", "BLOCKER", False, f"{shallow_count}/{checked} entries ({shallow_ratio:.0%}) have source files < {_SOURCE_FIDELITY_SHALLOW_CHARS} chars — search-result highlights are NOT sufficient; re-fetch full article content", repair_hints=[f"{pct} of source files are too short (<{_SOURCE_FIDELITY_SHALLOW_CHARS} chars). Re-fetch full article content — search-result snippets are not sufficient for analysis"])
        if snippet_overlap_ratio > _SOURCE_FIDELITY_SNIPPET_OVERLAP_RATIO_BLOCKER:
            pct = f"{snippet_overlap_ratio:.0%}"
            return CheckResult("source_fidelity", "BLOCKER", False, f"{snippet_overlap_count}/{checked} entries ({snippet_overlap_ratio:.0%}) have source files with >{_SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD:.0%} snippet overlap — source files appear to be summaries of snippets, not full article text (ADR 0040)", repair_hints=[f"{pct} of source files have high snippet overlap — they appear to be rewrites of search snippets, not full articles. Re-fetch original content from the source URL"])
        if exempt_ratio > _SOURCE_FIDELITY_EXEMPT_RATIO_WARN:
            parts.append(f"high exempt ratio: {exempt_ratio:.0%}")
            return CheckResult("source_fidelity", "WARN", False, "; ".join(parts))
        if missing_count > 0:
            return CheckResult("source_fidelity", "WARN", False, msg)
        if shallow_count > 0 or thin_count > 0:
            return CheckResult("source_fidelity", "WARN", False, msg)
        return CheckResult("source_fidelity", "BLOCKER", True, msg)

    def _build_tier_hints(self, tiers: list[int], prefix_fn: "Callable[[int], str]") -> list[str]:
        """Build repair hints for given tiers by querying config sources.

        Args:
            tiers: Tier numbers to generate hints for.
            prefix_fn: Returns the prefix string for each tier (e.g. "Tier 2 零覆盖").
        """
        hints: list[str] = []
        if not self.config:
            return hints
        sources = self.config.get("sources", {})
        for tier in tiers:
            tier_data = sources.get(str(tier), {})
            tier_sources = tier_data.get("sources", [])
            by_lang: dict[str, list[dict]] = {}
            for s in tier_sources:
                lang = s.get("language", "en")
                by_lang.setdefault(lang, []).append(s)
            parts = [prefix_fn(tier)]
            for lang, lang_sources in sorted(by_lang.items()):
                names = [s.get("name", s.get("domain", "")) for s in lang_sources]
                site_queries = [s.get("site_query", "") for s in lang_sources if s.get("site_query")]
                lang_parts: list[str] = []
                if names:
                    lang_parts.append(f"sources({lang}): {', '.join(names)}")
                if site_queries:
                    lang_parts.append(f"try({lang}): {', '.join(site_queries)}")
                parts.extend(lang_parts)
            if len(parts) > 1:
                hints.append(" → ".join(parts))
        return hints

    def _build_tier_repair_hints(self, missing_tiers: list[int]) -> list[str]:
        """Build repair hints for missing tiers by querying config sources."""
        return self._build_tier_hints(missing_tiers, lambda t: f"Tier {t} 零覆盖")

    def _build_all_tier_repair_hints(self) -> list[str]:
        """Build repair hints listing ALL route tiers (for min_sources check)."""
        goal_type = self._goal_type
        route = get_route(goal_type, self.config)
        route_path = route.get("path", [])
        route_optional = route.get("optional_tiers", [])
        all_tiers = route_path + [t for t in route_optional if t not in route_path]
        return self._build_tier_hints(all_tiers, lambda t: f"Tier {t}")

    @staticmethod
    def _snippet_overlap_ratio(file_content: str, snippet: str) -> float:
        """Compute what fraction of file_content is covered by snippet.

        A summary that merely restates the snippet will have a high ratio
        (snippet covers most of the short file). A genuine full article will
        have a low ratio (snippet is a tiny fraction of the file).

        Uses word-level matching for Latin text, character-level for CJK.
        Returns 0.0 if file_content is empty.
        """
        if not file_content or not file_content.strip():
            return 0.0
        content_lower = file_content.lower().strip()
        snippet_lower = snippet.lower().strip()
        if not snippet_lower:
            return 0.0
        has_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in snippet_lower)
        if has_cjk:
            content_chars = [ch for ch in content_lower if not ch.isspace()]
            snippet_chars = [ch for ch in snippet_lower if not ch.isspace()]
            if not content_chars:
                return 0.0
            snippet_set = set(snippet_chars)
            matched_in_content = sum(1 for ch in content_chars if ch in snippet_set)
            return matched_in_content / len(content_chars)
        content_words = content_lower.split()
        snippet_words = set(snippet_lower.split())
        if not content_words:
            return 0.0
        matched_in_content = sum(1 for w in content_words if w in snippet_words)
        return matched_in_content / len(content_words)
