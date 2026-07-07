from __future__ import annotations

import json
from pathlib import Path

from scripts.artifact_checks import CheckResult
from scripts.lib.utils import compute_url_hash
from scripts.proceed import (
    _check_review_report_exists,
    _gate_final,
    detect_current_phase,
    proceeds,
    write_phase_state,
)
from scripts.reporter import build_front_matter, generate_report
from scripts.report_checks import run_report_checks
from scripts.search_gate import SearchGate



def _make_source_file(workdir, url, content="Test source content for verification."):
    h = compute_url_hash(url)
    sources_dir = workdir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    (sources_dir / f"{h}.md").write_text(content, encoding="utf-8")
    return f"sources/{h}.md"


def _make_collected_entry(url, title, snippet, source_tier,
                          covered_directions=None, fetch_failed=False,
                          source_file=None):
    entry = {
        "url": url,
        "title": title,
        "snippet": snippet,
        "source_tier": source_tier,
        "fetched_content": snippet[:200],
    }
    if covered_directions is not None:
        entry["covered_directions"] = covered_directions
    if fetch_failed:
        entry["fetch_failed"] = True
    if source_file is not None:
        entry["source_file"] = source_file
    return entry



def _write_report_to_reports_dir(workdir, report_content, monkeypatch=None):
    reports_dir = workdir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "test_report.md"
    report_path.write_text(report_content, encoding="utf-8")
    return report_path


class TestTechSelectionHappyPath:
    def test_full_pipeline(self, tmp_path, monkeypatch):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        directions = ["Rust backend", "Go backend"]
        _make_scope(workdir, goal_type="tech_selection", depth="standard",
                     search_directions=directions,
                     scope_description="Rust vs Go for backend services")

        ok, errors = proceeds(workdir, "scope", "search")
        assert ok, f"scope→search failed: {errors}"

        collected = []
        urls_by_tier = {
            2: ["https://doc.rust-lang.org/book/", "https://go.dev/doc/"],
            3: ["https://medium.com/rust-vs-go", "https://thenewstack.io/go-microservices/"],
            4: ["https://reddit.com/r/rust", "https://reddit.com/r/golang"],
            1: ["https://arxiv.org/abs/2401.0001", "https://arxiv.org/abs/2401.0002"],
        }
        for tier, urls in urls_by_tier.items():
            for url in urls:
                sf = _make_source_file(workdir, url)
                collected.append(_make_collected_entry(
                    url=url,
                    title=f"Source {url}",
                    snippet="Rust backend Go backend performance",
                    source_tier=tier,
                    covered_directions=directions,
                    source_file=sf,
                ))
        _write_json(workdir / "collected.json", collected)

        search_plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in search_plan["tasks"]:
            task["status"] = "completed"
        _write_json(workdir / "search_plan.json", search_plan)

        ok, errors = proceeds(workdir, "search", "analysis")
        assert ok, f"search→analysis failed: {errors}"

        all_urls = [e["url"] for e in collected]
        ref_markers = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[:4])
        analysis = {
            "topic": "Rust vs Go for backend services",
            "goal_type": "tech_selection",
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": f"Rust provides memory safety without GC. Go offers simplicity and fast compilation. {ref_markers}",
                    "claims": [
                        {"text": "Rust achieves 0 memory safety bugs in production", "source_urls": all_urls[:2],
                         "evidence_type": "independent_benchmark", "confidence": "high", "precision": "exact",
                         "source_metadata": {"test_conditions": "AWS c5.xlarge, Ubuntu 22.04", "test_date": "2025-Q4", "source_type": "independent_test"}},
                    ],
                },
                {
                    "id": "comparison",
                    "title": "Comparison",
                    "content": f"Rust shows 30% lower latency than Go in web services. {ref_markers}",
                    "claims": [
                        {"text": "Rust 30% lower latency", "source_urls": all_urls[2:4],
                         "evidence_type": "third_party_estimate", "confidence": "medium", "precision": "range"},
                    ],
                },
                {
                    "id": "recommendation",
                    "title": "Recommendation",
                    "content": f"We recommend Rust for latency-critical services. Go is not recommended for sub-millisecond requirements. {ref_markers}",
                    "claims": [
                        {"text": "Rust recommended for latency-critical", "source_urls": all_urls[:2],
                         "evidence_type": "expert_opinion", "confidence": "medium", "precision": "qualitative"},
                    ],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "Data sourced from benchmarks and community reports. | Metric | Rust | Go | |---|---|---| | Latency p99 | 2ms | 3ms |",
                    "claims": [],
                },
            ],
        }
        _write_json(workdir / "analysis.json", analysis)

        ok, errors = proceeds(workdir, "analysis", "review")
        assert ok, f"analysis→review failed: {errors}"

        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass**\n", encoding="utf-8")

        write_phase_state(workdir, "post_review")
        ok, errors = proceeds(workdir, "review", "final")
        assert ok, f"review→final failed: {errors}"

        assert detect_current_phase(workdir) == "post_final"

        report = generate_report(
            workdir / "analysis.json",
            workdir / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=len(collected),
        )
        report_path = _write_report_to_reports_dir(workdir, report)
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        errors = _gate_final(workdir)
        assert errors == [], f"report BLOCKERs: {errors}"

        report_checks = run_report_checks(report_path)
        blockers = [r for r in report_checks if r.level == "BLOCKER" and not r.passed]
        assert blockers == [], f"report BLOCKER checks failed: {[b.message for b in blockers]}"

        assert "---" in report
        assert "topic:" in report
        assert "goal_type:" in report
        assert "review_status: passed" in report
        assert "verification_required: true" in report

        assert "[&#91;" in report
        assert "(#refs)" in report

        ref_section = report[report.rfind("## References"):]
        assert "Tier 1" in ref_section or "Tier 2" in ref_section or "Tier 3" in ref_section


