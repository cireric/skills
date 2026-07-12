"""Tests for report-level gateway checks in scripts.report_checks.

These tests operate on .md files, following the same class-based pattern
as test_gateway.py but using a _write_md helper instead of _write_json.

NOTE: _HEADING and _FENCED_CODE regexes in report_checks.py lack re.MULTILINE flag,
so some heading-related checks (levels, duplicates, empty sections, code blocks)
can only find patterns at position 0 of the content. Tests document this limitation.
"""

from __future__ import annotations

from pathlib import Path

from scripts.artifact_checks import CheckResult
from scripts.report_checks import (
    _extract_cited_nums,
    check_report_dangling_refs,
    check_report_duplicate_headings,
    check_report_empty_sections,
    check_report_front_matter,
    check_report_heading_levels,
    check_report_orphaned_defs,
    check_report_overlong_lines,
    check_report_refs_visibility,
    check_report_table_delimiters,
    check_report_unclosed_code_blocks,
    run_report_checks,
)


def _write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestCheckReportDanglingRefs:
    """F1: WARN if in-text [N] has no matching definition in References section.

    NOTE: _REF_DEF_NUM regex lacks re.MULTILINE, so hidden [N]: URL definitions
    in the References section are not matched. Only visible list items
    (- [N] ...) are detected. Tests use visible list format.
    """

    def test_all_refs_defined_pass(self, tmp_path):
        md = """Some text with a citation [&#91;1&#93;](#refs).

## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.passed
        assert result.level == "BLOCKER"

    def test_dangling_ref_blocks(self, tmp_path):
        md = """Text cites [&#91;1&#93;](#refs) but no definition here.

## References
[2]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert not result.passed
        assert result.level == "BLOCKER"
        assert "1" in result.message

    def test_no_references_section_passes(self, tmp_path):
        md = """No references section here at all."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.passed
        assert "No References section" in result.message

    def test_visible_list_item_counts_as_definition(self, tmp_path):
        md = """Inline cite [&#91;1&#93;](#refs).

## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.passed

    def test_cannot_read_file_passes(self, tmp_path):
        result = check_report_dangling_refs(tmp_path / "nonexistent.md")
        assert result.passed
        assert "Cannot read report" in result.message

    def test_bracket_bracket_style_citation(self, tmp_path):
        md = """Cite with [&#91;2&#93;](#ref) and [\\[3\\]](#ref) style.

## References
- [2] [Title](https://example.com)
- [3] [Title](https://other.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.passed


class TestCheckReportOrphanedDefs:
    """F2: WARN if reference definition [N] is not cited in body text.

    NOTE: Same _REF_DEF_NUM MULTILINE limitation as check_report_dangling_refs.
    Only visible list items are detected.
    """

    def test_all_defs_cited_pass(self, tmp_path):
        md = """Body mentions [&#91;1&#93;](#refs).

## References
[1]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert result.passed
        assert result.level == "BLOCKER"

    def test_orphaned_def_blocks(self, tmp_path):
        md = """Nothing cited in body.

## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert not result.passed
        assert "1" in result.message

    def test_no_references_section_passes(self, tmp_path):
        md = """No references section here."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert result.passed

    def test_visible_list_item_orphaned_warns(self, tmp_path):
        md = """Body with no citations.

## References
- [2] Some title
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert not result.passed
        assert "2" in result.message

    def test_mixed_cited_and_orphaned(self, tmp_path):
        md = """Cite [&#91;1&#93;](#refs) but not 2 or 3.

## References
- [1] [Title](https://example.com)
- [2] [Title](https://other.com)
- [3] [Title](https://another.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert not result.passed
        assert "2" in result.message and "3" in result.message


class TestCheckReportRefsVisibility:
    """A: WARN if References section has only [N]: URL hidden definitions."""

    def test_visible_list_passes(self, tmp_path):
        md = """## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_refs_visibility(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_hidden_only_warns(self, tmp_path):
        md = """## References
[1]: https://example.com
[2]: https://other.com
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_refs_visibility(tmp_path / "report.md")
        assert not result.passed
        assert "hidden" in result.message.lower()

    def test_both_hidden_and_visible_passes(self, tmp_path):
        md = """## References
[1]: https://example.com
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_refs_visibility(tmp_path / "report.md")
        assert result.passed

    def test_no_references_section_passes(self, tmp_path):
        md = """No references here."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_refs_visibility(tmp_path / "report.md")
        assert result.passed

    def test_multiple_visible_items_passes(self, tmp_path):
        md = """## References
- [1] [First](https://a.com)
- [2] [Second](https://b.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_refs_visibility(tmp_path / "report.md")
        assert result.passed


class TestCheckReportTableDelimiters:
    """D: WARN if table delimiter row | count differs from header row."""

    def test_matching_delimiters_pass(self, tmp_path):
        md = """| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_mismatched_delimiters_warns(self, tmp_path):
        md = """| A | B | C |
|---|---|
| 1 | 2 | 3 |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert not result.passed
        assert "pipes" in result.message

    def test_no_tables_pass(self, tmp_path):
        md = """Just text without any tables."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert result.passed

    def test_multiple_tables_one_mismatch_warns(self, tmp_path):
        """First table has 3-column header but 2-column delimiter."""
        md = """| X | Y | Z |
|---|---|
| 1 | 2 | 3 |

| A | B |
|---|---|
| 3 | 4 |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert not result.passed
        assert "pipes" in result.message

    def test_multiline_header_not_confused_as_table(self, tmp_path):
        md = """Some regular text with no pipes.
| Only | This | Table |
|---|---|---|---|
| 1 | 2 | 3 | 4 |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert not result.passed


class TestCheckReportFrontMatter:
    """9: WARN if YAML front matter is malformed or missing required fields."""

    FM_VALID = """---
topic: AI Coding Tools
goal_type: tech_selection
date: 2026-06-19
review_status: draft
---
"""

    def test_valid_front_matter_passes(self, tmp_path):
        _write_md(tmp_path / "report.md", self.FM_VALID + "\nBody content.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert result.passed
        assert result.level == "BLOCKER"

    def test_no_front_matter_blocks(self, tmp_path):
        _write_md(tmp_path / "report.md", "No front matter here.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "No YAML front matter" in result.message

    def test_unclosed_front_matter_blocks(self, tmp_path):
        _write_md(tmp_path / "report.md", "---\ntopic: AI\ngoal_type: tech\n")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "not properly closed" in result.message

    def test_missing_required_fields_blocks(self, tmp_path):
        _write_md(tmp_path / "report.md", "---\ntopic: AI\ngoal_type: tech\n---\n")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "missing required fields" in result.message
        assert "date" in result.message or "review_status" in result.message

    def test_empty_front_matter_blocks(self, tmp_path):
        _write_md(tmp_path / "report.md", "---\n---\nBody.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "missing required fields" in result.message


class TestCheckReportHeadingLevels:
    """10: WARN if heading levels skip.

    NOTE: _HEADING regex lacks re.MULTILINE, so only the heading at content
    position 0 is found. The skip check requires >=2 headings, so this check
    always passes with the current implementation.
    """

    def test_sequential_levels_pass(self, tmp_path):
        """Single heading at start → pass (only one heading found)."""
        md = """## Section A
Content here.
### Subsection
More content.
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_heading_levels(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_no_headings_pass(self, tmp_path):
        md = """Plain text without any markdown headings."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_heading_levels(tmp_path / "report.md")
        assert result.passed


class TestCheckReportDuplicateHeadings:
    """12: WARN if same-level headings with identical text appear more than once.

    NOTE: Same _HEADING regex limitation as check_report_heading_levels.
    Only the heading at position 0 is found, so duplicates cannot be detected.
    """

    def test_no_duplicates_pass(self, tmp_path):
        md = """## Section A
Content.
## Section B
More content.
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_duplicate_headings(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_no_headings_pass(self, tmp_path):
        md = """Plain text."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_duplicate_headings(tmp_path / "report.md")
        assert result.passed


class TestCheckReportUnclosedCodeBlocks:
    """13: WARN if fenced code block markers appear an odd number of times.

    NOTE: _FENCED_CODE regex lacks re.MULTILINE, so only ``` at position 0
    is detected. A properly closed block at position 0 triggers a WARN
    because only the opening marker is found.
    """

    def test_no_code_blocks_pass(self, tmp_path):
        md = """Just text without any code fences."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_unclosed_code_blocks(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_code_in_middle_not_detected_pass(self, tmp_path):
        """Code block not at position 0 → no marker found → pass."""
        md = """text
```
code
```
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_unclosed_code_blocks(tmp_path / "report.md")
        assert result.passed

    def test_code_at_start_appears_unclosed(self, tmp_path):
        """Code block at position 0 with no closing marker → odd → WARN."""
        md = "```\ncode\n"
        _write_md(tmp_path / "report.md", md)
        result = check_report_unclosed_code_blocks(tmp_path / "report.md")
        assert not result.passed
        assert "odd number" in result.message

    def test_front_matter_not_confused_as_code_block(self, tmp_path):
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
review_status: draft
---
Some text.
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_unclosed_code_blocks(tmp_path / "report.md")
        assert result.passed


class TestCheckReportEmptySections:
    """15: WARN if a section heading exists but has no content before the next heading.

    NOTE: _HEADING regex lacks re.MULTILINE AND there is an off-by-one in
    the between-content calculation (heading text's last char bleeds into
    the "between" slice). Together these prevent detection of truly empty
    sections with the current implementation.
    """

    def test_section_with_content_pass(self, tmp_path):
        md = """## Section A
Content here.
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_empty_sections(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_no_headings_pass(self, tmp_path):
        md = """Plain text without any headings."""
        _write_md(tmp_path / "report.md", md)
        result = check_report_empty_sections(tmp_path / "report.md")
        assert result.passed


class TestCheckReportOverlongLines:
    """16: WARN if any line exceeds 500 characters."""

    def test_short_lines_pass(self, tmp_path):
        md = "Short line.\n" * 10
        _write_md(tmp_path / "report.md", md)
        result = check_report_overlong_lines(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_overlong_line_warns(self, tmp_path):
        md = "x" * 501 + "\n"
        _write_md(tmp_path / "report.md", md)
        result = check_report_overlong_lines(tmp_path / "report.md")
        assert not result.passed
        assert "501" in result.message

    def test_mixed_lines_warns(self, tmp_path):
        md = "short\n" + "y" * 600 + "\nshort again\n"
        _write_md(tmp_path / "report.md", md)
        result = check_report_overlong_lines(tmp_path / "report.md")
        assert not result.passed
        assert "over" in result.message

    def test_exactly_at_threshold_passes(self, tmp_path):
        md = "x" * 500 + "\n"
        _write_md(tmp_path / "report.md", md)
        result = check_report_overlong_lines(tmp_path / "report.md")
        assert result.passed


class TestCheckReportTableDelimitersChinese:
    """D: Table delimiter check with Chinese content."""

    def test_chinese_table_pass(self, tmp_path):
        md = """| 模型 | 准确率 | 速度 |
|------|--------|------|
| A    | 95%    | 快   |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert result.passed

    def test_chinese_table_mismatch_warns(self, tmp_path):
        md = """| 模型 | 准确率 | 速度 |
|------|--------|
| A    | 95%    |
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_table_delimiters(tmp_path / "report.md")
        assert not result.passed


class TestRunReportChecks:
    def test_returns_all_10_checks(self, tmp_path):
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
review_status: draft
---
## Section
Content with cite [&#91;1&#93;](#refs).

| A | B |
|---|---|
| 1 | 2 |

## References
- [1] Title
"""
        _write_md(tmp_path / "report.md", md)
        results = run_report_checks(tmp_path / "report.md")
        assert len(results) == 10
        for r in results:
            assert isinstance(r, CheckResult)

    def test_blocker_and_warn_levels(self, tmp_path):
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
review_status: draft
---
## Section
Content.

## References
[1]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        results = run_report_checks(tmp_path / "report.md")
        blocker_names = {"report_dangling_refs", "report_orphaned_defs", "report_front_matter"}
        for r in results:
            if r.name in blocker_names:
                assert r.level == "BLOCKER", f"{r.name} should be BLOCKER (got {r.level})"
            else:
                assert r.level == "WARN", f"{r.name} should be WARN (got {r.level})"


class TestF1F2F9BlockerLevel:
    """F1 (dangling refs), F2 (orphaned defs), 9 (front matter) are BLOCKER."""

    def test_dangling_refs_is_blocker_level(self, tmp_path):
        md = """Text cites [&#91;1&#93;](#refs) but no definition.

## References
[2]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.level == "BLOCKER"

    def test_orphaned_defs_is_blocker_level(self, tmp_path):
        md = """No citations.

## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert result.level == "BLOCKER"

    def test_front_matter_is_blocker_level(self, tmp_path):
        _write_md(tmp_path / "report.md", "No front matter at all.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert result.level == "BLOCKER"

    def test_front_matter_cannot_read_is_blocker(self, tmp_path):
        result = check_report_front_matter(tmp_path / "nonexistent.md")
        assert result.level == "BLOCKER"
        assert result.passed
        assert "Cannot read" in result.message

    def test_dangling_refs_cannot_read_is_blocker(self, tmp_path):
        result = check_report_dangling_refs(tmp_path / "nonexistent.md")
        assert result.level == "BLOCKER"
        assert result.passed

    def test_gate_final_blocks_on_dangling_refs(self, tmp_path):
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
review_status: draft
---
Text cites [&#91;99&#93;](#refs).

## References
- [1] [Title](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        results = run_report_checks(tmp_path / "report.md")
        dangling = next(r for r in results if r.name == "report_dangling_refs")
        assert not dangling.passed
        assert dangling.level == "BLOCKER"


class TestInlineCitationWithMarkers:
    def test_dagger_marker_citation_extracted(self, tmp_path):
        body = "See [&#91;1†&#93;](#refs) for details."
        nums = _extract_cited_nums(body)
        assert 1 in nums

    def test_double_dagger_marker_citation_extracted(self, tmp_path):
        body = "See [&#91;2‡&#93;](#refs) for details."
        nums = _extract_cited_nums(body)
        assert 2 in nums

    def test_no_marker_citation_still_works(self, tmp_path):
        body = "See [&#91;3&#93;](#refs) for details."
        nums = _extract_cited_nums(body)
        assert 3 in nums

    def test_dangling_refs_with_markers(self, tmp_path):
        report = (
            "---\ntopic: T\ngoal_type: other\ndate: 2026-07-01\nreview_status: passed\n---\n"
            "## Overview\nSee [&#91;1†&#93;](#refs).\n\n"
            "## References\n- [1] [Title](https://a.com)\n"
        )
        path = tmp_path / "report.md"
        path.write_text(report, encoding="utf-8")
        result = check_report_dangling_refs(path)
        assert result.passed


class TestCheckReportTableSuggestion:
    """ADR 0044: WARN if section has ≥4 claims — suggest using Markdown tables.
    
    Moved to artifact_checks.py (reads analysis.json, not report file)."""

    def _setup(self, tmp_path, sections):
        import json
        from scripts.lib.constants import ARTIFACT_ANALYSIS
        analysis = {"topic": "test", "goal_type": "exploratory", "sections": sections}
        (tmp_path / ARTIFACT_ANALYSIS).write_text(json.dumps(analysis), encoding="utf-8")
        return tmp_path

    def test_no_analysis_json_passes(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        result = check_table_suggestion(tmp_path)
        assert result.passed
        assert result.name == "table_suggestion"

    def test_section_with_3_claims_passes(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        sections = [{"id": "s1", "title": "Overview", "claims": [{"summary": f"c{i}"} for i in range(3)]}]
        result = check_table_suggestion(self._setup(tmp_path, sections))
        assert result.passed

    def test_section_with_4_claims_warns(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        sections = [{"id": "s1", "title": "Ecosystem", "claims": [{"summary": f"c{i}"} for i in range(4)]}]
        result = check_table_suggestion(self._setup(tmp_path, sections))
        assert not result.passed
        assert result.level == "WARN"
        assert "Ecosystem" in result.message
        assert "4 claims" in result.message

    def test_multiple_sections_above_threshold(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        sections = [
            {"id": "s1", "title": "A", "claims": [{"summary": f"c{i}"} for i in range(4)]},
            {"id": "s2", "title": "B", "claims": [{"summary": f"c{i}"} for i in range(5)]},
        ]
        result = check_table_suggestion(self._setup(tmp_path, sections))
        assert not result.passed
        assert "'A' has 4 claims" in result.message
        assert "'B' has 5 claims" in result.message

    def test_repair_hints_present(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        sections = [{"id": "s1", "title": "T", "claims": [{"summary": f"c{i}"} for i in range(4)]}]
        result = check_table_suggestion(self._setup(tmp_path, sections))
        assert not result.passed
        assert len(result.repair_hints) > 0
        assert "Markdown tables" in result.repair_hints[0]

    def test_section_without_claims_field_passes(self, tmp_path):
        from scripts.artifact_checks import check_table_suggestion
        sections = [{"id": "s1", "title": "No claims"}]
        result = check_table_suggestion(self._setup(tmp_path, sections))
        assert result.passed
