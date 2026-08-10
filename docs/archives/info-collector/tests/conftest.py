import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _make_scope(workdir, goal_type="tech_selection", depth="standard",
                report_language=None, english_title=None,
                search_directions=None, audience="engineer",
                scope_description="Test scope"):
    data = {
        "topic": "Test",
        "goal_type": goal_type,
        "depth": depth,
        "audience": audience,
        "scope_description": scope_description,
        "search_directions": search_directions or ["AI", "ML"],
    }
    if report_language is not None:
        data["report_language"] = report_language
    if english_title is not None:
        data["english_title"] = english_title
    _write_json(workdir / "scope.json", data)


@pytest.fixture(autouse=True)
def _inject_helpers(request):
    request.module._write_json = _write_json
    request.module._make_scope = _make_scope
