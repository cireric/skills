from __future__ import annotations

import json
from pathlib import Path

from scripts.search_gate import SearchGate
from scripts.artifact_checks import CheckResult, check_subagent_delegation, check_direction_coverage, check_facet_coverage, check_key_insights_coverage
from scripts.lib.utils import compute_url_hash


def _find_result(results: list[CheckResult], name: str) -> CheckResult | None:
    return next((r for r in results if r.name == name), None)


def _create_source_file(workdir, url, content="full content"):
    sources_dir = workdir / "sources"
    sources_dir.mkdir(exist_ok=True)
    h = compute_url_hash(url)
    path = sources_dir / f"{h}.md"
    path.write_text(content, encoding="utf-8")
    return f"sources/{h}.md"


class TestSourceFidelityContentDepth:
    def _build_collected(self, workdir, entries_spec):
        entries = []
        for url, content in entries_spec:
            entry = {"url": url, "title": "T", "snippet": "S", "source_tier": 3, "fetched_content": content[:200]}
            if content:
                sf = _create_source_file(workdir, url, content)
                entry["source_file"] = sf
            entries.append(entry)
        return entries

    def test_all_deep_pass(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, [
            (f"https://example.com/{i}", "x" * 5000) for i in range(5)
        ])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed

    def test_40pct_shallow_blocker(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, [
            (f"https://example.com/{i}", "x" * 200 if i < 4 else "x" * 5000)
            for i in range(10)
        ])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "BLOCKER"
        assert "summary-only" in sf.message or "< 2000" in sf.message

    def test_20pct_shallow_warn(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, [
            (f"https://example.com/{i}", "x" * 200 if i < 1 else "x" * 5000)
            for i in range(5)
        ])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.level == "WARN"

    def test_60pct_thin_warn(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, [
            (f"https://example.com/{i}", "x" * 3000 if i < 3 else "x" * 8000)
            for i in range(5)
        ])
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert not sf.passed
        assert sf.level == "WARN"
        assert "< 5000" in sf.message

    def test_fetch_failed_exempt_from_depth(self, tmp_path):
        _make_scope(tmp_path)
        entries = self._build_collected(tmp_path, [
            (f"https://example.com/{i}", "x" * 5000) for i in range(3)
        ])
        entries.append({"url": "https://example.com/failed", "title": "T", "snippet": "S", "source_tier": 3, "fetch_failed": True, "fetched_content": ""})
        _write_json(tmp_path / "collected.json", entries)
        results = SearchGate(tmp_path).check()
        sf = _find_result(results, "source_fidelity")
        assert sf is not None
        assert sf.passed


