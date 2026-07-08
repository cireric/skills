from __future__ import annotations
import re
from pathlib import Path
from .fetch_strategies.base import FetchStrategy, UrlRewriter
from .fetch_strategies.default import DefaultStrategy


_STRATEGY_DIR = Path(__file__).parent / "fetch_strategies"


class ComposedStrategy:
    def __init__(self, rewriter: UrlRewriter | None, tools: list[str] | None = None,
                 url_rewrite_rules: list[dict] | None = None):
        self._rewriter = rewriter
        self._url_rewrite_rules = url_rewrite_rules or []
        self._tools = tools or ["webfetch"]

    def rewrite_url(self, url: str) -> str:
        if self._rewriter:
            return self._rewriter.rewrite_url(url)
        return apply_url_rewrite(url, self._url_rewrite_rules)

    def tools(self) -> list[str]:
        return self._tools

    def retries(self, tier: int) -> int:
        return 2 if tier <= 2 else 1


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


def _load_url_rewriter(strategy_name: str) -> UrlRewriter | None:
    module_path = _STRATEGY_DIR / f"{strategy_name}.py"
    if not module_path.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(strategy_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if (isinstance(attr, type) and
            attr_name.endswith("Strategy") and
            attr_name != "FetchStrategy" and
            attr_name != "UrlRewriter" and
            hasattr(attr, "rewrite_url")):
            return attr()
    return None


def get_fetch_strategy(source_config: dict) -> FetchStrategy:
    fetch_config = source_config.get("fetch", {})
    tools = fetch_config.get("tools")
    url_rewrite = fetch_config.get("url_rewrite", [])

    strategy_name = source_config.get("fetch_strategy")
    rewriter = _load_url_rewriter(strategy_name) if strategy_name else None

    if rewriter:
        return ComposedStrategy(rewriter, tools=tools)

    if url_rewrite or tools:
        return ConfigRewriteStrategy(url_rewrite, tools)

    return DefaultStrategy()
