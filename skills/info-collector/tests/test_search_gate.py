from __future__ import annotations

from pathlib import Path

from scripts.search_gate import SearchGate
from scripts.artifact_checks import CheckResult
from scripts.lib.utils import compute_url_hash


def _create_source_file(workdir, url, content="x" * 2100):
    sources_dir = workdir / "sources"
    sources_dir.mkdir(exist_ok=True)
    h = compute_url_hash(url)
    path = sources_dir / f"{h}.md"
    path.write_text(content, encoding="utf-8")
    return f"sources/{h}.md"


def _find_result(results: list[CheckResult], name: str) -> CheckResult | None:
    return next((r for r in results if r.name == name), None)


class TestSearchGateCheck:
    def test_empty_collected_blocks(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        results = SearchGate(tmp_path).check()
        collected_exists = _find_result(results, "collected_exists")
        assert collected_exists is not None
        assert not collected_exists.passed

    def test_missing_collected_blocks(self, tmp_path):
        _make_scope(tmp_path)
        results = SearchGate(tmp_path).check()
        collected_exists = _find_result(results, "collected_exists")
        assert collected_exists is not None
        assert not collected_exists.passed

    def test_valid_search_passes(self, tmp_path):
        config = {
            "sources": {
                "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com"}]},
            },
            "routes": {"tech_selection": {"entry_tier": 2, "path": [2, 3, 4, 1]}},
        }
        _make_scope(tmp_path, goal_type="tech_selection", depth="standard")
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        entries = []
        for i, tier in enumerate([2, 3, 4, 1, 2]):
            url = f"https://src{i}.com"
            h = compute_url_hash(url)
            fname = f"sources/{h}.md"
            (sources_dir / f"{h}.md").write_text("x" * 2100, encoding="utf-8")
            entries.append({"url": url, "title": f"Source {i}", "snippet": f"About topic {i}", "fetched_content": "x" * 2100, "source_file": fname, "source_tier": tier, "direction": ["ai", "ml"][i % 2]})
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path, config).check()
        blockers = [r for r in results if r.level == "BLOCKER" and not r.passed]
        assert not blockers, f"Unexpected blockers: {[b.message for b in blockers]}"

    def test_returns_list_of_check_results(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        assert isinstance(results, list)
        assert all(isinstance(r, CheckResult) for r in results)


class TestTierCoverage:
    def test_all_tiers_covered_no_warn(self, tmp_path):
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI", "snippet": "About AI", "source_tier": 2, "fetched_content": "x" * 800},
                {"url": "https://b.com", "title": "ML", "snippet": "About ML", "source_tier": 3, "fetched_content": "x" * 1000},
                {"url": "https://c.com", "title": "DL", "snippet": "About DL", "source_tier": 4, "fetched_content": "x" * 800},
                {"url": "https://d.com", "title": "NN", "snippet": "About NN", "source_tier": 1, "fetched_content": "x" * 1000},
            ],
        )
        results = SearchGate(tmp_path).check()
        tier = _find_result(results, "tier_coverage")
        assert tier is not None
        assert tier.passed

    def test_missing_tier_produces_warn(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI ML", "snippet": "About AI and ML", "source_tier": 4, "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "More AI", "snippet": "About ML too", "source_tier": 4, "fetched_content": "x" * 500},
            ],
        )
        results = SearchGate(tmp_path).check()
        tier = _find_result(results, "tier_coverage")
        assert tier is not None
        assert not tier.passed

    def test_optional_tier_missing_is_info_not_warn(self, tmp_path, capsys):
        config = {
            "sources": {
                "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com"}]},
            },
            "routes": {
                "academic_research": {"entry_tier": 1, "path": [1], "optional_tiers": [2]},
            },
        }
        _make_scope(tmp_path, goal_type="academic_research", search_directions=[])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "Paper 1", "snippet": "About topic", "source_tier": 1, "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "Paper 2", "snippet": "About topic", "source_tier": 1, "fetched_content": "x" * 700},
            ],
        )
        results = SearchGate(tmp_path, config).check()
        tier = _find_result(results, "tier_coverage")
        assert tier is not None
        assert tier.passed
        captured = capsys.readouterr()
        assert "optional tiers" in captured.err
        assert "[INFO]" in captured.err