class TestSubagentDelegation:
    def test_single_section_skipped(self, tmp_path):
        analysis = {"topic": "T", "goal_type": "other", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_subagent_delegation(tmp_path)
        assert result.passed

    def test_multi_section_no_files_blocker(self, tmp_path):
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "tools", "title": "Tools", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "protocols", "title": "Protocols", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_subagent_delegation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"

    def test_multi_section_all_files_pass(self, tmp_path):
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "tools", "title": "Tools", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        (tmp_path / "analysis_section_overview.json").write_text("{}", encoding="utf-8")
        (tmp_path / "analysis_section_tools.json").write_text("{}", encoding="utf-8")
        result = check_subagent_delegation(tmp_path)
        assert result.passed

    def test_multi_section_partial_files_blocker(self, tmp_path):
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "tools", "title": "Tools", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        (tmp_path / "analysis_section_overview.json").write_text("{}", encoding="utf-8")
        result = check_subagent_delegation(tmp_path)
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "tools" in result.message

    def test_no_analysis_file_skipped(self, tmp_path):
        result = check_subagent_delegation(tmp_path)
        assert result.passed


class TestDirectionCoverage:
    def test_no_search_directions_skipped(self, tmp_path):
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "panoramic_understanding", "depth": "standard", "audience": "engineer", "scope_description": "Test"})
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_direction_coverage(tmp_path)
        assert result.passed
        assert "no search_directions" in result.message.lower()

    def test_all_directions_covered_pass(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI safety", "ML benchmarks"])
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "ai_safety", "title": "AI Safety Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "ml_benchmarks", "title": "ML Benchmarks", "content": "text", "depth_strategy": "deep_dive", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_direction_coverage(tmp_path)
        assert result.passed

    def test_some_directions_uncovered_warn(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI safety", "ML benchmarks", "edge computing"])
        collected = [
            {"url": "https://a.com/safety", "title": "S", "snippet": "x", "source_tier": 1, "fetched_content": "x", "source_file": "sources/a.md", "direction": "AI safety"},
            {"url": "https://b.com/bench", "title": "B", "snippet": "x", "source_tier": 1, "fetched_content": "x", "source_file": "sources/b.md", "direction": "ML benchmarks"},
        ]
        _write_json(tmp_path / "collected.json", collected)
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "ai_safety", "title": "AI Safety", "content": "text", "depth_strategy": "overview",
             "key_insights": [], "tensions": [], "claims": [{"summary": "c", "sources": ["https://other.com/x"]}]},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_direction_coverage(tmp_path)
        assert not result.passed
        assert result.level == "WARN"
        assert "ai safety" in result.message or "ml benchmarks" in result.message

    def test_empty_search_directions_list_skipped(self, tmp_path):
        _write_json(tmp_path / "scope.json", {"topic": "T", "goal_type": "panoramic_understanding", "depth": "standard", "audience": "engineer", "scope_description": "Test", "search_directions": []})
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_direction_coverage(tmp_path)
        assert result.passed


class TestFacetCoverage:
    def _collected(self, tmp_path, tier_entries, community_hosts):
        entries = []
        i = 0
        for tier in tier_entries:
            entries.append({"url": f"https://t{tier}s{i}.example.com", "title": f"T{i}",
                            "snippet": "s", "source_tier": tier, "fetched_content": "x"})
            i += 1
        for host in community_hosts:
            entries.append({"url": f"https://{host}/p", "title": "C", "snippet": "s",
                            "source_tier": 4, "fetched_content": "x"})
            i += 1
        return entries

    def _analysis_with_limitation(self, url):
        return {"sections": [{"id": "s1", "claims": [
            {"summary": "The model has a known limitation in long-context reasoning",
             "sources": [url]},
        ]}]}

    def test_passes_when_all_facets_covered(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=[])
        entries = self._collected(tmp_path, [1, 2, 3, 4], ["huggingface.co", "reddit.com"])
        _write_json(tmp_path / "collected.json", entries)
        _write_json(tmp_path / "analysis.json", self._analysis_with_limitation("https://t1s0.example.com"))
        result = check_facet_coverage(tmp_path)
        assert result.passed
        assert result.level == "WARN"

    def test_warns_when_tier12_missing(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=[])
        entries = self._collected(tmp_path, [3, 4], ["huggingface.co", "reddit.com"])
        _write_json(tmp_path / "collected.json", entries)
        _write_json(tmp_path / "analysis.json", self._analysis_with_limitation("https://t3s0.example.com"))
        result = check_facet_coverage(tmp_path)
        assert not result.passed
        assert "technical_architecture" in result.message

    def test_warns_single_platform_community(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=[])
        entries = self._collected(tmp_path, [1, 2, 3], ["huggingface.co"])
        _write_json(tmp_path / "collected.json", entries)
        _write_json(tmp_path / "analysis.json", self._analysis_with_limitation("https://t1s0.example.com"))
        result = check_facet_coverage(tmp_path)
        assert not result.passed
        assert "community_ecosystem" in result.message or "single platform" in result.message.lower()


class TestKeyInsightsCoverageTensions:
    def test_tensions_empty_sources_warn(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding")
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview",
             "key_insights": [{"summary": "insight", "sources": ["https://a.com", "https://b.com"]}],
             "tensions": [{"summary": "tension", "sources": []}],
             "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "tensions[0]" in result.message

    def test_tensions_sufficient_sources_pass(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding")
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview",
             "key_insights": [{"summary": "insight1", "sources": ["https://a.com", "https://b.com"]}, {"summary": "insight2", "sources": ["https://c.com", "https://d.com"]}],
             "tensions": [{"summary": "tension", "sources": ["https://a.com", "https://b.com"]}],
             "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert result.passed

    def test_mixed_key_insights_and_tensions_empty_sources_warn(self, tmp_path):
        _make_scope(tmp_path, goal_type="panoramic_understanding")
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview",
             "key_insights": [{"summary": "insight1", "sources": ["https://a.com", "https://b.com"]}, {"summary": "insight2", "sources": []}],
             "tensions": [{"summary": "tension1", "sources": []}],
             "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        result = check_key_insights_coverage(tmp_path, "panoramic_understanding")
        assert not result.passed
        assert "key_insights[1]" in result.message
        assert "tensions[0]" in result.message
