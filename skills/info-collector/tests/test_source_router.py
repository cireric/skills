from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.source_router import (
    _get_config,
    get_default_depth,
    get_default_min_sources,
    get_route,
    recommend_sources,
)
from scripts.lib.utils import config_path

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


class TestOptionalTiers:
    def test_optional_tiers_returned(self):
        cfg = {
            "sources": {"1": {"sources": []}, "2": {"sources": []}, "3": {"sources": []}, "4": {"sources": []}},
            "routes": {"panoramic_understanding": {"entry_tier": 4, "path": [4, 3, 1], "optional_tiers": [2]}},
        }
        route = get_route("panoramic_understanding", cfg)
        assert route["optional_tiers"] == [2]

    def test_optional_tiers_missing_is_empty(self):
        cfg = {
            "sources": {"1": {"sources": []}, "2": {"sources": []}, "3": {"sources": []}, "4": {"sources": []}},
            "routes": {"tech_selection": {"entry_tier": 2, "path": [2, 1]}},
        }
        route = get_route("tech_selection", cfg)
        assert route.get("optional_tiers", []) == []

    def test_recommend_sources_includes_optional_tiers(self):
        cfg = {
            "sources": {
                "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org"}]},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
                "3": {"sources": [{"name": "Medium", "domain": "medium.com"}]},
                "4": {"sources": [{"name": "Reddit", "domain": "reddit.com"}]},
            },
            "routes": {"panoramic_understanding": {"entry_tier": 4, "path": [4, 3, 1], "optional_tiers": [2]}},
        }
        result = recommend_sources("panoramic_understanding", cfg)
        assert 2 in result["recommended_sources"]
        assert any(s["name"] == "GitHub" for s in result["recommended_sources"][2])

    def test_cmd_source_output_includes_optional_tiers(self):
        cfg = {
            "sources": {
                "1": {"sources": []},
                "2": {"sources": [{"name": "GitHub", "domain": "github.com"}]},
                "3": {"sources": []},
                "4": {"sources": []},
            },
            "routes": {"panoramic_understanding": {"entry_tier": 4, "path": [4, 3, 1], "optional_tiers": [2]}},
        }
        result = recommend_sources("panoramic_understanding", cfg)
        assert "optional_tiers" in result
        assert result["optional_tiers"] == [2]


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


class TestNewSourcesInLiveConfig:
    """Validate 10 new sources appear in recommend_sources against live config."""

    @staticmethod
    def _load_real_config() -> dict:
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_tier1_has_acl_anthology(self):
        config = self._load_real_config()
        result = recommend_sources("academic_research", config)
        tier1_names = [s["name"] for s in result["all_sources"][1]]
        assert "ACL Anthology" in tier1_names

    def test_tier1_has_semantic_scholar(self):
        config = self._load_real_config()
        result = recommend_sources("academic_research", config)
        tier1_names = [s["name"] for s in result["all_sources"][1]]
        assert "Semantic Scholar" in tier1_names

    def test_tier2_has_hugging_face(self):
        config = self._load_real_config()
        result = recommend_sources("tech_selection", config)
        tier2_names = [s["name"] for s in result["all_sources"][2]]
        assert "Hugging Face" in tier2_names

    def test_tier2_has_pypi(self):
        config = self._load_real_config()
        result = recommend_sources("tech_selection", config)
        tier2_names = [s["name"] for s in result["all_sources"][2]]
        assert "PyPI" in tier2_names

    def test_tier2_has_readthedocs(self):
        config = self._load_real_config()
        result = recommend_sources("tech_selection", config)
        tier2_names = [s["name"] for s in result["all_sources"][2]]
        assert "ReadTheDocs" in tier2_names

    def test_tier3_has_substack(self):
        config = self._load_real_config()
        result = recommend_sources("other", config)
        tier3_names = [s["name"] for s in result["all_sources"][3]]
        assert "Substack" in tier3_names

    def test_tier3_has_towards_data_science(self):
        config = self._load_real_config()
        result = recommend_sources("other", config)
        tier3_names = [s["name"] for s in result["all_sources"][3]]
        assert "Towards Data Science" in tier3_names

    def test_tier3_has_the_new_stack(self):
        config = self._load_real_config()
        result = recommend_sources("other", config)
        tier3_names = [s["name"] for s in result["all_sources"][3]]
        assert "The New Stack" in tier3_names

    def test_tier4_has_hacker_news(self):
        config = self._load_real_config()
        result = recommend_sources("exploratory", config)
        tier4_names = [s["name"] for s in result["all_sources"][4]]
        assert "Hacker News" in tier4_names

    def test_tier4_has_dev_to(self):
        config = self._load_real_config()
        result = recommend_sources("exploratory", config)
        tier4_names = [s["name"] for s in result["all_sources"][4]]
        assert "Dev.to" in tier4_names


