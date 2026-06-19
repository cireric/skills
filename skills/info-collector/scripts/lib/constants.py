"""Shared constants for the info-collector skill.

Single source of truth for enumerations, thresholds, and classification sets.
When adding a new goal_type or metric_type, only this file needs updating.
"""

from __future__ import annotations


# ── Stop words ──

_ENGLISH_STOP_WORDS = frozenset({
    "a", "the", "is", "are", "of", "in", "on", "to", "for", "with", "and",
    "or", "but", "that", "this", "it", "from", "by", "at", "be", "was", "has",
    "had", "can", "will", "may", "not", "no", "do", "did", "what", "how",
    "which", "who", "when", "where", "why",
})

_CHINESE_STOP_WORDS = frozenset({
    "的", "了", "在", "是", "和", "与", "或", "等", "中", "上", "下", "对",
    "被", "从", "到", "为", "以", "及", "其", "之", "而", "把", "让", "给",
    "向", "于", "就", "也", "都", "还", "要", "能", "会", "可", "应", "该",
    "已", "曾", "将", "正", "着", "过", "来", "去", "出", "起", "回", "开",
    "关", "比", "更", "最", "很", "多", "少", "大", "小", "长", "群",
})


# ── Enumerations (single definition point) ──

_VALID_GOAL_TYPES = frozenset({
    "exploratory", "panoramic_understanding", "tech_selection",
    "feasibility_assessment", "competitive_comparison", "academic_research",
    "fact_check", "background_check", "market_analysis", "other",
})

_VALID_DEPTHS = frozenset({"quick", "standard", "deep"})

_VALID_AUDIENCES = frozenset({"CTO", "engineer", "researcher", "general"})

_VALID_METRIC_TYPES = frozenset({
    "swe_bench_verified",
    "swe_bench_pro",
    "terminal_bench",
    "pr_merge_rate",
    "refactoring_safety",
    "custom",
})

_VALID_EVIDENCE_TYPES = frozenset({
    "official_data", "independent_benchmark", "third_party_estimate",
    "qualitative_trend", "expert_opinion",
})

_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})

_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})


# ── Goal-type classifications ──

_QUANTITATIVE_GOAL_TYPES = frozenset({
    "tech_selection",
    "competitive_comparison",
    "feasibility_assessment",
    "market_analysis",
    "academic_research",
})

_EXPLORATORY_GOAL_TYPES = frozenset({
    "exploratory", "panoramic_understanding", "background_check", "other",
})

_CONCRETENESS_STRICT_GOAL_TYPES = frozenset({
    "tech_selection", "competitive_comparison",
})


# ── Thresholds ──

_VAGUE_DENSITY_THRESHOLD = 0.10
_TIER_BALANCE_THRESHOLD = 0.30
_METHODOLOGY_MIN_WORDS = 150
_MIN_SOURCES = 2
_FETCHED_CONTENT_MIN_LENGTH = 200
_FETCHED_CONTENT_STUB_RATIO_BLOCKER = 0.30
_FETCHED_CONTENT_MIN_BY_TIER = {
    1: 1000,  # Academic papers — methodology, results, limitations
    2: 800,   # Official docs — API details, configuration
    3: 600,   # Industry blogs — context, nuance, caveats
    4: 400,   # Community posts — shorter but still fetched
}
_DEPTH_MIN_SOURCES_PER_DIRECTION = {"quick": 1, "standard": 3, "deep": 5}
_COVERAGE_THRESHOLD = 0.5
_OVERLONG_LINE_THRESHOLD = 500
