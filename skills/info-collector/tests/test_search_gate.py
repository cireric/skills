from __future__ import annotations

import json
from pathlib import Path

from scripts.search_gate import SearchGate
from scripts.artifact_checks import CheckResult


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_scope(workdir, goal_type="tech_selection", depth="standard", report_language=None, search_directions=None):
    data = {
        "topic": "Test",
        "goal_type": goal_type,
        "depth": depth,
        "audience": "engineer",
        "scope_description": "Test scope",
        "search_directions": search_directions if search_directions is not None else ["AI", "ML"],
    }
    if report_language is not None:
        data["report_language"] = report_language
    _write_json(workdir / "scope.json", data)


def _make_completed_search_plan(workdir, directions=None):
    if directions is None:
        scope = json.loads((workdir / "scope.json").read_text(encoding="utf-8"))
        directions = scope.get("search_directions", ["AI", "ML"])
    tasks = [{"direction": d, "tier": 4, "status": "completed", "collected_count": 1} for d in directions]
    _write_json(workdir / "search_plan.json", {"tasks": tasks})


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
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML", "fetched_content": "x" * 300},
            ],
        )
        _make_completed_search_plan(tmp_path)
        results = SearchGate(tmp_path).check()
        blockers = [r for r in results if r.level == "BLOCKER" and not r.passed]
        assert not blockers

    def test_returns_list_of_check_results(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        assert isinstance(results, list)
        assert all(isinstance(r, CheckResult) for r in results)


class TestTopicCoverage:
    def test_topic_coverage_blocker_when_uncovered(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://x.com", "title": "Unrelated", "snippet": "Something else"}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert not tc.passed
        assert "BLOCKER" in tc.message or tc.level == "BLOCKER"

    def test_cjk_downgraded_to_warn(self, tmp_path):
        _make_scope(tmp_path, search_directions=["智能体编程框架"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://x.com", "title": "Unrelated", "snippet": "Something else"}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert "CJK" in tc.message

    def test_no_false_positive_substring(self, tmp_path):
        _make_scope(tmp_path, search_directions=["artificial intelligence"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://x.com", "title": "Training RAIN models", "snippet": "About ML"}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert not tc.passed
        assert "artificial intelligence" in tc.message.lower()

    def test_word_boundary_match(self, tmp_path):
        _make_scope(tmp_path, search_directions=["AI"], depth="quick")
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://x.com", "title": "AI advances in 2026", "snippet": "About AI and ML", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert tc.passed

    def test_chinese_topic_coverage(self, tmp_path):
        _make_scope(tmp_path, depth="quick", search_directions=["主流agentic coding框架对比"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "主流agentic coding框架对比", "snippet": "关于框架对比", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert tc.passed

    def test_chinese_topic_coverage_partial(self, tmp_path):
        _make_scope(tmp_path, depth="quick", search_directions=["MCP协议生态与服务器数量"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "MCP 17-month anniversary 97M downloads", "snippet": "Fastest protocol adoption", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert tc.passed

    def test_chinese_topic_coverage_missing(self, tmp_path):
        _make_scope(tmp_path, search_directions=["主流agentic coding框架对比"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "Unrelated", "snippet": "Something else", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert "CJK" in tc.message

    def test_threshold_partial_coverage(self, tmp_path):
        _make_scope(tmp_path, depth="quick", search_directions=["AI coding tools benchmarks pricing"])
        _write_json(
            tmp_path / "collected.json",
            [{"url": "https://a.com", "title": "AI Coding Tools 2026", "snippet": "Benchmarks comparison", "fetched_content": "x" * 300}],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert tc.passed


class TestPerDirectionMinSources:
    def test_depth_quick_passes_with_1_source_per_direction(self, tmp_path):
        _make_scope(tmp_path, depth="quick", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML", "fetched_content": "x" * 300},
            ],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert not any("per_direction_min_sources" in tc.message for _ in [1])

    def test_depth_standard_warns_with_insufficient_sources(self, tmp_path):
        _make_scope(tmp_path, depth="standard", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML", "fetched_content": "x" * 300},
            ],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert "per_direction_min_sources" in tc.message

    def test_depth_deep_warns_with_insufficient_sources(self, tmp_path):
        _make_scope(tmp_path, depth="deep", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI News", "snippet": "About AI", "fetched_content": "x" * 300},
                {"url": "https://b.com", "title": "ML Update", "snippet": "About ML", "fetched_content": "x" * 300},
            ],
        )
        results = SearchGate(tmp_path).check()
        tc = _find_result(results, "topic_coverage")
        assert tc is not None
        assert "per_direction_min_sources" in tc.message
        assert "deep" in tc.message


class TestTierCoverage:
    def test_all_tiers_covered_no_warn(self, tmp_path):
        _make_scope(tmp_path, goal_type="tech_selection")
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI", "snippet": "About AI", "source_tier": 2, "fetched_content": "x" * 800},
                {"url": "https://b.com", "title": "ML", "snippet": "About ML", "source_tier": 1, "fetched_content": "x" * 1000},
            ],
        )
        _make_completed_search_plan(tmp_path)
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
        _make_completed_search_plan(tmp_path)
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
                "panoramic_understanding": {"entry_tier": 4, "path": [4, 3, 1], "optional_tiers": [2]},
            },
        }
        _make_scope(tmp_path, goal_type="panoramic_understanding", search_directions=["AI", "ML"])
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "AI ML", "snippet": "About AI and ML", "source_tier": 4, "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "More AI", "snippet": "About ML too", "source_tier": 3, "fetched_content": "x" * 700},
                {"url": "https://c.com", "title": "Deep AI", "snippet": "About AI research", "source_tier": 1, "fetched_content": "x" * 1100},
            ],
        )
        _make_completed_search_plan(tmp_path)
        results = SearchGate(tmp_path, config).check()
        tier = _find_result(results, "tier_coverage")
        assert tier is not None
        assert tier.passed
        captured = capsys.readouterr()
        assert "optional tiers" in captured.err
        assert "[INFO]" in captured.err


class TestFetchedContentDepth:
    def test_all_entries_have_substantial_content(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "source_tier": 4, "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "B", "snippet": "s", "source_tier": 4, "fetched_content": "y" * 500},
            ],
        )
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert fcd.passed

    def test_empty_fetched_content_blocker(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "source_tier": 4, "fetched_content": "x" * 500},
                {"url": "https://b.com", "title": "B", "snippet": "s", "source_tier": 4},
            ],
        )
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert not fcd.passed
        assert fcd.level == "BLOCKER"
        assert "missing or stub" in fcd.message

    def test_stub_fetched_content_warns(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s", "source_tier": 4, "fetched_content": "short"},
                {"url": "https://b.com", "title": "B", "snippet": "s", "source_tier": 4, "fetched_content": "y" * 500},
            ],
        )
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert not fcd.passed
        assert "stub" in fcd.message

    def test_majority_stub_blocks(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(
            tmp_path / "collected.json",
            [
                {"url": "https://a.com", "title": "A", "snippet": "s"},
                {"url": "https://b.com", "title": "B", "snippet": "s"},
                {"url": "https://c.com", "title": "C", "snippet": "s", "fetched_content": "ok" * 100},
            ],
        )
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert fcd.level == "BLOCKER"

    def test_missing_collected_warns(self, tmp_path):
        _make_scope(tmp_path)
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert fcd.level == "WARN"

    def test_empty_collected_warns(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [])
        results = SearchGate(tmp_path).check()
        fcd = _find_result(results, "fetched_content_depth")
        assert fcd is not None
        assert fcd.level == "WARN"


class TestSearchPlanCompliance:
    def test_no_plan_warns(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s"}])
        results = SearchGate(tmp_path).check()
        spc = _find_result(results, "search_plan_compliance")
        assert spc is not None
        assert spc.passed

    def test_all_completed_passes(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s"}])
        _make_completed_search_plan(tmp_path)
        results = SearchGate(tmp_path).check()
        spc = _find_result(results, "search_plan_compliance")
        assert spc is not None
        assert spc.passed

    def test_pending_tasks_warns(self, tmp_path):
        _make_scope(tmp_path)
        _write_json(tmp_path / "collected.json", [{"url": "https://a.com", "title": "A", "snippet": "s"}])
        _write_json(
            tmp_path / "search_plan.json",
            {"tasks": [{"direction": "AI", "tier": 4, "status": "pending", "collected_count": 0}]},
        )
        results = SearchGate(tmp_path).check()
        spc = _find_result(results, "search_plan_compliance")
        assert spc is not None
        assert not spc.passed
