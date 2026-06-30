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

_NON_EXACT_EVIDENCE_TYPES = frozenset({"third_party_estimate", "qualitative_trend", "expert_opinion"})


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
_SINGLE_SOURCE_RATIO = 0.5
_MAX_COVERED_DIRECTIONS = 3


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
ARTIFACT_SEARCH_PLAN = "search_plan.json"
ARTIFACT_PIPELINE_STATE = "pipeline_state.json"
ARTIFACT_REVIEW_REPORT = "review_report.md"
ARTIFACT_REVIEW_FALLBACK_LOG = "review_fallback.log"
ARTIFACT_CONFIG = "config.json"


# ── Pipeline configuration ──

_VALID_TRANSITIONS_SET = {
    ("scope", "search"),
    ("search", "analysis"),
    ("analysis", "review"),
    ("review", "final"),
    ("review", "review"),
    ("final", "cleanup"),
}

_PHASE_ARTIFACTS: dict[str, list[str]] = {
    "scope": [ARTIFACT_SCOPE, ARTIFACT_SEARCH_PLAN, ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT, ARTIFACT_PIPELINE_STATE],
    "search": [ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT],
    "analysis": [ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT],
    "review": [ARTIFACT_REVIEW_REPORT],
    "final": [ARTIFACT_PIPELINE_STATE],
    "cleanup": [ARTIFACT_SCOPE, ARTIFACT_SEARCH_PLAN, ARTIFACT_COLLECTED, ARTIFACT_ANALYSIS, ARTIFACT_REVIEW_REPORT, ARTIFACT_PIPELINE_STATE],
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
