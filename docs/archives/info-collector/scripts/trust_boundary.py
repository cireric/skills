"""Trust boundary validation for subagent output (ADR 0053).

Validates subagent output before writing to section_file.
Two layers: structural validation + semantic validation (URL matching).

Structural validation delegates to lib/schemas._validate_sections for
schema-level checks (required fields, types, enums), then adds
trust-boundary-specific checks (empty sources, missing summary on claims).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .lib.utils import normalize_url
from .lib.schemas import _validate_sections


@dataclass
class ValidationError:
    path: str
    error: str
    expected: str
    actual: str


@dataclass
class ValidationResult:
    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    report_json: str = ""

    def __post_init__(self):
        if not self.report_json and self.errors:
            self.report_json = json.dumps(
                {
                    "validation_errors": [
                        {
                            "path": e.path,
                            "error": e.error,
                            "expected": e.expected,
                            "actual": e.actual,
                        }
                        for e in self.errors
                    ],
                    "retry_count": 0,
                    "max_retries": 2,
                },
                ensure_ascii=False,
            )


_REF_MARKER_RE = __import__("re").compile(r"\{\{ref:(.*?)\}\}")


def validate_section_output(
    raw_json: str,
    collected_urls: set[str],
) -> ValidationResult:
    errors: list[ValidationError] = []

    try:
        data = json.loads(raw_json.lstrip('\ufeff'))
    except json.JSONDecodeError as e:
        return ValidationResult(
            passed=False,
            errors=[ValidationError("root", "invalid_json", "valid JSON object", str(e))],
        )

    if not isinstance(data, dict):
        return ValidationResult(
            passed=False,
            errors=[ValidationError("root", "type_mismatch", "dict", type(data).__name__)],
        )

    _validate_structural(data, errors)
    _validate_semantic(data, collected_urls, errors)

    passed = len(errors) == 0
    return ValidationResult(passed=passed, errors=errors)


def _convert_schema_errors(schema_errors: list) -> list[ValidationError]:
    """Convert lib.schemas.ValidationError to trust_boundary.ValidationError."""
    result = []
    for e in schema_errors:
        path = e.field.replace("sections[0].", "")
        result.append(ValidationError(path, "schema_violation", "valid value per schema", e.message))
    return result


def _validate_structural(data: dict, errors: list[ValidationError]) -> None:
    schema_errors: list = []
    _validate_sections([data], schema_errors)
    errors.extend(_convert_schema_errors(schema_errors))

    _validate_trust_boundary_extras(data, errors)


def _validate_trust_boundary_extras(data: dict, errors: list[ValidationError]) -> None:
    for field_name in ("key_insights", "tensions"):
        items = data.get(field_name)
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            src = item.get("sources")
            if isinstance(src, list) and len(src) == 0:
                errors.append(ValidationError(f"{field_name}[{i}].sources", "empty_array", "non-empty list of URLs", "[]"))

    claims = data.get("claims")
    if not isinstance(claims, list):
        return
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        src = claim.get("sources")
        if isinstance(src, list) and len(src) == 0:
            errors.append(ValidationError(f"claims[{i}].sources", "empty_array", "non-empty list of URLs", "[]"))


def _validate_semantic(data: dict, collected_urls: set[str], errors: list[ValidationError]) -> None:
    if not collected_urls:
        return

    content = data.get("content", "")
    ref_urls = _REF_MARKER_RE.findall(content)
    for url in ref_urls:
        if normalize_url(url) not in collected_urls:
            errors.append(ValidationError(f"content {{{{ref:{url}}}}}", "url_not_in_collected", "URL from collected.json", url))

    for field_name in ("key_insights", "tensions", "claims"):
        items = data.get(field_name)
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for url in item.get("sources", []):
                if normalize_url(url) not in collected_urls:
                    errors.append(ValidationError(f"{field_name}[{i}].sources", "url_not_in_collected", "URL from collected.json", url))