class TestSourceLanguageField:
    """Validate language field on source entries in live config."""

    @staticmethod
    def _load_real_config() -> dict:
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_cnki_has_language_zh(self):
        config = self._load_real_config()
        tier1 = config["sources"]["1"]["sources"]
        cnki = next(s for s in tier1 if s["name"] == "CNKI")
        assert cnki.get("language") == "zh"

    def test_zhihu_has_language_zh(self):
        config = self._load_real_config()
        tier4 = config["sources"]["4"]["sources"]
        zhihu = next(s for s in tier4 if s["name"] == "Zhihu")
        assert zhihu.get("language") == "zh"

    def test_arxiv_defaults_to_en(self):
        config = self._load_real_config()
        tier1 = config["sources"]["1"]["sources"]
        arxiv = next(s for s in tier1 if s["name"] == "arXiv")
        assert arxiv.get("language", "en") == "en"


class TestRouteAdjustments:
    """Validate updated routes for competitive_comparison, market_analysis, background_check."""

    @staticmethod
    def _load_real_config() -> dict:
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_competitive_comparison_entry_tier(self):
        config = self._load_real_config()
        route = get_route("competitive_comparison", config)
        assert route["entry_tier"] == 2

    def test_competitive_comparison_path(self):
        config = self._load_real_config()
        route = get_route("competitive_comparison", config)
        assert route["path"] == [2, 1, 3, 4]

    def test_market_analysis_path(self):
        config = self._load_real_config()
        route = get_route("market_analysis", config)
        assert route["path"] == [3, 4, 1, 2]

    def test_background_check_path(self):
        config = self._load_real_config()
        route = get_route("background_check", config)
        assert route["path"] == [3, 2, 1, 4]


@pytest.fixture(scope="module")
def _real_config():
    with open(config_path(), encoding="utf-8") as f:
        return json.load(f)


EXPECTED_ROUTES = {
    "exploratory": {"entry_tier": 4, "path": [4, 3, 2]},
    "panoramic_understanding": {"entry_tier": 4, "path": [4, 3, 1], "optional_tiers": [2]},
    "tech_selection": {"entry_tier": 2, "path": [2, 3, 4, 1]},
    "feasibility_assessment": {"entry_tier": 2, "path": [2, 1, 3]},
    "competitive_comparison": {"entry_tier": 2, "path": [2, 1, 3, 4]},
    "academic_research": {"entry_tier": 1, "path": [1], "optional_tiers": [2]},
    "fact_check": {"entry_tier": 1, "path": [1, 2, 4]},
    "background_check": {"entry_tier": 3, "path": [3, 2, 1, 4]},
    "market_analysis": {"entry_tier": 3, "path": [3, 4, 1, 2]},
    "other": {"entry_tier": 3, "path": [3, 2, 1]},
}


class TestConfigStructuralValidation:

    def test_four_tiers_present(self, _real_config):
        for key in ("1", "2", "3", "4"):
            assert key in _real_config["sources"]
            tier = _real_config["sources"][key]
            assert "name" in tier
            assert isinstance(tier["sources"], list)

    def test_every_source_has_required_fields(self, _real_config):
        for tier_key, tier_data in _real_config["sources"].items():
            for src in tier_data["sources"]:
                assert "name" in src, f"Tier {tier_key} source missing 'name'"
                assert "domain" in src, f"{src.get('name', '?')} missing 'domain'"
                assert "site_query" in src, f"{src['name']} missing 'site_query'"
                assert "fetch" in src, f"{src['name']} missing 'fetch'"
                assert "tools" in src["fetch"], f"{src['name']} fetch missing 'tools'"

    def test_chinese_sources_have_language_zh(self, _real_config):
        zh_names = {"CNKI", "Wanfang", "CQVIP", "Zhihu"}
        found = set()
        for tier_data in _real_config["sources"].values():
            for src in tier_data["sources"]:
                if src["name"] in zh_names:
                    assert src.get("language") == "zh", f"{src['name']} language != 'zh'"
                    found.add(src["name"])
        assert found == zh_names, f"Missing zh sources: {zh_names - found}"

    def test_arxiv_has_fetch_strategy_arxiv(self, _real_config):
        tier1 = _real_config["sources"]["1"]["sources"]
        arxiv = next(s for s in tier1 if s["name"] == "arXiv")
        assert arxiv.get("fetch_strategy") == "arxiv"

    def test_github_has_fetch_strategy_github(self, _real_config):
        tier2 = _real_config["sources"]["2"]["sources"]
        github = next(s for s in tier2 if s["name"] == "GitHub")
        assert github.get("fetch_strategy") == "github"

    def test_ten_routes_present(self, _real_config):
        routes = _real_config["routes"]
        assert len(routes) == 10
        for gt in EXPECTED_ROUTES:
            assert gt in routes, f"Missing route for '{gt}'"

    def test_each_route_has_entry_tier_and_path(self, _real_config):
        for gt, route in _real_config["routes"].items():
            assert "entry_tier" in route, f"{gt} missing entry_tier"
            assert "path" in route, f"{gt} missing path"

    def test_entry_tier_is_integer_1_to_4(self, _real_config):
        for gt, route in _real_config["routes"].items():
            et = route["entry_tier"]
            assert isinstance(et, int) and 1 <= et <= 4, f"{gt} entry_tier={et}"

    def test_path_is_nonempty_list_of_tier_ints(self, _real_config):
        for gt, route in _real_config["routes"].items():
            p = route["path"]
            assert isinstance(p, list) and len(p) > 0, f"{gt} path empty or not list"
            for t in p:
                assert isinstance(t, int) and 1 <= t <= 4, f"{gt} path element {t}"

    def test_optional_tiers_present_where_expected(self, _real_config):
        routes = _real_config["routes"]
        assert "optional_tiers" in routes["panoramic_understanding"]
        assert routes["panoramic_understanding"]["optional_tiers"] == [2]
        assert "optional_tiers" in routes["academic_research"]
        assert routes["academic_research"]["optional_tiers"] == [2]
        no_optional = {"exploratory", "tech_selection", "feasibility_assessment",
                       "competitive_comparison", "fact_check", "background_check",
                       "market_analysis", "other"}
        for gt in no_optional:
            assert routes[gt].get("optional_tiers", []) == [], f"{gt} should have no optional_tiers"