class TestSourceFidelity:
    def test_all_entries_have_source_files(self, tmp_path):
        _make_scope(tmp_path)
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("x" * 6000, encoding="utf-8")
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com", "title": "T", "snippet": "S", "source_tier": 3, "source_file": "sources/abc123.md", "fetched_content": "x" * 200}],
        )
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed

    def test_missing_source_files_blocker(self, tmp_path):
        _make_scope(tmp_path)
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/1", "title": "T1", "snippet": "S", "source_tier": 3, "source_file": "sources/missing.md", "fetched_content": ""},
                {"url": "https://example.com/2", "title": "T2", "snippet": "S", "source_tier": 3, "source_file": "sources/also_missing.md", "fetched_content": ""},
            ],
        )
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "BLOCKER"

    def test_fetch_failed_exempt(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com/1", "title": "T1", "snippet": "S", "source_tier": 3, "fetch_failed": True, "fetched_content": ""}],
        )
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed

    def test_no_source_file_field_counts_as_missing(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://example.com/1", "title": "T1", "snippet": "S", "source_tier": 3, "fetched_content": "some text"}],
        )
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "BLOCKER"

    def test_high_exempt_ratio_warns(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://example.com/1", "title": "T1", "snippet": "S", "source_tier": 3, "fetch_failed": True, "fetched_content": ""},
                {"url": "https://example.com/2", "title": "T2", "snippet": "S", "source_tier": 3, "fetch_failed": True, "fetched_content": ""},
                {"url": "https://example.com/3", "title": "T3", "snippet": "S", "source_tier": 3, "source_file": "sources/exists.md", "fetched_content": "x"},
            ],
        )
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "exists.md").write_text("x" * 2100, encoding="utf-8")
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.level == "WARN"
        assert "exempt" in sf.message.lower() or "high exempt" in sf.message.lower()


class TestSnippetOverlapCheck:
    def _build_collected(self, workdir, total, missing, fetch_failed):
        entries = []
        for i in range(total):
            url = f"https://example.com/{i}"
            entry = {"url": url, "title": "T", "snippet": "S", "source_tier": 3, "fetched_content": ""}
            if i < fetch_failed:
                entry["fetch_failed"] = True
            elif i < fetch_failed + missing:
                entry["source_file"] = ""
            else:
                sf = _create_source_file(workdir, url, "x" * 6000)
                entry["source_file"] = sf
            entries.append(entry)
        return entries

    def test_20pct_missing_warn(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=2, fetch_failed=0)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.level == "WARN"
        assert not sf.passed

    def test_30pct_missing_warn(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=3, fetch_failed=0)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.level == "WARN"
        assert not sf.passed

    def test_40pct_missing_blocker(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=4, fetch_failed=0)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "BLOCKER"

    def test_60pct_exempt_warn(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=0, fetch_failed=6)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "WARN"

    def test_50pct_exempt_pass(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=0, fetch_failed=5)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed

    def test_mixed_missing_and_exempt_blocker(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=10, missing=3, fetch_failed=5)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "BLOCKER"

    def test_all_exempt_pass(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, total=1, missing=0, fetch_failed=1)
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed

    def test_empty_collected_pass(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed


class TestSnippetOverlapCheck:
    def test_full_article_passes_overlap(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI"])
        snippet = "Claude Code achieves 78% on SWE-bench Verified with Opus 4.7"
        full_text = snippet + "\n\n" + "Detailed analysis of the benchmark results shows that " * 100
        sf = _create_source_file(tmp_path, "https://a.com", full_text)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "AI", "snippet": snippet, "source_file": sf}],
        )
        results = SearchGate(tmp_path).check()
        fidelity = _find_result(results, "source_fidelity")
        assert fidelity is not None
        assert fidelity.passed

    def test_summary_same_as_snippet_blocks(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI"])
        snippet = "Claude Code achieves 78% on SWE-bench Verified with Opus 4.7 model and strong multi-file editing capability"
        summary_text = (snippet + " ") * 40
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        a_path = sources_dir / "a.md"
        a_path.write_text(summary_text, encoding="utf-8")
        for name in ("b", "c", "d"):
            (sources_dir / f"{name}.md").write_text(summary_text, encoding="utf-8")
        collected = [
            {"url": "https://a.com", "title": "AI", "snippet": snippet, "source_file": "sources/a.md"},
            {"url": "https://b.com", "title": "ML", "snippet": snippet, "source_file": "sources/b.md"},
            {"url": "https://c.com", "title": "DL", "snippet": snippet, "source_file": "sources/c.md"},
            {"url": "https://d.com", "title": "RL", "snippet": snippet, "source_file": "sources/d.md"},
        ]
        _write_json(tmp_path / "collected.json", collected)
        results = SearchGate(tmp_path).check()
        fidelity = _find_result(results, "source_fidelity")
        assert fidelity is not None
        assert not fidelity.passed
        assert "snippet overlap" in fidelity.message.lower() or "ADR 0040" in fidelity.message

    def test_no_snippet_skips_overlap(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI"])
        sf = _create_source_file(tmp_path, "https://a.com", "x" * 5500)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "AI", "snippet": "", "source_file": sf}],
        )
        results = SearchGate(tmp_path).check()
        fidelity = _find_result(results, "source_fidelity")
        assert fidelity is not None
        assert fidelity.passed

    def test_snippet_overlap_ratio_method(self):
        content = "AI coding agents and their benchmarks"
        snippet = "AI coding agents and their benchmarks"
        ratio = SearchGate._snippet_overlap_ratio(content, snippet)
        assert ratio > 0.8

    def test_snippet_overlap_low_for_full_text(self):
        content = "This is a very long article with many different words. " * 200
        snippet = "AI coding agents achieve 78% on SWE-bench"
        ratio = SearchGate._snippet_overlap_ratio(content, snippet)
        assert ratio < 0.5


