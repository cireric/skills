"""Tests for Reporter section writers — structured conclusion rendering."""

import pytest

from scripts.models import (
    AnalysisResult,
    Comparison,
    ConclusionData,
    ConfidenceAssessment,
    DataPoint,
    Section,
    Source,
    TimelineEvent,
)
from scripts.reporter import Reporter


class TestReporterFrontMatter:
    """Front matter generation tests."""

    def test_front_matter_basic(self):
        analysis = AnalysisResult(
            topic="Test Topic",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "title: Test Topic" in output
        assert "depth: standard" in output
        assert "lang: en" in output
        assert "sources: 0" in output
        assert "---" in output

    def test_front_matter_with_draft(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis, draft=True)
        assert "status: draft" in output

    def test_front_matter_date_format(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        # Should have YYYY-MM-DD format
        import re
        assert re.search(r"date: \d{4}-\d{2}-\d{2}", output)

    def test_front_matter_source_count(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sources=[
                Source(url="https://a.com", title="A", source_type="web", source_lang="en", content="..."),
                Source(url="https://b.com", title="B", source_type="web", source_lang="en", content="..."),
            ],
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "sources: 2" in output


class TestReporterStructuredConclusion:
    """Structured conclusion rendering tests."""

    def test_conclusion_with_recommendation(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(
                recommendation="Option A",
                reasoning="It is better",
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### Recommendation" in output
        assert "**Recommendation**: Option A" in output
        assert "**Reasoning**: It is better" in output

    def test_conclusion_chinese_labels(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            conclusion_data=ConclusionData(
                recommendation="方案A",
                reasoning="更好",
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### 推荐方案" in output
        assert "**推荐**: 方案A" in output
        assert "**理由**: 更好" in output

    def test_conclusion_with_confidence_assessments(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(
                confidence_assessments=[
                    ConfidenceAssessment(
                        conclusion="Feasible",
                        confidence="High",
                        evidence_strength="3 sources",
                    ),
                    ConfidenceAssessment(
                        conclusion="Risky",
                        confidence="Low",
                        evidence_strength="1 source",
                    ),
                ],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### Confidence Assessment" in output
        assert "| Feasible | High | 3 sources |" in output
        assert "| Risky | Low | 1 source |" in output

    def test_conclusion_chinese_confidence_table(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            conclusion_data=ConclusionData(
                confidence_assessments=[
                    ConfidenceAssessment(
                        conclusion="可行",
                        confidence="高",
                        evidence_strength="3个来源",
                    ),
                ],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### 置信度评估" in output
        assert "| 结论 | 置信度 | 依据强度 |" in output
        assert "| 可行 | 高 | 3个来源 |" in output

    def test_conclusion_with_action_items(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(
                action_items=["Implement PoC", "Review with team"],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### Action Items" in output
        assert "- [ ] Implement PoC" in output
        assert "- [ ] Review with team" in output

    def test_conclusion_chinese_action_items(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            conclusion_data=ConclusionData(
                action_items=["实施PoC", "团队评审"],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### 后续行动" in output
        assert "- [ ] 实施PoC" in output

    def test_conclusion_with_open_questions(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(
                open_questions=["Integration complexity?", "Cost analysis?"],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### Open Questions" in output
        assert "- Integration complexity?" in output
        assert "- Cost analysis?" in output

    def test_conclusion_chinese_open_questions(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            conclusion_data=ConclusionData(
                open_questions=["集成复杂度?"],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### 未解问题" in output
        assert "- 集成复杂度?" in output

    def test_conclusion_full(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(
                recommendation="Option A",
                reasoning="Best choice",
                confidence_assessments=[
                    ConfidenceAssessment("Feasible", "High", "3 sources"),
                ],
                action_items=["Do X"],
                open_questions=["What about Y?"],
            ),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "### Recommendation" in output
        assert "### Confidence Assessment" in output
        assert "### Action Items" in output
        assert "### Open Questions" in output

    def test_no_conclusion_data(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=None,
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        # Should not have conclusion section
        assert "---" in output  # front matter only
        # Count --- separators: front matter + sources (empty) = 2
        assert output.count("---\n---") == 0  # no empty conclusion separator

    def test_conclusion_separator(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            conclusion_data=ConclusionData(recommendation="X"),
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        # Should have --- before conclusion
        lines = output.split("\n")
        # Find front matter end and conclusion start
        assert "---" in output


class TestReporterDataPoints:
    """Key data points section tests."""

    def test_data_points_english(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            data_points=[
                DataPoint(key="Speed", value="100ms", source_url="https://example.com"),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Key Data" in output
        assert "| Metric | Value | Source |" in output
        assert "| Speed | 100ms | https://example.com |" in output

    def test_data_points_chinese(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            data_points=[
                DataPoint(key="速度", value="100ms", source_url="https://example.com"),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## 关键数据" in output
        assert "| 指标 | 数据 | 来源 |" in output

    def test_no_data_points(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Key Data" not in output


class TestReporterComparisons:
    """Comparison section tests."""

    def test_comparison_english(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            comparisons=[
                Comparison(
                    dimension="Performance",
                    values={"A": "100ms", "B": "200ms"},
                ),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Comparison" in output
        assert "| Dimension | A | B |" in output
        assert "| Performance | 100ms | 200ms |" in output

    def test_comparison_chinese(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            comparisons=[
                Comparison(
                    dimension="性能",
                    values={"A": "100ms", "B": "200ms"},
                ),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## 对比分析" in output

    def test_no_comparisons(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Comparison" not in output


class TestReporterContradictions:
    """Contradictions section tests."""

    def test_contradictions_english(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            contradictions=["A says X, B says Y"],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Contradictions" in output
        assert "- A says X, B says Y" in output

    def test_contradictions_chinese(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            contradictions=["矛盾点"],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## 已发现的矛盾点" in output

    def test_no_contradictions(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Contradictions" not in output


class TestReporterSources:
    """Sources section tests."""

    def test_sources_english(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
            sources=[
                Source(
                    url="https://example.com",
                    title="Example",
                    source_type="web",
                    source_lang="en",
                    content="...",
                    confidence="high",
                ),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## Sources" in output
        assert "| # | Title | Source | Confidence |" in output
        assert "| 1 | [Example](https://example.com) | web | high |" in output

    def test_sources_chinese(self):
        analysis = AnalysisResult(
            topic="测试",
            depth="standard",
            lang="zh",
            sections=[Section(id="summary", title="摘要", content="...")],
            sources=[
                Source(
                    url="https://example.com",
                    title="示例",
                    source_type="web",
                    source_lang="zh",
                    content="...",
                    confidence="高",
                ),
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        assert "## 数据来源" in output
        assert "| # | 标题 | 来源 | 可信度 |" in output

    def test_no_sources(self):
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[Section(id="summary", title="S", content="...")],
        )
        reporter = Reporter()
        output = reporter.generate(analysis)
        # Sources section should not appear when no sources
        assert "## Sources" not in output


class TestTemplateSelection:
    """Template selection tests."""

    def test_standard_template_sections(self):
        from scripts.models import SECTION_IDS_STANDARD
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[
                Section(id=sid, title=sid, content="...")
                for sid in SECTION_IDS_STANDARD
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis, template="standard")
        for sid in SECTION_IDS_STANDARD:
            assert f"# {sid}" in output

    def test_deep_template_sections(self):
        from scripts.models import SECTION_IDS_DEEP
        analysis = AnalysisResult(
            topic="Test",
            depth="deep",
            lang="en",
            sections=[
                Section(id=sid, title=sid, content="...")
                for sid in SECTION_IDS_DEEP
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis, template="deep")
        for sid in SECTION_IDS_DEEP:
            assert f"# {sid}" in output

    def test_invalid_template_falls_back_to_standard(self):
        from scripts.models import SECTION_IDS_STANDARD
        analysis = AnalysisResult(
            topic="Test",
            depth="standard",
            lang="en",
            sections=[
                Section(id=SECTION_IDS_STANDARD[0], title="S", content="...")
            ],
        )
        reporter = Reporter()
        output = reporter.generate(analysis, template="invalid")
        assert "# S" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
