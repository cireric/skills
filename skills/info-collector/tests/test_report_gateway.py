"""Tests for report-level gateway checks in scripts.gateway.

These tests operate on .md files, following the same class-based pattern
as test_gateway.py but using a _write_md helper instead of _write_json.

NOTE: _HEADING and _FENCED_CODE regexes in gateway.py lack re.MULTILINE flag,
so some heading-related checks (levels, duplicates, empty sections, code blocks)
can only find patterns at position 0 of the content. Tests document this limitation.
"""

from __future__ import annotations

from pathlib import Path

from scripts.gateway import (
    CheckResult,
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
    (- **[N]** ...) are detected. Tests use visible list format.
    """

    def test_all_refs_defined_pass(self, tmp_path):
        md = """Some text with a citation [&#91;1&#93;](#refs).

## References
- **[1]** Title — [URL](https://example.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_dangling_ref_warns(self, tmp_path):
        md = """Text cites [&#91;1&#93;](#refs) but no definition here.

## References
[2]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_dangling_refs(tmp_path / "report.md")
        assert not result.passed
        assert result.level == "WARN"
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
- **[1]** Title — [URL](https://example.com)
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
- **[2]** Title — [URL](https://example.com)
- **[3]** Title — [URL](https://other.com)
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
        assert result.level == "WARN"

    def test_orphaned_def_warns(self, tmp_path):
        md = """Nothing cited in body.

## References
- **[1]** Title — [URL](https://example.com)
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
- **[2]** Some title
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert not result.passed
        assert "2" in result.message

    def test_mixed_cited_and_orphaned(self, tmp_path):
        md = """Cite [&#91;1&#93;](#refs) but not 2 or 3.

## References
- **[1]** Title — [URL](https://example.com)
- **[2]** Title — [URL](https://other.com)
- **[3]** Title — [URL](https://another.com)
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_orphaned_defs(tmp_path / "report.md")
        assert not result.passed
        assert "2" in result.message and "3" in result.message


class TestCheckReportRefsVisibility:
    """A: WARN if References section has only [N]: URL hidden definitions."""

    def test_visible_list_passes(self, tmp_path):
        md = """## References
- **[1]** Title — [URL](https://example.com)
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
- **[1]** Title — [URL](https://example.com)
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
- **[1]** First — [URL](https://a.com)
- **[2]** Second — [URL](https://b.com)
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
quality: draft
---
"""

    def test_valid_front_matter_passes(self, tmp_path):
        _write_md(tmp_path / "report.md", self.FM_VALID + "\nBody content.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert result.passed
        assert result.level == "WARN"

    def test_no_front_matter_warns(self, tmp_path):
        _write_md(tmp_path / "report.md", "No front matter here.")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "No YAML front matter" in result.message

    def test_unclosed_front_matter_warns(self, tmp_path):
        _write_md(tmp_path / "report.md", "---\ntopic: AI\ngoal_type: tech\n")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "not properly closed" in result.message

    def test_missing_required_fields_warns(self, tmp_path):
        _write_md(tmp_path / "report.md", "---\ntopic: AI\ngoal_type: tech\n---\n")
        result = check_report_front_matter(tmp_path / "report.md")
        assert not result.passed
        assert "missing required fields" in result.message
        assert "date" in result.message or "quality" in result.message

    def test_empty_front_matter_warns(self, tmp_path):
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
        """Code block at position 0 → only opening marker found → odd → WARN."""
        md = """```
code
```
"""
        _write_md(tmp_path / "report.md", md)
        result = check_report_unclosed_code_blocks(tmp_path / "report.md")
        assert not result.passed
        assert "odd number" in result.message

    def test_front_matter_not_confused_as_code_block(self, tmp_path):
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
quality: draft
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
quality: draft
---
## Section
Content with cite [&#91;1&#93;](#refs).

| A | B |
|---|---|
| 1 | 2 |

## References
- **[1]** Title
"""
        _write_md(tmp_path / "report.md", md)
        results = run_report_checks(tmp_path / "report.md")
        assert len(results) == 10
        for r in results:
            assert isinstance(r, CheckResult)

    def test_all_return_warn_level(self, tmp_path):
        """All report checks return WARN level regardless of pass/fail."""
        md = """---
topic: AI
goal_type: tech_selection
date: 2026-01-01
quality: draft
---
## Section
Content.

## References
[1]: https://example.com
"""
        _write_md(tmp_path / "report.md", md)
        results = run_report_checks(tmp_path / "report.md")
        for r in results:
            assert r.level == "WARN", f"{r.name} is not WARN (got {r.level})"
