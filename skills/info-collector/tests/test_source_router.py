from __future__ import annotations

import json
from pathlib import Path

from scripts.lib.source_router import (
    _get_config,
    get_default_depth,
    get_default_min_sources,
    get_route,
    recommend_sources,
)

TEST_CONFIG = {
    "sources": {
        "1": {
            "name": "Academic / Standards",
            "sources": [
                {"name": "arXiv", "domain": "arxiv.org", "site_query": "arxiv.org"},
            ],
        },
        "2": {
            "name": "Documentation / Open Source",
            "sources": [
                {"name": "GitHub", "domain": "github.com", "site_query": "github.com"},
            ],
        },
        "3": {
            "name": "Industry / Expert Blogs",
            "sources": [
                {"name": "Medium", "domain": "medium.com", "site_query": "medium.com"},
            ],
        },
        "4": {
            "name": "Community / UGC",
            "sources": [
                {"name": "Reddit", "domain": "reddit.com", "site_query": "reddit.com"},
                {"name": "Zhihu", "domain": "zhihu.com", "site_query": "zhihu.com"},
            ],
        },
    },
    "routes": {
        "exploratory": {"entry_tier": 4, "path": [4, 2]},
        "tech_selection": {"entry_tier": 2, "path": [2, 1]},
        "academic_research": {"entry_tier": 1, "path": [1]},
        "other": {"entry_tier": 3, "path": [3, 2, 1]},
    },
    "goal_type_defaults": {
        "exploratory": {"depth": "quick", "min_sources": 1},
    },
}


class TestGetRoute:
    def test_known_goal_type(self):
        route = get_route("tech_selection", TEST_CONFIG)
        assert route["entry_tier"] == 2  # noqa: PLR2004
        assert route["path"] == [2, 1]

    def test_unknown_goes_to_other(self):
        route = get_route("nonexistent", TEST_CONFIG)
        assert route["entry_tier"] == 3  # noqa: PLR2004

    def test_academic_only_tier1(self):
        route = get_route("academic_research", TEST_CONFIG)
        assert route["path"] == [1]


class TestRecommendSources:
    def test_returns_goal_type(self):
        result = recommend_sources("exploratory", TEST_CONFIG)
        assert result["goal_type"] == "exploratory"

    def test_includes_recommended_sources(self):
        result = recommend_sources("academic_research", TEST_CONFIG)
        assert 1 in result["recommended_sources"]
        sources = result["recommended_sources"][1]
        assert any(s["name"] == "arXiv" for s in sources)

    def test_all_sources_reflects_config(self):
        result = recommend_sources("exploratory", TEST_CONFIG)
        assert 4 in result["all_sources"]  # noqa: PLR2004
        names = [s["name"] for s in result["all_sources"][4]]
        assert "Zhihu" in names


class TestGetDefaults:
    def test_default_min_sources(self):
        assert get_default_min_sources("tech_selection", TEST_CONFIG) == 2  # noqa: PLR2004

    def test_default_min_sources_with_override(self):
        cfg = {"goal_type_defaults": {"exploratory": {"min_sources": 1}}}
        assert get_default_min_sources("exploratory", cfg) == 1

    def test_default_depth(self):
        assert get_default_depth("tech_selection", TEST_CONFIG) == "standard"

    def test_default_depth_with_override(self):
        cfg = {"goal_type_defaults": {"exploratory": {"depth": "quick"}}}
        assert get_default_depth("exploratory", cfg) == "quick"


class TestRouteConfigIntegrity:
    """Tests against the live config.json to validate route configuration integrity."""

    @staticmethod
    def _load_real_config() -> dict:
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_all_routes_have_valid_entry_tier(self):
        """Every route entry_tier must point to an existing source tier key."""
        config = self._load_real_config()
        source_tiers = set(config["sources"].keys())
        routes = config["routes"]
        for goal_type, route in routes.items():
            assert str(route["entry_tier"]) in source_tiers, (
                f"Route '{goal_type}' has entry_tier={route['entry_tier']} "
                f"which is not a valid source tier (keys: {sorted(source_tiers)})"
            )

    def test_fact_check_entry_tier_is_academic(self):
        """fact_check route must start at Academic/Standards tier (1) and include Community tier (4)."""
        config = self._load_real_config()
        route = config["routes"]["fact_check"]
        assert route["entry_tier"] == 1
        assert 4 in route["path"]

    def test_fact_check_recommends_academic_sources(self):
        """recommend_sources for fact_check must return Academic tier sources."""
        config = self._load_real_config()
        result = recommend_sources("fact_check", config)
        assert result["entry_tier"] == 1
        assert 1 in result["recommended_sources"]

    def test_default_depth_fallback_to_config_default(self):
        """When goal_type not in goal_type_defaults, config.default_depth is used."""
        cfg = {"goal_type_defaults": {}, "default_depth": "deep"}
        assert get_default_depth("unknown_type", cfg) == "deep"
        cfg2 = {"goal_type_defaults": None, "default_depth": "deep"}
        assert get_default_depth("unknown_type", cfg2) == "deep"

    def test_default_depth_goal_type_overrides_config(self):
        """Goal_type_defaults.depth takes priority over config.default_depth."""
        cfg = {
            "goal_type_defaults": {"exploratory": {"depth": "quick"}},
            "default_depth": "deep",
        }
        assert get_default_depth("exploratory", cfg) == "quick"

    def test_default_depth_hardcoded_fallback(self):
        """When neither goal_type_defaults nor config.default_depth exist, fall back to 'standard'."""
        cfg: dict = {}
        assert get_default_depth("unknown_type", cfg) == "standard"

    def test_get_config_injects_test_config(self):
        """_get_config returns the injected test config directly."""
        cfg = {"test": True}
        assert _get_config(cfg) is cfg
