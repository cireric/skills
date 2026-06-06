"""Validate reading-grill SKILL.md structure and content."""

import re
from pathlib import Path

import pytest

SKILL_PATH = (
    Path(__file__).resolve().parent.parent / "SKILL.md"
)


class TestSkillStructure:
    """SKILL.md must follow OpenCode skill conventions."""

    def test_file_exists(self):
        assert SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"

    def test_has_yaml_frontmatter(self):
        content = SKILL_PATH.read_text()
        assert content.startswith("---")
        assert "---" in content[3:], "Must close YAML frontmatter"

    def test_has_name_field(self):
        content = SKILL_PATH.read_text()
        assert "name: reading-grill" in content, "Must declare skill name"

    def test_has_description(self):
        content = SKILL_PATH.read_text()
        assert "description:" in content, "Must have description"

    def test_has_trigger_keywords(self):
        content = SKILL_PATH.read_text().lower()
        triggers = [
            "reading grill",
            "comprehension",
            "理解检查",
            "读书拷问",
        ]
        for trigger in triggers:
            assert trigger in content, f"Missing trigger keyword: {trigger}"

    def test_has_three_layers_defined(self):
        content = SKILL_PATH.read_text()
        assert "L1 Recall" in content, "Must define L1 Recall layer"
        assert "L2 Understanding" in content, "Must define L2 Understanding layer"
        assert "L3 Critical reflection" in content, "Must define L3 Critical reflection layer"

    def test_transition_rule_present(self):
        content = SKILL_PATH.read_text()
        assert "At least 2 questions" in content, "Must specify transition rule"

    def test_rules_section_has_numbered_items(self):
        content = SKILL_PATH.read_text()
        rules = re.findall(r"^\d+\.\s+\*\*.+\*\*", content, re.MULTILINE)
        assert len(rules) >= 5, f"Expected ≥5 numbered rules, found {len(rules)}"

    def test_ending_conditions(self):
        content = SKILL_PATH.read_text()
        assert 'User says "停"' in content, "Must define stop condition"
        assert "3 consecutive L3 passes" in content, "Must define completion condition"


class TestContentQuality:
    """Behavioral tests for reading-grill content quality."""

    def test_no_direct_answers(self):
        """Skill must not provide answers — only questions."""
        content = SKILL_PATH.read_text()
        # Check that rules enforce Socratic method
        assert "Never correct" in content
        assert "Never evaluate" in content
        assert "guide self-discovery" in content

    def test_one_question_per_turn(self):
        content = SKILL_PATH.read_text()
        assert "One question per turn" in content

    def test_avoids_vague_language(self):
        """Skill instructions should be concrete, not vague."""
        content = SKILL_PATH.read_text()
        vague_terms = ["maybe", "perhaps", "sort of", "kind of"]
        for term in vague_terms:
            assert term not in content.lower(), f"Avoid vague term: {term}"

    def test_has_three_layers_described(self):
        content = SKILL_PATH.read_text()
        # Each layer should have a description
        assert "L1 Recall" in content and "作者说的 X 具体指什么" in content
        assert "L2 Understanding" in content and "为什么 A 导致 B" in content
        assert "L3 Critical reflection" in content and "你同意吗" in content

    def test_follow_up_question_rule(self):
        content = SKILL_PATH.read_text()
        # Should specify how to handle wrong answers
        assert "当 wrong" in content or "contradiction" in content or "矛盾" in content


class TestSkillFormat:
    """Format and layout tests."""

    def test_has_when_to_use_section(self):
        content = SKILL_PATH.read_text()
        assert "## When to Use" in content

    def test_has_three_layers_section(self):
        content = SKILL_PATH.read_text()
        assert "## Three Layers" in content

    def test_has_rules_section(self):
        content = SKILL_PATH.read_text()
        assert "## Rules" in content

    def test_has_ending_section(self):
        content = SKILL_PATH.read_text()
        assert "## Ending" in content

    def test_frontmatter_has_required_fields(self):
        content = SKILL_PATH.read_text()
        lines = content.split("\n")
        in_frontmatter = False
        frontmatter_keys = []
        for line in lines:
            if line == "---":
                if in_frontmatter:
                    break
                in_frontmatter = True
                continue
            if in_frontmatter and ":" in line:
                key = line.split(":")[0].strip()
                frontmatter_keys.append(key)

        assert "name" in frontmatter_keys
        assert "description" in frontmatter_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