class TestAcademicResearchChinese:
    def test_full_pipeline_chinese(self, tmp_path, monkeypatch):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        directions = ["代码生成", "大语言模型应用"]
        _make_scope(workdir, goal_type="academic_research", depth="deep",
                     report_language="zh",
                     english_title="LLM Code Generation Application Research",
                     search_directions=directions,
                     scope_description="大语言模型在代码生成中的应用研究")

        ok, errors = proceeds(workdir, "scope", "search")
        assert ok, f"scope→search failed: {errors}"

        collected = []
        tier1_urls = [
            "https://arxiv.org/abs/2401.0100",
            "https://arxiv.org/abs/2401.0101",
            "https://cnki.net/article/001",
            "https://semanticscholar.org/paper/abc",
            "https://aclanthology.org/2024.acl-long.1",
        ]
        for url in tier1_urls:
            sf = _make_source_file(workdir, url)
            collected.append(_make_collected_entry(
                url=url,
                title=f"Paper on LLM code generation",
                snippet="大语言模型 代码生成 应用 研究",
                source_tier=1,
                covered_directions=directions,
                source_file=sf,
            ))
        _write_json(workdir / "collected.json", collected)

        search_plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in search_plan["tasks"]:
            task["status"] = "completed"
        _write_json(workdir / "search_plan.json", search_plan)

        ok, errors = proceeds(workdir, "search", "analysis")
        assert ok, f"search→analysis failed: {errors}"

        all_urls = [e["url"] for e in collected]
        abstract_refs = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[:3])
        findings_refs = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[2:5])
        analysis = {
            "topic": "大语言模型在代码生成中的应用研究",
            "goal_type": "academic_research",
            "sections": [
                {
                    "id": "abstract",
                    "title": "Abstract",
                    "content": f"This paper surveys LLM applications in code generation. {abstract_refs}",
                    "claims": [
                        {"text": "LLMs achieve 60% pass@1 on HumanEval", "source_urls": all_urls[:2],
                         "evidence_type": "independent_benchmark", "confidence": "high", "precision": "exact",
                         "source_metadata": {"test_conditions": "HumanEval benchmark, greedy decoding", "test_date": "2024-Q1", "source_type": "independent_test"}},
                    ],
                },
                {
                    "id": "findings",
                    "title": "Findings",
                    "content": f"Key findings on code generation quality and capability. {findings_refs}",
                    "claims": [
                        {"text": "Code generation quality improves with model scale", "source_urls": all_urls[2:4],
                         "evidence_type": "qualitative_trend", "confidence": "medium", "precision": "qualitative"},
                    ],
                },
                {
                    "id": "references",
                    "title": "References",
                    "content": "Survey of relevant literature.",
                    "claims": [],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "Systematic review methodology. | Aspect | Detail | |---|---| | Scope | LLM code gen | | Papers | 50+ |",
                    "claims": [],
                },
            ],
        }
        _write_json(workdir / "analysis.json", analysis)

        ok, errors = proceeds(workdir, "analysis", "review")
        assert ok, f"analysis→review failed: {errors}"

        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass**\n", encoding="utf-8")

        write_phase_state(workdir, "post_review")
        ok, errors = proceeds(workdir, "review", "final")
        assert ok, f"review→final failed: {errors}"

        report = generate_report(
            workdir / "analysis.json",
            workdir / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=len(collected),
            report_language="zh",
        )
        assert "参考文献" in report
        assert "数据来源" in report

        assert "---" in report
        assert "review_status: passed" in report
        assert "verification_required: true" in report

        report_path = _write_report_to_reports_dir(workdir, report)
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        errors = _gate_final(workdir)
        assert errors == [], f"report BLOCKERs: {errors}"


