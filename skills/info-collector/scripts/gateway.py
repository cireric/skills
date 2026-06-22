"""Hard gate checks: artifact_exists, url_traceability, section_coverage, schema, heuristics,
precision_inflation, claim_metadata.

This module re-exports all check functions from artifact_checks and report_checks
for backward compatibility. New code should import from the specific module.
"""

from __future__ import annotations

# Re-export CheckResult and all artifact checks
from .artifact_checks import (  # noqa: F401
    CheckResult,
    _count_words,
    _has_concrete_name,
    _has_valid_number,
    _normalize_numbers,
    _number_found_in_source,
    check_analysis_schema,
    check_artifact_exists,
    check_claim_dedup,
    check_claim_metadata,
    check_claim_source_relevance,
    check_claim_verified,
    check_content_concreteness,
    check_fetched_content_depth,
    check_methodology_depth,
    check_metric_type_homogeneity,
    check_precision_inflation,
    check_quality_heuristics,
    check_recommendation_structure,
    check_search_plan_compliance,
    check_section_coverage,
    check_source_metadata,
    check_source_tier_balance,
    check_url_traceability,
    run_all,
)

# Re-export all report checks
from .report_checks import (  # noqa: F401
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
