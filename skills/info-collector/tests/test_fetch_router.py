import pytest
import json
from pathlib import Path
from scripts.fetch_strategies.base import FetchStrategy, UrlRewriter
from scripts.fetch_strategies.default import DefaultStrategy
from scripts.lib.utils import compute_url_hash


def test_default_strategy_no_rewrite():
    s = DefaultStrategy()
    assert s.rewrite_url("https://example.com/page") == "https://example.com/page"


def test_default_strategy_tools():
    s = DefaultStrategy()
    assert s.tools() == ["webfetch"]


def test_default_strategy_retries_tier4():
    s = DefaultStrategy()
    assert s.retries(4) == 1


def test_default_strategy_retries_tier1():
    s = DefaultStrategy()
    assert s.retries(1) == 2


from scripts.fetch_strategies.arxiv import ArxivStrategy


def test_arxiv_rewrite_pdf():
    s = ArxivStrategy()
    assert s.rewrite_url("https://arxiv.org/pdf/2509.16941") == "https://ar5iv.labs.arxiv.org/html/2509.16941"


def test_arxiv_rewrite_abs():
    s = ArxivStrategy()
    assert s.rewrite_url("https://arxiv.org/abs/2509.16941") == "https://ar5iv.labs.arxiv.org/html/2509.16941"


def test_arxiv_rewrite_html_passthrough():
    s = ArxivStrategy()
    assert s.rewrite_url("https://ar5iv.labs.arxiv.org/html/2509.16941") == "https://ar5iv.labs.arxiv.org/html/2509.16941"


def test_arxiv_rewrite_non_arxiv():
    s = ArxivStrategy()
    assert s.rewrite_url("https://example.com/paper") == "https://example.com/paper"


def test_arxiv_is_url_rewriter():
    s = ArxivStrategy()
    assert hasattr(s, "rewrite_url")
    assert not hasattr(s, "tools")


from scripts.fetch_strategies.github import GithubStrategy


def test_github_rewrite_repo():
    s = GithubStrategy()
    result = s.rewrite_url("https://github.com/openai/openai-agents-python")
    assert "README" in result or "readme" in result


def test_github_rewrite_non_github():
    s = GithubStrategy()
    assert s.rewrite_url("https://example.com/code") == "https://example.com/code"


def test_github_is_url_rewriter():
    s = GithubStrategy()
    assert hasattr(s, "rewrite_url")
    assert not hasattr(s, "tools")


from scripts.fetch_router import get_fetch_strategy, apply_url_rewrite, ComposedStrategy


def test_get_fetch_strategy_default():
    config = {"name": "Unknown", "domain": "unknown.com"}
    strategy = get_fetch_strategy(config)
    assert isinstance(strategy, DefaultStrategy)


def test_get_fetch_strategy_arxiv_with_config_tools():
    config = {"name": "arXiv", "domain": "arxiv.org", "fetch_strategy": "arxiv",
              "fetch": {"tools": ["exa_web_fetch_exa", "webfetch", "playwright"]}}
    strategy = get_fetch_strategy(config)
    assert isinstance(strategy, ComposedStrategy)
    assert strategy.rewrite_url("https://arxiv.org/abs/2509.16941") == "https://ar5iv.labs.arxiv.org/html/2509.16941"
    assert strategy.tools() == ["exa_web_fetch_exa", "webfetch", "playwright"]


def test_get_fetch_strategy_arxiv_without_config_tools():
    config = {"name": "arXiv", "domain": "arxiv.org", "fetch_strategy": "arxiv"}
    strategy = get_fetch_strategy(config)
    assert isinstance(strategy, ComposedStrategy)
    assert strategy.tools() == ["webfetch"]


def test_get_fetch_strategy_config_rewrite():
    config = {
        "name": "Medium",
        "domain": "medium.com",
        "fetch": {
            "url_rewrite": [
                {"match": r"medium\.com/p/(\w+)", "replace": r"medium.com/p/\1"}
            ],
            "tools": ["webfetch"]
        }
    }
    strategy = get_fetch_strategy(config)
    assert strategy.tools() == ["webfetch"]


def test_get_fetch_strategy_config_tools_without_rewrite():
    config = {"name": "PyPI", "domain": "pypi.org",
              "fetch": {"tools": ["exa_web_fetch_exa", "webfetch", "playwright"]}}
    strategy = get_fetch_strategy(config)
    assert strategy.tools() == ["exa_web_fetch_exa", "webfetch", "playwright"]


def test_apply_url_rewrite_no_match():
    rules = [{"match": r"arxiv\.org/pdf/(.+)", "replace": r"ar5iv.labs.arxiv.org/html/\1"}]
    assert apply_url_rewrite("https://example.com/page", rules) == "https://example.com/page"


def test_apply_url_rewrite_match():
    rules = [{"match": r"arxiv\.org/pdf/(.+)", "replace": r"ar5iv.labs.arxiv.org/html/\1"}]
    assert apply_url_rewrite("https://arxiv.org/pdf/2509.16941", rules) == "https://ar5iv.labs.arxiv.org/html/2509.16941"


def test_get_fetch_strategy_broken_strategy_falls_back():
    """When fetch_strategy points to a module that fails to load, fall back gracefully."""
    config = {"name": "Broken", "domain": "broken.com", "fetch_strategy": "nonexistent_strategy_xyz"}
    strategy = get_fetch_strategy(config)
    assert isinstance(strategy, DefaultStrategy)


from scripts.fetch_router import _load_url_rewriter


def test_load_url_rewriter_import_error_returns_none(monkeypatch, tmp_path):
    """When a strategy module raises ImportError, _load_url_rewriter returns None instead of crashing."""
    broken_file = tmp_path / "broken_strategy.py"
    broken_file.write_text("import nonexistent_module_xyz\n", encoding="utf-8")
    monkeypatch.setattr("scripts.fetch_router._STRATEGY_DIR", tmp_path)
    result = _load_url_rewriter("broken_strategy")
    assert result is None


class TestEndToEndFetchFlow:
    def test_arxiv_fetch_flow(self, tmp_path):
        cfg = {"fetch_strategy": "arxiv",
               "fetch": {"tools": ["exa_web_fetch_exa", "webfetch", "playwright"]}}
        url = "https://arxiv.org/pdf/2509.16941"

        strategy = get_fetch_strategy(cfg)
        assert isinstance(strategy, ComposedStrategy)

        rewritten = strategy.rewrite_url(url)
        assert rewritten == "https://ar5iv.labs.arxiv.org/html/2509.16941"

        tools = strategy.tools()
        assert tools == ["exa_web_fetch_exa", "webfetch", "playwright"]

        retries = strategy.retries(1)
        assert retries == 2

        url_hash = compute_url_hash(url)
        source_file = f"sources/{url_hash}.md"

        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        source_path = sources_dir / f"{url_hash}.md"
        source_path.write_text("# Fetched content", encoding="utf-8")

        collected = [{"url": url, "title": "Test Paper", "source_file": source_file}]
        collected_path = tmp_path / "collected.json"
        collected_path.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")

        loaded = json.loads(collected_path.read_text(encoding="utf-8"))
        assert loaded[0]["source_file"] == source_file
        assert (tmp_path / loaded[0]["source_file"]).exists()
