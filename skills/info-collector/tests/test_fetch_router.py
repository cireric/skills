import pytest
from pathlib import Path
from scripts.fetch_strategies.base import FetchStrategy
from scripts.fetch_strategies.default import DefaultStrategy


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


def test_arxiv_tools():
    s = ArxivStrategy()
    assert s.tools() == ["webfetch", "exa_web_fetch_exa"]


from scripts.fetch_strategies.github import GithubStrategy


def test_github_rewrite_repo():
    s = GithubStrategy()
    result = s.rewrite_url("https://github.com/openai/openai-agents-python")
    assert "README" in result or "readme" in result


def test_github_rewrite_non_github():
    s = GithubStrategy()
    assert s.rewrite_url("https://example.com/code") == "https://example.com/code"


def test_github_tools():
    s = GithubStrategy()
    assert s.tools() == ["webfetch", "exa_web_fetch_exa"]


from scripts.fetch_router import get_fetch_strategy, apply_url_rewrite


def test_get_fetch_strategy_default():
    config = {"name": "Unknown", "domain": "unknown.com"}
    strategy = get_fetch_strategy(config)
    assert isinstance(strategy, DefaultStrategy)


def test_get_fetch_strategy_arxiv():
    config = {"name": "arXiv", "domain": "arxiv.org", "fetch_strategy": "arxiv"}
    strategy = get_fetch_strategy(config)
    assert type(strategy).__name__ == "ArxivStrategy"


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


def test_apply_url_rewrite_no_match():
    rules = [{"match": r"arxiv\.org/pdf/(.+)", "replace": r"ar5iv.labs.arxiv.org/html/\1"}]
    assert apply_url_rewrite("https://example.com/page", rules) == "https://example.com/page"


def test_apply_url_rewrite_match():
    rules = [{"match": r"arxiv\.org/pdf/(.+)", "replace": r"ar5iv.labs.arxiv.org/html/\1"}]
    assert apply_url_rewrite("https://arxiv.org/pdf/2509.16941", rules) == "https://ar5iv.labs.arxiv.org/html/2509.16941"