class TestRepairHints:
    def test_collected_exists_missing_has_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "collected_exists")
        assert r is not None
        assert not r.passed
        assert len(r.repair_hints) > 0
        assert "collected.json" in r.repair_hints[0]

    def test_collected_exists_empty_has_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "collected_exists")
        assert r is not None
        assert not r.passed
        assert len(r.repair_hints) > 0

    def test_collected_exists_passes_no_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s", "source_tier": 3}])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "collected_exists")
        assert r is not None
        assert r.passed
        assert r.repair_hints == []

    def test_collected_schema_invalid_has_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com"}])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "collected_schema")
        assert r is not None
        assert not r.passed
        assert len(r.repair_hints) > 0
        assert "schema" in r.repair_hints[0].lower()

    def test_collected_schema_passes_no_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s", "source_tier": 3}])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "collected_schema")
        assert r is not None
        assert r.passed
        assert r.repair_hints == []

    def test_source_fidelity_missing_blocker_has_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [
            {"url": "https://example.com/1", "title": "T1", "snippet": "S", "source_tier": 3, "source_file": "sources/missing.md", "fetched_content": ""},
            {"url": "https://example.com/2", "title": "T2", "snippet": "S", "source_tier": 3, "source_file": "sources/also_missing.md", "fetched_content": ""},
        ])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "source_fidelity")
        assert r is not None
        assert not r.passed
        assert r.level == "BLOCKER"
        assert len(r.repair_hints) > 0
        assert "Re-fetch" in r.repair_hints[0]

    def test_source_fidelity_passes_no_repair_hints(self, tmp_path):
        _make_scope(tmp_path)
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        (sources_dir / "abc123.md").write_text("x" * 6000, encoding="utf-8")
        _write_json(tmp_path / "collected.json", [{"url": "https://example.com", "title": "T", "snippet": "S", "source_tier": 3, "source_file": "sources/abc123.md", "fetched_content": "x" * 200}])
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "source_fidelity")
        assert r is not None
        assert r.passed
        assert r.repair_hints == []


