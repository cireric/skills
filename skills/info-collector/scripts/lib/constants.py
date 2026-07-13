"""Shared constants for the info-collector skill.

Single source of truth for enumerations, thresholds, and classification sets.
When adding a new goal_type or metric_type, only this file needs updating.
"""

from __future__ import annotations

import re


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

# Safe alias map for common LLM-isms in `evidence_type`. Only maps to values that
# never unlock `exact` precision (third-party / opinion), so a wrong guess cannot
# escalate a claim's authority. Never maps to official_data / independent_benchmark.
_EVIDENCE_TYPE_ALIASES = {
    "blog": "third_party_estimate",
    "post": "third_party_estimate",
    "article": "third_party_estimate",
    "opinion": "expert_opinion",
    "commentary": "expert_opinion",
}

_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})
_VALID_PRECISION = frozenset({"exact", "range", "qualitative"})

_NON_EXACT_EVIDENCE_TYPES = frozenset({"third_party_estimate", "qualitative_trend", "expert_opinion"})

_VALID_SOURCE_VERIFICATIONS = frozenset({"source_confirmed", "source_absent", "source_indirect"})
_VALID_DEPTH_STRATEGIES = frozenset({"overview", "deep_dive", "comparison", "methodology"})
_MIN_KEY_INSIGHTS_PANORAMIC = 2
_SOURCE_INDIRECT_RATIO_WARN = 0.30
_INDIRECT_CITATION_PATTERNS = (
    re.compile(r"据\s*\S+\s*(报告|预测|发现|统计|调查|研究|分析)"),
    re.compile(r"\S+\s*(报告|预测|发现|统计|调查|研究|分析)\s*(显示|指出|表明|称)"),
    re.compile(r"(according to|based on|cited in|reported by)\s+\S+", re.IGNORECASE),
)
_VENDOR_SOURCE_TYPES = frozenset({
    "analyst_forecast", "vendor_benchmark", "vendor_survey", "vendor_blog",
})


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



# ── Thresholds ──

_VAGUE_DENSITY_THRESHOLD = 0.10
_TIER_BALANCE_THRESHOLD = 0.30
_METHODOLOGY_MIN_WORDS = 150
_MIN_SOURCES = 2
_SUBAGENT_DELEGATION_MIN_SECTIONS = 2
_SOURCES_DIR = "sources"
_SOURCE_FIDELITY_MISSING_RATIO_BLOCKER = 0.30
_SOURCE_FIDELITY_EXEMPT_RATIO_WARN = 0.50
_SOURCE_FIDELITY_SHALLOW_RATIO_BLOCKER = 0.30
_SOURCE_FIDELITY_SHALLOW_CHARS = 2000
_SOURCE_FIDELITY_THIN_RATIO_WARN = 0.50
_SOURCE_FIDELITY_THIN_CHARS = 5000
_SOURCE_FIDELITY_SNIPPET_OVERLAP_RATIO_BLOCKER = 0.30
_SOURCE_FIDELITY_SNIPPET_OVERLAP_THRESHOLD = 0.80
_FETCH_TIMEOUT_SECONDS = 60
_FETCH_PLAYWRIGHT_TIMEOUT = 30000
_FETCH_PLAYWRIGHT_CHANNEL_DEFAULT = "chrome"
_FETCH_PLAYWRIGHT_CHANNEL_FALLBACK = "chromium"
_FETCHED_CONTENT_INDEX_LENGTH = 200
_DEPTH_MIN_SOURCES = {"quick": 3, "standard": 5, "deep": 8}
_OVERLONG_LINE_THRESHOLD = 500
_SINGLE_SOURCE_RATIO = 0.5
# Axis-B multi-source corroboration: depth-dynamic WARN threshold for the ratio of
# single-source claims. quick is not checked (single source is expected); standard
# warns above 70%; deep warns above 50%.
_SINGLE_SOURCE_RATIO_QUICK = None
_SINGLE_SOURCE_RATIO_STANDARD = 0.70
_SINGLE_SOURCE_RATIO_DEEP = 0.50


def single_source_ratio_threshold(depth: str) -> float | None:
    """Return the single-source-ratio WARN threshold for a given search depth.

    Returns None when the depth should not be checked (quick).
    """
    return {
        "quick": _SINGLE_SOURCE_RATIO_QUICK,
        "standard": _SINGLE_SOURCE_RATIO_STANDARD,
        "deep": _SINGLE_SOURCE_RATIO_DEEP,
    }.get(depth, _SINGLE_SOURCE_RATIO)



# ── Vague phrases (content quality) ──

_VAGUE_PHRASES_ZH = frozenset({
    "比较优秀", "性能良好", "值得关注", "较为突出", "比较突出",
    "相对较好", "较为成熟", "相当不错", "比较强大", "较为完善",
    "比较稳定", "比较丰富",
})
_VAGUE_PHRASES_EN = frozenset({
    "relatively good", "quite impressive", "worth considering", "fairly well",
    "somewhat better", "reasonably good", "fairly strong", "quite capable",
    "generally positive", "relatively mature",
})


# ── Required section IDs per goal_type ──

_REQUIRED_SECTION_IDS: dict[str, list[str]] = {
    "tech_selection": ["overview", "comparison", "recommendation", "methodology"],
    "feasibility_assessment": ["overview", "analysis", "conclusion", "methodology"],
    "fact_check": ["claims", "evidence", "conclusion"],
    "competitive_comparison": ["overview", "comparison", "positioning", "methodology"],
    "academic_research": ["abstract", "findings", "references", "methodology"],
    "market_analysis": ["overview", "data", "trends", "conclusion", "methodology"],
}


# ── Artifact filenames ──

ARTIFACT_SCOPE = "scope.json"
ARTIFACT_COLLECTED = "collected.json"
ARTIFACT_ANALYSIS = "analysis.json"
ARTIFACT_PIPELINE_STATE = "pipeline_state.json"
ARTIFACT_REVIEW_REPORT = "review_report.md"
ARTIFACT_CONFIG = "config.json"


# ── Pipeline configuration ──

_VALID_TRANSITIONS_SET = {
    ("scope", "search"),
    ("search", "analysis"),
    ("analysis", "review"),
    ("review", "final"),
    ("review", "review"),
}

_PHASE_ARTIFACTS: dict[str, list[str]] = {
    "scope": [ARTIFACT_SCOPE, ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT, ARTIFACT_PIPELINE_STATE],
    "search": [ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT],
    "analysis": [ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT],
    "review": [ARTIFACT_REVIEW_REPORT],
    "final": [ARTIFACT_PIPELINE_STATE],
}


# ── Display labels ──

_TIER_LABELS: dict[str, str] = {
    "1": "★★★☆ Tier 1",
    "2": "★★☆☆ Tier 2",
    "3": "★☆☆☆ Tier 3",
    "4": "☆☆☆☆ Tier 4",
}

_LABELS: dict[tuple[str, str], str] = {
    ("sources", "en"): "Sources",
    ("sources", "zh"): "数据来源",
    ("references", "en"): "References",
    ("references", "zh"): "参考文献",
    ("test_conditions", "en"): "Test Conditions",
    ("test_conditions", "zh"): "测试环境",
    ("claim", "en"): "Claim",
    ("claim", "zh"): "声明",
    ("conditions", "en"): "Conditions",
    ("conditions", "zh"): "条件",
    ("date", "en"): "Date",
    ("date", "zh"): "日期",
    ("source_type", "en"): "Source Type",
    ("source_type", "zh"): "来源类型",
    ("methodology", "en"): "Methodology",
    ("methodology", "zh"): "方法论",
}
