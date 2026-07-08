from __future__ import annotations

import json
from pathlib import Path

from scripts.search_gate import SearchGate
from scripts.artifact_checks import CheckResult, check_subagent_delegation
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
        _make_completed_search_plan(tmp_path)
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
        _make_completed_search_plan(tmp_path)
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
        _make_completed_search_plan(tmp_path)
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
        _make_completed_search_plan(tmp_path)
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
        _make_completed_search_plan(tmp_path)
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
        assert "analysis_section_" in result.message

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

    def test_multi_section_partial_files_warn(self, tmp_path):
        analysis = {"topic": "T", "goal_type": "panoramic_understanding", "sections": [
            {"id": "overview", "title": "Overview", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
            {"id": "tools", "title": "Tools", "content": "text", "depth_strategy": "overview", "key_insights": [], "tensions": [], "claims": []},
        ]}
        _write_json(tmp_path / "analysis.json", analysis)
        (tmp_path / "analysis_section_overview.json").write_text("{}", encoding="utf-8")
        result = check_subagent_delegation(tmp_path)
        assert not result.passed
        assert result.level == "WARN"
        assert "tools" in result.message

    def test_no_analysis_file_skipped(self, tmp_path):
        result = check_subagent_delegation(tmp_path)
        assert result.passed
