"""Report-level gateway checks: operate on the generated .md file."""

from __future__ import annotations

import re
from pathlib import Path

from .artifact_checks import CheckResult
from .lib.constants import _OVERLONG_LINE_THRESHOLD


_HIDDEN_REF_DEF = re.compile(r'^\[\d+\]:\s+https?://\S')
_VISIBLE_REF_ITEM = re.compile(r'^-\s+\[\d+\]')
_INLINE_CITATION = re.compile(r'\[&#91;(\d+)[†‡]?&#93;\]\([^)]*\)|\[\\?\[(\d+)[†‡]?\\?\]\]\([^)]*\)')
_REF_DEF_NUM = re.compile(r'^\[(\d+)\]:\s+https?://\S')
_FENCED_CODE = re.compile(r'^```', re.MULTILINE)
_HEADING = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_FRONT_MATTER_DELIM = re.compile(r'^---\s*$')


def _strip_front_matter(content: str) -> str:
    if content.startswith("---"):
        end = re.search(r'^---\s*$', content[3:], re.MULTILINE)
        if end:
            return content[3 + end.end():]
    return content


def _find_references_section(content: str) -> int:
    ref_idx = content.rfind("## 参考文献")
    if ref_idx == -1:
        ref_idx = content.rfind("## References")
    return ref_idx


def _extract_defined_nums(ref_section: str) -> set[int]:
    defined_nums = set(int(m.group(1)) for m in _REF_DEF_NUM.finditer(ref_section))
    visible_nums = set(int(m.group(1)) for m in re.finditer(r'\[(\d+)\]', ref_section))
    return defined_nums | visible_nums


def _extract_cited_nums(body: str) -> set[int]:
    cited_nums = set()
    for m in _INLINE_CITATION.finditer(body):
        num = m.group(1) or m.group(2)
        if num:
            cited_nums.add(int(num))
    for m in re.finditer(r'\[(\d{1,2})[†‡]?\]\[\]', body):
        cited_nums.add(int(m.group(1)))
    return cited_nums


def check_report_dangling_refs(report_path: Path) -> CheckResult:
    """F1: BLOCKER if in-text [N] has no matching definition in References section."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_dangling_refs", "BLOCKER", True, f"Cannot read report: {e}")
    ref_idx = _find_references_section(content)
    if ref_idx == -1:
        return CheckResult("report_dangling_refs", "BLOCKER", True, "No References section found")
    ref_section = content[ref_idx:]
    all_defined = _extract_defined_nums(ref_section)
    body = content[:ref_idx]
    cited_nums = _extract_cited_nums(body)
    dangling = cited_nums - all_defined
    if dangling:
        return CheckResult(
            "report_dangling_refs", "BLOCKER", False,
            f"In-text citations with no reference definition: {sorted(dangling)}",
            repair_hints=[f"Add reference definitions for citations {sorted(dangling)} to the References section"],
        )
    return CheckResult("report_dangling_refs", "BLOCKER", True)


def check_report_orphaned_defs(report_path: Path) -> CheckResult:
    """F2: BLOCKER if reference definition [N] is not cited in body text."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_orphaned_defs", "BLOCKER", True, f"Cannot read report: {e}")
    ref_idx = _find_references_section(content)
    if ref_idx == -1:
        return CheckResult("report_orphaned_defs", "BLOCKER", True, "No References section found")
    ref_section = content[ref_idx:]
    all_defined = _extract_defined_nums(ref_section)
    body = content[:ref_idx]
    cited_nums = _extract_cited_nums(body)
    orphaned = all_defined - cited_nums
    if orphaned:
        return CheckResult(
            "report_orphaned_defs", "BLOCKER", False,
            f"Reference definitions not cited in body: {sorted(orphaned)}",
            repair_hints=[f"Cite references {sorted(orphaned)} in the report body, or remove unused definitions"],
        )
    return CheckResult("report_orphaned_defs", "BLOCKER", True)


def check_report_refs_visibility(report_path: Path) -> CheckResult:
    """A: WARN if References section has only [N]: URL hidden definitions with no visible list."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_refs_visibility", "WARN", True, f"Cannot read report: {e}")
    ref_idx = _find_references_section(content)
    if ref_idx == -1:
        return CheckResult("report_refs_visibility", "WARN", True, "No References section found")
    ref_section = content[ref_idx:]
    ref_lines = ref_section.split("\n")
    has_hidden = any(_HIDDEN_REF_DEF.match(line) for line in ref_lines)
    has_visible = any(_VISIBLE_REF_ITEM.match(line) for line in ref_lines)
    if has_hidden and not has_visible:
        return CheckResult(
            "report_refs_visibility", "WARN", False,
            "References section has only hidden [N]: URL definitions — not visible in rendered output"
        )
    return CheckResult("report_refs_visibility", "WARN", True)


def check_report_table_delimiters(report_path: Path) -> CheckResult:
    """D: WARN if table delimiter row | count differs from header row."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_table_delimiters", "WARN", True, f"Cannot read report: {e}")
    issues = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "|" in line and not re.match(r'^[\s|:-]+$', line):
            header_pipes = line.count("|")
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                delim_line = lines[j].strip()
                if re.match(r'^[\s|:-]+$', delim_line):
                    delim_pipes = delim_line.count("|")
                    if header_pipes != delim_pipes:
                        issues.append(f"Line {j + 1}: delimiter has {delim_pipes} pipes, header has {header_pipes}")
        i += 1
    if issues:
        return CheckResult("report_table_delimiters", "WARN", False, "; ".join(issues))
    return CheckResult("report_table_delimiters", "WARN", True)


