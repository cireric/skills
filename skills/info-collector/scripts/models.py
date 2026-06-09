from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Source:
    url: str
    title: str
    source_type: Literal["web", "github", "docs", "user_file"]
    source_lang: Literal["zh", "en"]
    content: str
    confidence: Literal["high", "medium", "low"] = "medium"
    quality: Literal["high", "medium", "low", "excluded"] = "medium"
    published_date: str | None = None
    duplicate_of: str | None = None
    filter_note: str = ""


@dataclass
class DataPoint:
    key: str
    value: str
    source_url: str


@dataclass
class Comparison:
    dimension: str
    values: dict[str, str]
    winner: str | None = None


@dataclass
class TimelineEvent:
    date: str
    event: str
    source_url: str


@dataclass
class Section:
    id: str
    title: str
    content: str
    confidence: Literal["high", "medium", "low"] = "medium"


@dataclass
class Claim:
    statement: str
    sources: list[str] = field(default_factory=list)
    type: Literal["fact", "opinion", "prediction"] = "fact"
    confidence: Literal["high", "medium", "low"] = "medium"
    contradicted_by: list[str] = field(default_factory=list)
    section_id: str = ""


@dataclass
class ConfidenceAssessment:
    conclusion: str
    confidence: str
    evidence_strength: str


@dataclass
class ConclusionData:
    recommendation: str = ""
    reasoning: str = ""
    confidence_assessments: list[ConfidenceAssessment] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    topic: str
    lang: str = "zh"
    depth: str = "standard"
    summary: str = ""
    sources: list[Source] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    data_points: list[DataPoint] = field(default_factory=list)
    comparisons: list[Comparison] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    timelines: list[TimelineEvent] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    conclusion_data: ConclusionData | None = None


SECTION_IDS_STANDARD: list[str] = [
    "summary",
    "overview",
    "analysis",
    "comparison",
    "practice",
    "verification",
    "risks",
    "conclusion",
]

SECTION_IDS_DEEP: list[str] = [
    "summary",
    "overview",
    "analysis",
    "comparison",
    "practice",
    "verification",
    "risks",
    "methodology",
    "timeline",
    "decision_matrix",
    "conclusion",
]

REPORT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "lang": {"type": "string", "enum": ["zh", "en"]},
        "depth": {"type": "string", "enum": ["standard", "deep"]},
        "summary": {"type": "string"},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "source_type": {"type": "string"},
                    "source_lang": {"type": "string"},
                    "content": {"type": "string"},
                    "confidence": {"type": "string"},
                },
                "required": ["url", "title", "content"],
            },
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "confidence": {"type": "string"},
                },
                "required": ["id", "title", "content"],
            },
        },
        "data_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "source_url": {"type": "string"},
                },
            },
        },
        "comparisons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string"},
                    "values": {"type": "object"},
                    "winner": {"type": "string"},
                },
            },
        },
        "contradictions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "timelines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "event": {"type": "string"},
                    "source_url": {"type": "string"},
                },
            },
        },
    },
    "required": ["topic", "depth", "sections"],
}