class TestMarketAnalysisUnreviewed:
    def test_unreviewed_pipeline(self, tmp_path, monkeypatch):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        directions = ["AI agent market", "framework trends 2026"]
        _make_scope(workdir, goal_type="market_analysis", depth="standard",
                     search_directions=directions,
                     scope_description="AI agent framework market 2026")

        ok, errors = proceeds(workdir, "scope", "search")
        assert ok, f"scope→search failed: {errors}"

        collected = []
        url_tier_map = [
            ("https://thenewstack.io/ai-agents-2026", 3),
            ("https://reddit.com/r/LocalLLaMA/agents", 4),
            ("https://news.ycombinator.com/item?id=12345", 4),
            ("https://zhihu.com/question/ai-agents", 4),
            ("https://arxiv.org/abs/2401.0200", 1),
            ("https://go.dev/doc/ai-frameworks", 2),
        ]
        for url, tier in url_tier_map:
            sf = _make_source_file(workdir, url)
            collected.append(_make_collected_entry(
                url=url,
                title=f"Source on AI agents {tier}",
                snippet="AI agent framework market trends 2026",
                source_tier=tier,
                covered_directions=directions,
                source_file=sf,
            ))
        _write_json(workdir / "collected.json", collected)

        search_plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in search_plan["tasks"]:
            task["status"] = "completed"
        _write_json(workdir / "search_plan.json", search_plan)

        ok, errors = proceeds(workdir, "search", "analysis")
        assert ok, f"search→analysis failed: {errors}"

        all_urls = [e["url"] for e in collected]
        ref_markers = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[:4])
        analysis = {
            "topic": "AI agent framework market 2026",
            "goal_type": "market_analysis",
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": f"AI agent frameworks are rapidly evolving. {ref_markers}",
                    "claims": [
                        {"text": "AI agent market reached $2B in 2025", "source_urls": all_urls[:2],
                         "evidence_type": "third_party_estimate", "confidence": "medium", "precision": "range"},
                    ],
                },
                {
                    "id": "data",
                    "title": "Data",
                    "content": f"Market data and growth indicators. {ref_markers}",
                    "claims": [
                        {"text": "120% year-over-year growth", "source_urls": all_urls[2:4],
                         "evidence_type": "third_party_estimate", "confidence": "low", "precision": "range"},
                    ],
                },
                {
                    "id": "trends",
                    "title": "Trends",
                    "content": "Emerging trends in agent frameworks.",
                    "claims": [],
                },
                {
                    "id": "conclusion",
                    "title": "Conclusion",
                    "content": "The market continues to expand.",
                    "claims": [],
                },
                {
                    "id": "methodology",
                    "title": "Methodology",
                    "content": "Data sourced from industry reports and community signals. | Source | Type | |---|---| | Tier 3 | Industry | | Tier 4 | Community |",
                    "claims": [],
                },
            ],
        }
        _write_json(workdir / "analysis.json", analysis)

        ok, errors = proceeds(workdir, "analysis", "review")
        assert ok, f"analysis→review failed: {errors}"

        (workdir / "review_fallback.log").write_text(
            "2026-07-07 | user chose: unreviewed\n", encoding="utf-8")

        write_phase_state(workdir, "post_review")
        ok, errors = proceeds(workdir, "review", "final")
        assert ok, f"review→final failed: {errors}"

        rr_check = _check_review_report_exists(workdir)
        assert rr_check.passed
        assert "Skipped" in rr_check.message

        report = generate_report(
            workdir / "analysis.json",
            workdir / "scope.json",
            review_status="unreviewed",
            search_rounds=1,
            source_count=len(collected),
        )
        assert "review_status: unreviewed" in report
        assert "verification_required: true" in report

        report_path = _write_report_to_reports_dir(workdir, report)
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        errors = _gate_final(workdir)
        assert errors == [], f"report BLOCKERs: {errors}"


