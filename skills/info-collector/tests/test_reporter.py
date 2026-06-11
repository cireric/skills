from __future__ import annotations

import json
from pathlib import Path

from scripts.reporter import build_front_matter, generate_report, sections_to_markdown


class TestBuildFrontMatter:
    def test_basic_structure(self):
        fm = build_front_matter("Test Topic", "tech_selection", "Scope desc", "passed", 2, 10)
        assert fm.startswith("---")
        assert fm.endswith("---")
        assert "topic: Test Topic" in fm
        assert "quality: passed" in fm
        assert "version: 1" in fm

    def test_includes_parent(self):
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3, parent="parent.md")
        assert "parent: parent.md" in fm
        assert "version: 1" in fm

    def test_custom_version(self):
        fm = build_front_matter("T", "fact_check", "S", "passed", 1, 3, version=3)
        assert "version: 3" in fm


class TestSectionsToMarkdown:
    def test_single_section(self):
        analysis = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "content": "Some content here.",
                    "claims": [{"text": "A claim.", "source_urls": ["https://example.com"]}],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "## Overview" in md
        assert "Some content here." in md
        assert "A claim." in md
        assert "https://example.com" in md

    def test_section_without_claims(self):
        analysis = {
            "sections": [
                {
                    "id": "intro",
                    "title": "Intro",
                    "content": "Just intro.",
                    "claims": [],
                }
            ],
        }
        md = sections_to_markdown(analysis)
        assert "Just intro." in md
        assert "Sources:" not in md


class TestGenerateReport:
    def test_full_report(self, tmp_path):
        _write_json(
            tmp_path / "analysis.json",
            {
                "topic": "AI Frameworks",
                "goal_type": "tech_selection",
                "sections": [
                    {
                        "id": "comparison",
                        "title": "Comparison",
                        "content": "PyTorch vs TensorFlow.",
                        "claims": [
                            {"text": "PyTorch is popular.", "source_urls": ["https://example.com"]}
                        ],
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "scope.json",
            {
                "topic": "AI Frameworks",
                "goal_type": "tech_selection",
                "scope_description": "Compare PyTorch and TensorFlow",
            },
        )
        report = generate_report(
            tmp_path / "analysis.json",
            tmp_path / "scope.json",
            quality="passed",
            search_rounds=2,
            source_count=5,
        )
        assert "topic: AI Frameworks" in report
        assert "quality: passed" in report
        assert "## Comparison" in report
        assert "PyTorch vs TensorFlow." in report
        assert "PyTorch is popular." in report


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