class TestRoutePathInvariants:

    def test_entry_tier_is_first_in_path(self, _real_config):
        for gt, route in _real_config["routes"].items():
            assert route["entry_tier"] == route["path"][0], (
                f"{gt}: entry_tier={route['entry_tier']} != path[0]={route['path'][0]}"
            )

    def test_path_has_no_duplicates(self, _real_config):
        for gt, route in _real_config["routes"].items():
            assert len(route["path"]) == len(set(route["path"])), (
                f"{gt}: path has duplicates: {route['path']}"
            )

    def test_path_elements_in_1_to_4(self, _real_config):
        for gt, route in _real_config["routes"].items():
            for t in route["path"]:
                assert t in {1, 2, 3, 4}, f"{gt}: path element {t} not in {{1,2,3,4}}"

    def test_optional_tiers_disjoint_from_path(self, _real_config):
        for gt, route in _real_config["routes"].items():
            opt = set(route.get("optional_tiers", []))
            path_set = set(route["path"])
            assert opt.isdisjoint(path_set), (
                f"{gt}: optional_tiers {opt} overlaps with path {path_set}"
            )

    def test_every_route_has_nonempty_path(self, _real_config):
        for gt, route in _real_config["routes"].items():
            assert len(route["path"]) >= 1, f"{gt}: path is empty"


class TestSourceDomainUniqueness:

    def test_no_duplicate_domains_within_tier(self, _real_config):
        for tier_key, tier_data in _real_config["sources"].items():
            domains = [s["domain"] for s in tier_data["sources"]]
            assert len(domains) == len(set(domains)), (
                f"Tier {tier_key} has duplicate domains: {domains}"
            )

    def test_no_duplicate_domains_across_tiers(self, _real_config):
        all_domains = []
        for tier_data in _real_config["sources"].values():
            all_domains.extend(s["domain"] for s in tier_data["sources"])
        assert len(all_domains) == len(set(all_domains)), (
            f"Cross-tier duplicate domains found"
        )

    def test_all_domains_are_nonempty_strings(self, _real_config):
        for tier_key, tier_data in _real_config["sources"].items():
            for src in tier_data["sources"]:
                assert isinstance(src["domain"], str) and len(src["domain"]) > 0, (
                    f"Tier {tier_key} source {src.get('name', '?')} has empty/missing domain"
                )


class TestChineseSourceCountInTier1:

    def test_tier1_has_exactly_4_chinese_sources(self, _real_config):
        tier1 = _real_config["sources"]["1"]["sources"]
        zh_sources = [s for s in tier1 if s.get("language") == "zh"]
        zh_names = {s["name"] for s in zh_sources}
        assert zh_names == {"CNKI", "Wanfang", "CQVIP", "CBOA"}
        assert len(zh_sources) == 4

    def test_tier4_has_exactly_1_chinese_source(self, _real_config):
        tier4 = _real_config["sources"]["4"]["sources"]
        zh_sources = [s for s in tier4 if s.get("language") == "zh"]
        zh_names = {s["name"] for s in zh_sources}
        assert zh_names == {"Zhihu"}
        assert len(zh_sources) == 1