class TestFactCheckMinimal:
    def test_minimal_pipeline(self, tmp_path, monkeypatch):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        directions = ["Rust memory safety"]
        _make_scope(workdir, goal_type="fact_check", depth="quick",
                     search_directions=directions,
                     scope_description="Is Rust memory-safe without GC?")

        ok, errors = proceeds(workdir, "scope", "search")
        assert ok, f"scope→search failed: {errors}"

        url1 = "https://arxiv.org/abs/rust-memory-safety"
        url2 = "https://doc.rust-lang.org/book/ch04-00.html"
        sf1 = _make_source_file(workdir, url1, content="Rust ownership model provides memory safety guarantees.")
        collected = [
            _make_collected_entry(
                url=url1, title="Rust Memory Safety", snippet="Rust memory safety ownership",
                source_tier=1, covered_directions=directions, source_file=sf1),
            _make_collected_entry(
                url=url2, title="Rust Book Ownership", snippet="Rust ownership system memory safe",
                source_tier=2, fetch_failed=True),
        ]
        _write_json(workdir / "collected.json", collected)

        search_plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in search_plan["tasks"]:
            task["status"] = "completed"
        _write_json(workdir / "search_plan.json", search_plan)

        sg = SearchGate(workdir)
        fidelity = sg._check_source_fidelity()
        assert fidelity.passed, f"source_fidelity failed: {fidelity.message}"

        ok, errors = proceeds(workdir, "search", "analysis")
        assert ok, f"search→analysis failed: {errors}"

        analysis = {
            "topic": "Is Rust memory-safe without GC?",
            "goal_type": "fact_check",
            "sections": [
                {
                    "id": "claims",
                    "title": "Claims",
                    "content": f"Rust provides memory safety without garbage collection through ownership {{{{ref:{url1}}}}}.",
                    "claims": [
                        {"text": "Rust is memory-safe without GC", "source_urls": [url1],
                         "evidence_type": "official_data", "confidence": "high", "precision": "qualitative",
                         "source_metadata": {"test_conditions": "Compiler verification", "test_date": "2024", "source_type": "independent_test"}},
                    ],
                },
                {
                    "id": "evidence",
                    "title": "Evidence",
                    "content": f"The ownership model enforces safety at compile time {{{{ref:{url1}}}}}.",
                    "claims": [
                        {"text": "Ownership model enforces compile-time safety", "source_urls": [url1],
                         "evidence_type": "official_data", "confidence": "high", "precision": "qualitative"},
                    ],
                },
                {
                    "id": "conclusion",
                    "title": "Conclusion",
                    "content": f"Rust achieves memory safety without GC via its ownership system {{{{ref:{url1}}}}}.",
                    "claims": [
                        {"text": "Rust achieves memory safety without GC", "source_urls": [url1],
                         "evidence_type": "official_data", "confidence": "high", "precision": "qualitative"},
                    ],
                },
            ],
        }
        _write_json(workdir / "analysis.json", analysis)

        ok, errors = proceeds(workdir, "analysis", "review")
        assert ok, f"analysis→review failed: {errors}"

        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass**\n", encoding="utf-8")

        write_phase_state(workdir, "post_review")
        ok, errors = proceeds(workdir, "review", "final")
        assert ok, f"review→final failed: {errors}"

        report = generate_report(
            workdir / "analysis.json",
            workdir / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=len(collected),
        )
        report_path = _write_report_to_reports_dir(workdir, report)
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        errors = _gate_final(workdir)
        assert errors == [], f"report BLOCKERs: {errors}"

        assert "## Claims" in report
        assert "## Evidence" in report
        assert "## Conclusion" in report


