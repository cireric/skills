from __future__ import annotations

import re

_VALID_GOAL_TYPES = frozenset({
    "exploratory", "panoramic_understanding", "tech_selection",
    "feasibility_assessment", "competitive_comparison", "academic_research",
    "fact_check", "background_check", "market_analysis", "other",
})

_VALID_DEPTHS = frozenset({"quick", "standard", "deep"})

_VALID_EVIDENCE_TYPES = frozenset({
    "official_data", "independent_benchmark", "third_party_estimate",
    "qualitative_trend", "expert_opinion",
})

_NON_EXACT_EVIDENCE_TYPES = frozenset({
    "third_party_estimate", "qualitative_trend", "expert_opinion",
})

_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})

_VENDOR_SOURCE_TYPES = frozenset({
    "vendor_benchmark", "vendor_survey", "vendor_blog",
})

_INDIRECT_CITATION_PATTERNS = [
    re.compile(r"(?:according to|reported by|said by)\s+(.+?)(?:\s*[,\.]|$)", re.IGNORECASE),
    re.compile(r"(.+?)\s+(?:reports?|announces?|claims?|states?)\s+that", re.IGNORECASE),
]

_TIER_LABELS: dict[str, str] = {
    "1": "\u2605\u2605\u2605\u2606 Tier 1",
    "2": "\u2605\u2605\u2606\u2606 Tier 2",
    "3": "\u2605\u2606\u2606\u2606 Tier 3",
    "4": "\u2606\u2606\u2606\u2606 Tier 4",
}

_LABELS: dict[tuple[str, str], str] = {
    ("references", "en"): "References",
    ("references", "zh"): "\u53c2\u8003\u6587\u732e",
    ("key_insights", "en"): "Key Insights",
    ("key_insights", "zh"): "\u6838\u5fc3\u53d1\u73b0",
    ("tensions", "en"): "Tensions",
    ("tensions", "zh"): "\u5f20\u529b",
    ("verification_summary", "en"): "Verification Summary",
    ("verification_summary", "zh"): "\u9a8c\u8bc1\u6458\u8981",
    ("decision_questions", "en"): "Decision Questions Answered",
    ("decision_questions", "zh"): "\u51b3\u7b56\u95ee\u9898\u56de\u7b54",
}

_SOURCES_DIR = "sources"

_ROUTES: dict[str, list[int] | str] = {
    "tech_selection": [2, 3, 4, 1],
    "competitive_comparison": [2, 1, 3, 4],
    "feasibility_assessment": [2, 1, 3],
    "fact_check": [1, 2, 4],
    "background_check": [3, 2, 1, 4],
    "market_analysis": [3, 4, 1, 2],
    "academic_research": [1, 2],
    "panoramic_understanding": [2, 1, 3, 4],
    "exploratory": [4, 3, 2],
    "other": "auto",
}

_DEFAULT_OTHER_ROUTE = [2, 3, 1, 4]

_DEPTH_BUDGET: dict[str, dict] = {
    "quick": {"max_rounds": 1, "expected_sources": (5, 10), "dq_coverage": "any"},
    "standard": {"max_rounds": 2, "expected_sources": (10, 20), "dq_coverage": "tier12"},
    "deep": {"max_rounds": 3, "expected_sources": (20, 40), "dq_coverage": "tier12_multi"},
}
