"""Shared constants for the info-collector skill."""

from __future__ import annotations


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
