from __future__ import annotations
import re
from pathlib import Path
from .fetch_strategies.base import FetchStrategy
from .fetch_strategies.default import DefaultStrategy


_STRATEGY_DIR = Path(__file__).parent / "fetch_strategies"


class ConfigRewriteStrategy:
    def __init__(self, rules: list[dict], tools: list[str] | None = None):
        self._rules = rules
        self._tools = tools or ["webfetch"]

    def rewrite_url(self, url: str) -> str:
        return apply_url_rewrite(url, self._rules)

    def tools(self) -> list[str]:
        return self._tools

    def retries(self, tier: int) -> int:
        return 2 if tier <= 2 else 1


def apply_url_rewrite(url: str, rules: list[dict]) -> str:
    for rule in rules:
        pattern = rule.get("match", "")
        replacement = rule.get("replace", "")
        new_url, count = re.subn(pattern, replacement, url)
        if count > 0:
            return new_url
    return url


def get_fetch_strategy(source_config: dict) -> FetchStrategy:
    strategy_name = source_config.get("fetch_strategy")
    if strategy_name:
        module_path = _STRATEGY_DIR / f"{strategy_name}.py"
        if module_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location(strategy_name, module_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type) and
                    attr_name.endswith("Strategy") and
                    attr_name != "FetchStrategy" and
                    hasattr(attr, "rewrite_url")):
                    return attr()
    fetch_config = source_config.get("fetch", {})
    url_rewrite = fetch_config.get("url_rewrite", [])
    tools = fetch_config.get("tools")
    if url_rewrite or tools:
        return ConfigRewriteStrategy(url_rewrite, tools)
    return DefaultStrategy()