class TestDirectionTaggingAndCoverage:
    def _valid_entries(self, tmp_path, directions):
        # 5 entries covering tiers 3,2,1,4,3 with source files so the other
        # search-gate checks pass; only `direction` varies per entry.
        tiers = [3, 2, 1, 4, 3]
        entries = []
        for i, d in enumerate(directions):
            url = f"https://src{i}.example.com"
            sf = _create_source_file(tmp_path, url, "x" * 2100)
            entries.append({
                "url": url, "title": f"Source {i}", "snippet": f"About topic {i}",
                "source_tier": tiers[i], "source_file": sf, "fetched_content": "x" * 2100,
                "direction": d,
            })
        return entries

    def test_tagging_blocks_when_direction_missing(self, tmp_path):
        _make_scope(tmp_path, goal_type="other", search_directions=["AI", "ML"])
        entries = self._valid_entries(tmp_path, ["AI", "ML", "AI", "ML", "other"])
        del entries[0]["direction"]
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "direction_tagging")
        assert r is not None
        assert not r.passed
        assert r.level == "BLOCKER"

    def test_tagging_passes_when_all_tagged(self, tmp_path):
        _make_scope(tmp_path, goal_type="other", search_directions=["AI", "ML"])
        entries = self._valid_entries(tmp_path, ["AI", "ML", "AI", "ML", "other"])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "direction_tagging")
        assert r is not None
        assert r.passed

    def test_tagging_skipped_without_search_directions(self, tmp_path):
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "other", "depth": "standard", "audience": "engineer", "scope_description": "Test", "search_directions": []})
        entries = self._valid_entries(tmp_path, ["AI", "ML", "AI", "ML", "other"])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "direction_tagging")
        assert r is not None
        assert r.passed
        assert "no search_directions" in r.message.lower()

    def test_coverage_blocks_when_declared_direction_untagged(self, tmp_path):
        _make_scope(tmp_path, goal_type="other", search_directions=["AI", "ML"])
        entries = self._valid_entries(tmp_path, ["AI", "AI", "AI", "AI", "AI"])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "direction_coverage")
        assert r is not None
        assert not r.passed
        assert r.level == "BLOCKER"

    def test_coverage_passes_when_all_declared_directions_tagged(self, tmp_path):
        _make_scope(tmp_path, goal_type="other", search_directions=["AI", "ML"])
        entries = self._valid_entries(tmp_path, ["AI", "ML", "AI", "ML", "other"])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        r = _find_result(results, "direction_coverage")
        assert r is not None
        assert r.passed


class TestMinSourcesBlocker:
    def test_standard_requires_5(self, tmp_path):
        _make_scope(tmp_path, depth="standard")
        entries = [{"url": f"https://s{i}.com", "title": f"T{i}", "snippet": "S", "source_tier": 4} for i in range(4)]
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        ms = _find_result(results, "min_sources")
        assert ms is not None
        assert not ms.passed
        assert ms.level == "BLOCKER"
        assert "5" in ms.message

    def test_quick_requires_3(self, tmp_path):
        _make_scope(tmp_path, depth="quick")
        entries = [{"url": f"https://s{i}.com", "title": f"T{i}", "snippet": "S", "source_tier": 4} for i in range(2)]
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        ms = _find_result(results, "min_sources")
        assert ms is not None
        assert not ms.passed
        assert ms.level == "BLOCKER"
        assert "3" in ms.message

    def test_deep_requires_8(self, tmp_path):
        _make_scope(tmp_path, depth="deep")
        entries = [{"url": f"https://s{i}.com", "title": f"T{i}", "snippet": "S", "source_tier": 4} for i in range(7)]
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        ms = _find_result(results, "min_sources")
        assert ms is not None
        assert not ms.passed
        assert ms.level == "BLOCKER"
        assert "8" in ms.message


class TestTierCoverageBlocker:
    def test_missing_route_tier_fails_as_blocker(self, tmp_path):
        config = {
            "sources": {
                "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com"}]},
            },
            "routes": {"tech_selection": {"entry_tier": 2, "path": [2, 3, 4, 1]}},
        }
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "T1", "snippet": "S", "source_tier": 2},
                {"url": "https://b.com", "title": "T2", "snippet": "S", "source_tier": 3},
                {"url": "https://c.com", "title": "T3", "snippet": "S", "source_tier": 4},
            ],
        )
        results = SearchGate(tmp_path, config).check()
        tc = _find_result(results, "tier_coverage")
        assert tc is not None
        assert not tc.passed
        assert tc.level == "BLOCKER"

    def test_repair_hints_include_config_source_suggestions(self, tmp_path):
        config = {
            "sources": {
                "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org", "site_query": "arxiv.org AI"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com", "site_query": "github.com AI"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com"}]},
            },
            "routes": {"tech_selection": {"entry_tier": 2, "path": [2, 3, 4, 1]}},
        }
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "T1", "snippet": "S", "source_tier": 2},
                {"url": "https://b.com", "title": "T2", "snippet": "S", "source_tier": 3},
                {"url": "https://c.com", "title": "T3", "snippet": "S", "source_tier": 4},
            ],
        )
        results = SearchGate(tmp_path, config).check()
        tc = _find_result(results, "tier_coverage")
        assert tc is not None
        assert not tc.passed
        assert len(tc.repair_hints) > 0
        assert any("arXiv" in h for h in tc.repair_hints)
