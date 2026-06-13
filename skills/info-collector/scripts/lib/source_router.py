"""Route by goal_type to recommended source tiers and search paths.

All source/routes data lives in config.json (the single source of truth).
This module provides pure lookup logic with an optional config injection
for testing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast


def _get_config(config: dict | None = None) -> dict:
    """Load config dict. Injects test config if provided, else reads from disk."""
    if config is not None:
        return config
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return cast(dict, json.load(f))


def get_route(goal_type: str, config: dict | None = None) -> dict:
    """Return route dict (entry_tier, path) for a goal_type."""
    cfg = _get_config(config)
    routes: dict = cfg.get("routes", {})
    return cast(
        dict, routes.get(goal_type, routes.get("other", {"entry_tier": 3, "path": [3, 2, 1]}))
    )


def recommend_sources(
    goal_type: str,
    config: dict | None = None,
) -> dict:
    """Return structured source recommendations for a goal_type."""
    cfg = _get_config(config)
    sources: dict = cfg.get("sources", {})
    routes: dict = cfg.get("routes", {})
    route = routes.get(goal_type, routes.get("other", {"entry_tier": 3, "path": [3, 2, 1]}))
    path_tiers: list[int] = route["path"]
    recommended: dict[int, list[dict]] = {}
    for t in path_tiers:
        tier_key = str(t)
        recommended[t] = list(sources.get(tier_key, {}).get("sources", []))
    all_sources: dict[int, list[dict]] = {}
    for tier_key, tier_data in sources.items():
        all_sources[int(tier_key)] = list(tier_data.get("sources", []))
    return {
        "goal_type": goal_type,
        "entry_tier": route["entry_tier"],
        "path": path_tiers,
        "recommended_sources": recommended,
        "all_sources": all_sources,
    }


def get_default_min_sources(goal_type: str, config: dict | None = None) -> int:
    """Return min_sources for a goal_type from config or default 2."""
    cfg = _get_config(config)
    defaults: dict = cfg.get("goal_type_defaults", {})
    goal_cfg: dict = defaults.get(goal_type, {})
    return cast(int, goal_cfg.get("min_sources", 2))


def get_default_depth(goal_type: str, config: dict | None = None) -> str:
    """Return search depth for a goal_type.

    Priority chain:
      1. goal_type_defaults[goal_type].depth (if goal_type has explicit config)
      2. config.default_depth (top-level config fallback)
      3. hardcoded 'standard'
    """
    cfg = _get_config(config)
    defaults: dict = cfg.get("goal_type_defaults", {}) or {}
    goal_cfg: dict = defaults.get(goal_type, {})
    if "depth" in goal_cfg:
        return cast(str, goal_cfg["depth"])
    config_depth = cfg.get("default_depth")
    if config_depth is not None:
        return cast(str, config_depth)
    return "standard"