class TestExploratoryDeepDive:
    def test_exploratory_with_key_insights(self, tmp_path, monkeypatch):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        directions = ["agentic coding trends", "AI coding assistants"]
        _make_scope(workdir, goal_type="exploratory", depth="quick",
                     search_directions=directions,
                     scope_description="Emerging trends in agentic coding")

        config = {
            "sources": {
                "4": {"sources": [
                    {"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"},
                    {"name": "HN", "domain": "news.ycombinator.com", "site_query": "news.ycombinator.com"},
                ]},
                "3": {"sources": [
                    {"name": "Medium", "domain": "medium.com", "site_query": "medium.com"},
                ]},
                "2": {"sources": [
                    {"name": "GitHub", "domain": "github.com", "site_query": "github.com"},
                ]},
            },
            "routes": {"exploratory": {"entry_tier": 4, "path": [4, 3, 2]}},
        }

        ok, errors = proceeds(workdir, "scope", "search", config)
        assert ok, f"scope→search failed: {errors}"

        collected = []
        url_tier_map = [
            ("https://reddit.com/r/LocalLLaMA/agents2", 4),
            ("https://news.ycombinator.com/item?id=agent-coding", 4),
            ("https://medium.com/agentic-coding-trends", 3),
            ("https://github.com/features/copilot", 2),
        ]
        for url, tier in url_tier_map:
            sf = _make_source_file(workdir, url)
            collected.append(_make_collected_entry(
                url=url,
                title=f"Agentic coding source tier {tier}",
                snippet="agentic coding trends AI assistants",
                source_tier=tier,
                covered_directions=directions,
                source_file=sf,
            ))
        _write_json(workdir / "collected.json", collected)

        search_plan = json.loads((workdir / "search_plan.json").read_text(encoding="utf-8"))
        for task in search_plan["tasks"]:
            task["status"] = "completed"
        _write_json(workdir / "search_plan.json", search_plan)

        ok, errors = proceeds(workdir, "search", "analysis")
        assert ok, f"search→analysis failed: {errors}"

        all_urls = [e["url"] for e in collected]
        overview_refs = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[:3])
        trends_refs = " ".join(f"{{{{ref:{u}}}}}" for u in all_urls[1:])
        analysis = {
            "topic": "Emerging trends in agentic coding",
            "goal_type": "exploratory",
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": f"Agentic coding represents a shift from autocomplete to autonomous agents. {overview_refs}",
                    "depth_strategy": "overview",
                    "key_insights": [
                        {"text": "Agentic coding shifts from autocomplete to autonomous workflows",
                         "source_urls": all_urls[:2]},
                        {"text": "Community adoption is growing rapidly across platforms",
                         "source_urls": all_urls[1:3]},
                    ],
                    "tensions": [],
                    "claims": [],
                },
                {
                    "id": "trends",
                    "title": "Key Trends",
                    "content": f"AI coding assistants are evolving toward autonomous agents. {trends_refs}",
                    "depth_strategy": "deep_dive",
                    "key_insights": [
                        {"text": "Multi-step agent workflows are replacing single-turn completions",
                         "source_urls": all_urls[2:4]},
                        {"text": "Open-source agents are catching up to commercial offerings",
                         "source_urls": all_urls[:2]},
                    ],
                    "tensions": [],
                    "claims": [],
                },
            ],
        }
        _write_json(workdir / "analysis.json", analysis)

        ok, errors = proceeds(workdir, "analysis", "review")
        assert ok, f"analysis→review failed: {errors}"

        from scripts.artifact_checks import check_key_insights_coverage
        ki_check = check_key_insights_coverage(workdir, "exploratory")
        assert ki_check.passed, f"key_insights_coverage failed: {ki_check.message}"

        (workdir / "review_report.md").write_text(
            "## Overall Verdict\n**pass**\n", encoding="utf-8")

        write_phase_state(workdir, "post_review")
        ok, errors = proceeds(workdir, "review", "final")
        assert ok, f"review→final failed: {errors}"

        report = generate_report(
            workdir / "analysis.json",
            workdir / "scope.json",
            review_status="passed",
            search_rounds=1,
            source_count=len(collected),
        )
        report_path = _write_report_to_reports_dir(workdir, report)
        monkeypatch.setattr("scripts.proceed._find_report_path", lambda w: report_path)

        errors = _gate_final(workdir)
        assert errors == [], f"report BLOCKERs: {errors}"

        assert "**Key Insights:**" in report


