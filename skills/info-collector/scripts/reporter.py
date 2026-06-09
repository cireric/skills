"""Markdown report generator from structured analysis data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from scripts.models import SECTION_IDS_DEEP, SECTION_IDS_STANDARD, AnalysisResult


class Reporter:
    """Generates Markdown reports from structured AnalysisResult data.

    Table headers adapt to the report language (``analysis.lang``):
    ``zh`` (default) → Chinese headers, ``en`` → English headers.
    """

    TEMPLATES: dict[str, list[str]] = {
        "standard": SECTION_IDS_STANDARD.copy(),
        "deep": SECTION_IDS_DEEP.copy(),
    }

    def generate(
        self,
        analysis: AnalysisResult,
        template: Literal["standard", "deep"] = "deep",
        draft: bool = False,
    ) -> str:
        sections_by_id = {s.id: s for s in analysis.sections}
        section_order = self.TEMPLATES.get(template, self.TEMPLATES["standard"])

        lines: list[str] = []
        self._write_front_matter(lines, analysis, draft=draft)
        lines.append("")

        if analysis.summary:
            lines.append("> " + analysis.summary)
            lines.append("")

        for section_id in section_order:
            section = sections_by_id.get(section_id)
            if section is None:
                continue
            lines.append(f"# {section.title}")
            lines.append("")
            lines.append(section.content.strip())
            lines.append("")

        if analysis.conclusion_data:
            self._write_structured_conclusion(lines, analysis)

        self._write_data_points(lines, analysis)
        self._write_comparisons(lines, analysis)
        self._write_contradictions(lines, analysis)
        self._write_sources(lines, analysis)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Section writers (language-aware)
    # ------------------------------------------------------------------

    def _write_front_matter(
        self, lines: list[str], analysis: AnalysisResult, *, draft: bool = False
    ) -> None:
        lines.append("---")
        lines.append(f"title: {analysis.topic}")
        lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"depth: {analysis.depth}")
        lines.append(f"lang: {analysis.lang}")
        lines.append(f"sources: {len(analysis.sources)}")
        if draft:
            lines.append("status: draft")
        lines.append("---")

    def _write_structured_conclusion(self, lines: list[str], analysis: AnalysisResult) -> None:
        cd = analysis.conclusion_data
        if cd is None:
            return

        lang = analysis.lang
        zh = lang == "zh"

        lines.append("---")
        lines.append("")

        if cd.recommendation:
            heading = "推荐方案" if zh else "Recommendation"
            lines.append(f"### {heading}")
            lines.append(f"**{'推荐' if zh else 'Recommendation'}**: {cd.recommendation}")
            if cd.reasoning:
                lines.append(f"**{'理由' if zh else 'Reasoning'}**: {cd.reasoning}")
            lines.append("")

        if cd.confidence_assessments:
            heading = "置信度评估" if zh else "Confidence Assessment"
            lines.append(f"### {heading}")
            lines.append("")
            if zh:
                lines.append("| 结论 | 置信度 | 依据强度 |")
            else:
                lines.append("| Conclusion | Confidence | Evidence Strength |")
            lines.append("|------|--------|---------|")
            for ca in cd.confidence_assessments:
                lines.append(f"| {ca.conclusion} | {ca.confidence} | {ca.evidence_strength} |")
            lines.append("")

        if cd.action_items:
            heading = "后续行动" if zh else "Action Items"
            lines.append(f"### {heading}")
            lines.append("")
            for item in cd.action_items:
                lines.append(f"- [ ] {item}")
            lines.append("")

        if cd.open_questions:
            heading = "未解问题" if zh else "Open Questions"
            lines.append(f"### {heading}")
            lines.append("")
            for q in cd.open_questions:
                lines.append(f"- {q}")
            lines.append("")

    def _write_data_points(self, lines: list[str], analysis: AnalysisResult) -> None:
        if not analysis.data_points:
            return

        lang = analysis.lang
        zh = lang == "zh"
        lines.append(f"## {'关键数据' if zh else 'Key Data'}")
        lines.append("")
        h1, h2, h3 = ("指标", "数据", "来源") if zh else ("Metric", "Value", "Source")
        lines.append(f"| {h1} | {h2} | {h3} |")
        lines.append("|------|------|------|")
        for dp in analysis.data_points:
            lines.append(f"| {dp.key} | {dp.value} | {dp.source_url} |")
        lines.append("")

    def _write_comparisons(self, lines: list[str], analysis: AnalysisResult) -> None:
        if not analysis.comparisons:
            return

        lang = analysis.lang
        zh = lang == "zh"
        lines.append(f"## {'对比分析' if zh else 'Comparison'}")
        lines.append("")

        options = sorted({opt for c in analysis.comparisons for opt in c.values})
        header = f"| {'维度' if zh else 'Dimension'} | " + " | ".join(options) + " |"
        sep = "|------|" + "|".join("------" for _ in options) + "|"
        lines.append(header)
        lines.append(sep)
        for comp in analysis.comparisons:
            row = f"| {comp.dimension} "
            for opt in options:
                val = comp.values.get(opt, "-")
                row += f"| {val} "
            row += "|"
            lines.append(row)
        lines.append("")

    def _write_contradictions(self, lines: list[str], analysis: AnalysisResult) -> None:
        if not analysis.contradictions:
            return

        lang = analysis.lang
        zh = lang == "zh"
        lines.append(f"## {'已发现的矛盾点' if zh else 'Contradictions'}")
        lines.append("")
        for c in analysis.contradictions:
            lines.append(f"- {c}")
        lines.append("")

    def _write_sources(self, lines: list[str], analysis: AnalysisResult) -> None:
        if not analysis.sources:
            return

        lang = analysis.lang
        zh = lang == "zh"
        lines.append("---")
        lines.append("")
        lines.append(f"## {'数据来源' if zh else 'Sources'}")
        lines.append("")
        if zh:
            lines.append("| # | 标题 | 来源 | 可信度 |")
        else:
            lines.append("| # | Title | Source | Confidence |")
        lines.append("|---|------|------|--------|")
        for i, src in enumerate(analysis.sources, 1):
            lines.append(
                f"| {i} | [{src.title}]({src.url}) | {src.source_type} | {src.confidence} |"
            )
        lines.append("")