def check_report_front_matter(report_path: Path) -> CheckResult:
    """9: BLOCKER if YAML front matter is malformed or missing required fields."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_front_matter", "BLOCKER", True, f"Cannot read report: {e}")
    if not content.startswith("---"):
        return CheckResult("report_front_matter", "BLOCKER", False, "No YAML front matter delimiter found")
    end_match = re.search(r'^---\s*$', content[3:], re.MULTILINE)
    if not end_match:
        return CheckResult("report_front_matter", "BLOCKER", False, "YAML front matter not properly closed")
    yaml_text = content[3:3 + end_match.start()]
    required_fields = {"topic", "goal_type", "date", "review_status"}
    missing = []
    for field in required_fields:
        if not re.search(rf'^{field}\s*:', yaml_text, re.MULTILINE):
            missing.append(field)
    if missing:
        return CheckResult(
            "report_front_matter", "BLOCKER", False,
            f"Front matter missing required fields: {', '.join(missing)}",
            repair_hints=[f"Add the following fields to YAML front matter: {', '.join(missing)}"],
        )
    return CheckResult("report_front_matter", "BLOCKER", True)


def check_report_heading_levels(report_path: Path) -> CheckResult:
    """10: WARN if heading levels skip (e.g., ## directly to ####)."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_heading_levels", "WARN", True, f"Cannot read report: {e}")
    content = _strip_front_matter(content)
    headings = []
    for m in _HEADING.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        headings.append((level, text))
    issues = []
    for i in range(1, len(headings)):
        prev_level = headings[i - 1][0]
        curr_level = headings[i][0]
        if curr_level > prev_level + 1:
            issues.append(
                f"'{'#' * curr_level} {headings[i][1]}' (level {curr_level}) "
                f"follows '{'#' * prev_level} {headings[i - 1][1]}' (level {prev_level})"
            )
    if issues:
        return CheckResult("report_heading_levels", "WARN", False, "; ".join(issues[:5]))
    return CheckResult("report_heading_levels", "WARN", True)


def check_report_duplicate_headings(report_path: Path) -> CheckResult:
    """12: WARN if same-level headings with identical text appear more than once."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_duplicate_headings", "WARN", True, f"Cannot read report: {e}")
    content = _strip_front_matter(content)
    seen: dict[str, list[int]] = {}
    for m in _HEADING.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        key = f"L{level}:{text}"
        seen.setdefault(key, []).append(m.start())
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        items = [f"'{k.split(':', 1)[1]}' appears {len(v)} times" for k, v in list(duplicates.items())[:5]]
        return CheckResult("report_duplicate_headings", "WARN", False, "; ".join(items))
    return CheckResult("report_duplicate_headings", "WARN", True)


def check_report_unclosed_code_blocks(report_path: Path) -> CheckResult:
    """13: WARN if fenced code block markers appear an odd number of times."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_unclosed_code_blocks", "WARN", True, f"Cannot read report: {e}")
    content = _strip_front_matter(content)
    count = len(_FENCED_CODE.findall(content))
    if count % 2 != 0:
        return CheckResult(
            "report_unclosed_code_blocks", "WARN", False,
            f"Found {count} fenced code block markers (odd number — likely unclosed)"
        )
    return CheckResult("report_unclosed_code_blocks", "WARN", True)


def check_report_empty_sections(report_path: Path) -> CheckResult:
    """15: WARN if a section heading exists but has no content before the next heading."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_empty_sections", "WARN", True, f"Cannot read report: {e}")
    content = _strip_front_matter(content)
    headings = [(m.start(), m.end(), m.group(2).strip()) for m in _HEADING.finditer(content)]
    issues = []
    for i, (pos, end_pos, heading_text) in enumerate(headings):
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(content)
        between = content[end_pos:next_pos].strip()
        if not between:
            issues.append(f"'{heading_text}' has no content")
    if issues:
        return CheckResult("report_empty_sections", "WARN", False, "; ".join(issues[:5]))
    return CheckResult("report_empty_sections", "WARN", True)


def check_report_overlong_lines(report_path: Path) -> CheckResult:
    """16: WARN if any line exceeds 500 characters."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        return CheckResult("report_overlong_lines", "WARN", True, f"Cannot read report: {e}")
    overlong = []
    for i, line in enumerate(content.split("\n"), 1):
        if len(line) > _OVERLONG_LINE_THRESHOLD:
            overlong.append(f"Line {i}: {len(line)} chars")
    if overlong:
        return CheckResult(
            "report_overlong_lines", "WARN", False,
            f"{len(overlong)} line(s) over {_OVERLONG_LINE_THRESHOLD} chars: " + "; ".join(overlong[:5])
        )
    return CheckResult("report_overlong_lines", "WARN", True)


def run_report_checks(report_path: Path) -> list[CheckResult]:
    """Run all 10 report-level checks on the generated .md file."""
    return [
        check_report_dangling_refs(report_path),
        check_report_orphaned_defs(report_path),
        check_report_refs_visibility(report_path),
        check_report_table_delimiters(report_path),
        check_report_front_matter(report_path),
        check_report_heading_levels(report_path),
        check_report_duplicate_headings(report_path),
        check_report_unclosed_code_blocks(report_path),
        check_report_empty_sections(report_path),
        check_report_overlong_lines(report_path),
    ]