class TestSearchGateDirectChecks:
    def test_tier_coverage_academic_research_tier1_only(self, tmp_path):
        workdir = tmp_path
        _make_scope(workdir, goal_type="academic_research", depth="deep",
                     search_directions=["deep learning"])
        collected = [
            _make_collected_entry(
                url="https://arxiv.org/abs/test1", title="Paper 1",
                snippet="deep learning research", source_tier=1,
                covered_directions=["deep learning"],
                source_file=_make_source_file(workdir, "https://arxiv.org/abs/test1")),
            _make_collected_entry(
                url="https://arxiv.org/abs/test2", title="Paper 2",
                snippet="deep learning methods", source_tier=1,
                covered_directions=["deep learning"],
                source_file=_make_source_file(workdir, "https://arxiv.org/abs/test2")),
        ]
        _write_json(workdir / "collected.json", collected)
        _make_completed_search_plan(workdir, directions=["deep learning"])

        sg = SearchGate(workdir)
        tier_check = sg._check_tier_coverage()
        assert tier_check.passed, f"tier_coverage should pass with Tier 1 only for academic_research: {tier_check.message}"

    def test_source_fidelity_with_fetch_failed_exempt(self, tmp_path):
        workdir = tmp_path
        _make_scope(workdir, goal_type="fact_check", depth="quick",
                     search_directions=["test"])
        url1 = "https://arxiv.org/abs/fidelity-test"
        sf = _make_source_file(workdir, url1)
        collected = [
            _make_collected_entry(
                url=url1, title="Source with file", snippet="test",
                source_tier=1, source_file=sf),
            _make_collected_entry(
                url="https://doc.example.com/failed", title="Failed fetch",
                snippet="test", source_tier=2, fetch_failed=True),
        ]
        _write_json(workdir / "collected.json", collected)

        sg = SearchGate(workdir)
        fidelity = sg._check_source_fidelity()
        assert fidelity.passed, f"source_fidelity should pass: {fidelity.message}"

    def test_topic_coverage_with_covered_directions(self, tmp_path):
        workdir = tmp_path
        _make_scope(workdir, goal_type="tech_selection", depth="standard",
                     search_directions=["Rust performance", "Go concurrency"])
        url = "https://example.com/covered"
        collected = [
            _make_collected_entry(
                url=url, title="Test", snippet="test",
                source_tier=2, covered_directions=["Rust performance", "Go concurrency"],
                source_file=_make_source_file(workdir, url)),
            _make_collected_entry(
                url="https://example.com/covered2", title="Test2",
                snippet="Rust performance Go concurrency",
                source_tier=3,
                source_file=_make_source_file(workdir, "https://example.com/covered2")),
            _make_collected_entry(
                url="https://example.com/covered3", title="Test3",
                snippet="Rust Go backend comparison",
                source_tier=4,
                source_file=_make_source_file(workdir, "https://example.com/covered3")),
        ]
        _write_json(workdir / "collected.json", collected)
        _make_completed_search_plan(workdir, directions=["Rust performance", "Go concurrency"])

        sg = SearchGate(workdir)
        tc = sg._check_topic_coverage()
        assert tc.passed, f"topic_coverage should pass: {tc.message}"


class TestReportChecksDirect:
    def test_front_matter_required_fields(self, tmp_path):
        report = "---\ntopic: T\ngoal_type: fact_check\ndate: 2026-07-07\nreview_status: passed\nverification_required: true\n---\n## Claims\nContent.\n"
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")

        results = run_report_checks(report_path)
        fm_check = next(r for r in results if r.name == "report_front_matter")
        assert fm_check.passed, f"front matter should pass: {fm_check.message}"

    def test_dangling_refs_detected(self, tmp_path):
        report = "---\ntopic: T\ngoal_type: other\ndate: 2026-07-07\nreview_status: passed\n---\nContent with [&#91;99&#93;](#refs).\n\n## References\n- [1] [Title](https://a.com)\n"
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")

        results = run_report_checks(report_path)
        dangling = next(r for r in results if r.name == "report_dangling_refs")
        assert not dangling.passed

    def test_no_orphaned_defs(self, tmp_path):
        report = "---\ntopic: T\ngoal_type: other\ndate: 2026-07-07\nreview_status: passed\n---\nContent with [&#91;1&#93;](#refs).\n\n## References\n- [1] [Title](https://a.com)\n- [2] [Orphan](https://b.com)\n"
        report_path = tmp_path / "report.md"
        report_path.write_text(report, encoding="utf-8")

        results = run_report_checks(report_path)
        orphaned = next(r for r in results if r.name == "report_orphaned_defs")
        assert not orphaned.passed


class TestPipelineStateConsistency:
    def test_state_advances_through_phases(self, tmp_path):
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        config = {
            "sources": {"4": {"sources": [{"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"}]}},
            "routes": {"exploratory": {"entry_tier": 4, "path": [4]}},
        }

        _make_scope(workdir, goal_type="exploratory", depth="quick",
                     search_directions=["t1"])
        proceeds(workdir, "scope", "search", config)
        assert detect_current_phase(workdir) == "post_search"

        url = "https://example.com/state-test"
        sf = _make_source_file(workdir, url)
        _write_json(workdir / "collected.json", [
            _make_collected_entry(url=url, title="t1 info", snippet="t1",
                                  source_tier=4, source_file=sf,
                                  covered_directions=["t1"]),
        ])
        _make_completed_search_plan(workdir, directions=["t1"])

        proceeds(workdir, "search", "analysis")
        assert detect_current_phase(workdir) == "post_analysis"

        analysis = {"topic": "t", "goal_type": "exploratory", "sections": [
            {"id": "overview", "title": "Overview", "content": "test overview", "claims": [],
             "key_insights": [{"text": "insight 1", "source_urls": [url]}, {"text": "insight 2", "source_urls": [url]}]},
            {"id": "findings", "title": "Findings", "content": "test findings", "claims": []},
        ]}
        _write_json(workdir / "analysis.json", analysis)

        proceeds(workdir, "analysis", "review")
        assert detect_current_phase(workdir) == "post_review"

        (workdir / "review_report.md").write_text("## Verdict\n**pass**\n", encoding="utf-8")
        write_phase_state(workdir, "post_review")

        proceeds(workdir, "review", "final")
        assert detect_current_phase(workdir) == "post_final"
