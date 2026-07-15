from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .fetch_cleaner import clean
from .fetch_router import get_fetch_strategy
from .lib.constants import (
    _FETCHED_CONTENT_INDEX_LENGTH,
    _FETCH_PLAYWRIGHT_CHANNEL_DEFAULT,
    _FETCH_PLAYWRIGHT_CHANNEL_FALLBACK,
    _FETCH_PLAYWRIGHT_TIMEOUT,
    _SOURCE_FIDELITY_SHALLOW_CHARS,
    _SOURCES_DIR,
)
from .lib.utils import compute_url_hash


@dataclass
class FetchResult:
    url: str
    actual_url: str
    source_file: str | None
    url_hash: str
    char_count: int
    fetched_content: str
    fetch_failed: bool
    tool_used: str
    content_insufficient: bool
    source_tier: int | None


def _try_playwright(url: str, timeout: int = _FETCH_PLAYWRIGHT_TIMEOUT,
                     channel: str = _FETCH_PLAYWRIGHT_CHANNEL_DEFAULT) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    from markdownify import markdownify as md

    for ch in (channel, _FETCH_PLAYWRIGHT_CHANNEL_FALLBACK):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel=ch, headless=True)
                page = browser.new_page()
                try:
                    page.goto(url, wait_until="networkidle", timeout=timeout)
                except Exception:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                html = page.content()
                browser.close()
                return md(html)
        except Exception:
            continue
    return None


def _fetch_requests(url: str) -> str | None:
    try:
        import requests
        from markdownify import markdownify as md
        resp = requests.get(url, timeout=30, headers={"User-Agent": "InfoCollector/1.0"})
        resp.raise_for_status()
        text = _repair_encoding(resp)
        return md(text)
    except Exception:
        return None


def _repair_encoding(resp) -> str:
    text = resp.text
    try:
        resp.content.decode("utf-8")
        return text
    except UnicodeDecodeError:
        pass
    try:
        from charset_normalizer import from_bytes
        result = from_bytes(resp.content).best()
        if result:
            return resp.content.decode(result.encoding, errors="replace")
    except Exception:
        pass
    return text


_AUTONOMOUS_TOOL_MAP = {
    "webfetch": "_fetch_requests",
    "requests": "_fetch_requests",
    "playwright": "_try_playwright",
}


class Fetcher:
    def __init__(self, workdir: Path, config: dict | None = None):
        self._workdir = workdir
        self._config = config or {}
        self._sources_dir = workdir / _SOURCES_DIR
        self._fetch_defaults = self._config.get("fetch_defaults", {})
        self._shallow_threshold = self._fetch_defaults.get("shallow_threshold", _SOURCE_FIDELITY_SHALLOW_CHARS)
        self._pw_timeout = self._fetch_defaults.get("playwright_timeout", _FETCH_PLAYWRIGHT_TIMEOUT)
        self._pw_channel = self._fetch_defaults.get("playwright_channel", _FETCH_PLAYWRIGHT_CHANNEL_DEFAULT)
        self._playwright_enabled = self._fetch_defaults.get("playwright_enabled", True)

    def fetch(self, url: str, tier: int = 3, no_playwright: bool = False) -> FetchResult:
        url_hash = compute_url_hash(url)
        strategy = self._resolve_strategy(url)
        actual_url = strategy.rewrite_url(url)
        retries = strategy.retries(tier)
        tools = strategy.tools()

        content, tool_used = self._try_tools(actual_url, tools, retries, tier, no_playwright)

        if content is not None:
            content = clean(content, tool_used)
            return self._save_and_build_result(url, actual_url, url_hash, content, tool_used, tier)

        return FetchResult(
            url=url, actual_url=actual_url, source_file=None,
            url_hash=url_hash, char_count=0, fetched_content="",
            fetch_failed=True, tool_used="", content_insufficient=True,
            source_tier=self.infer_tier(url),
        )

    def save_piped(self, url: str, raw: str, tool_used: str = "piped",
                   actual_url: str | None = None, tier: int = 3) -> FetchResult:
        url_hash = compute_url_hash(url)
        content, parsed_tool, parsed_actual = _parse_piped_raw(raw, tool_used, actual_url or url)
        if not content:
            return FetchResult(
                url=url, actual_url=parsed_actual, source_file=None,
                url_hash=url_hash, char_count=0, fetched_content="",
                fetch_failed=True, tool_used=parsed_tool, content_insufficient=True,
                source_tier=self.infer_tier(url),
            )
        return self._save_and_build_result(url, parsed_actual, url_hash, content, parsed_tool, tier)

    def infer_tier(self, url: str) -> int | None:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        sources = self._config.get("sources", {})
        for tier_str, tier_data in sources.items():
            for source in tier_data.get("sources", []):
                src_domain = source.get("domain", "").lower()
                if src_domain and (domain == src_domain or domain.endswith("." + src_domain)):
                    return int(tier_str)
        return None

    def _resolve_strategy(self, url: str):
        source_config = self._find_source_config(url)
        if source_config:
            return get_fetch_strategy(source_config)
        from .fetch_strategies.default import DefaultStrategy
        return DefaultStrategy()

    def _find_source_config(self, url: str) -> dict | None:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        sources = self._config.get("sources", {})
        for tier_data in sources.values():
            for source in tier_data.get("sources", []):
                src_domain = source.get("domain", "").lower()
                if src_domain and (domain == src_domain or domain.endswith("." + src_domain)):
                    return source
        return None

    def _try_tools(self, url: str, tools: list[str], retries: int,
                   tier: int, no_playwright: bool) -> tuple[str | None, str]:
        best_shallow: tuple[str, str] | None = None
        for tool in tools:
            if tool == "exa_web_fetch_exa":
                continue
            if tool == "playwright" and (no_playwright or not self._playwright_enabled):
                continue
            impl_name = _AUTONOMOUS_TOOL_MAP.get(tool)
            if impl_name is None:
                continue
            for attempt in range(retries):
                result = self._call_tool_impl(impl_name, url)
                if result is None:
                    continue
                display_tool = tool if tool != "requests" else "webfetch"
                if len(result) >= self._shallow_threshold:
                    return result, display_tool
                if best_shallow is None or len(result) > len(best_shallow[0]):
                    best_shallow = (result, display_tool)
        return best_shallow if best_shallow is not None else (None, "")

    def _call_tool_impl(self, impl_name: str, url: str) -> str | None:
        if impl_name == "_fetch_requests":
            return _fetch_requests(url)
        if impl_name == "_try_playwright":
            return _try_playwright(url, timeout=self._pw_timeout, channel=self._pw_channel)
        return None

    def _save_and_build_result(self, url: str, actual_url: str, url_hash: str,
                                content: str, tool_used: str, tier: int) -> FetchResult:
        self._sources_dir.mkdir(parents=True, exist_ok=True)
        source_file = f"{_SOURCES_DIR}/{url_hash}.md"
        path = self._workdir / source_file
        path.write_text(content, encoding="utf-8")

        fetched_content = content[:_FETCHED_CONTENT_INDEX_LENGTH] if content else ""
        char_count = len(content) if content else 0
        content_insufficient = char_count < self._shallow_threshold

        return FetchResult(
            url=url, actual_url=actual_url, source_file=source_file,
            url_hash=url_hash, char_count=char_count,
            fetched_content=fetched_content, fetch_failed=False,
            tool_used=tool_used, content_insufficient=content_insufficient,
            source_tier=self.infer_tier(url),
        )


def _parse_piped_raw(raw: str, default_tool: str,
                     default_url: str) -> tuple[str, str, str | None]:
    stripped = raw.strip()
    if not stripped:
        return "", default_tool, default_url
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            return (
                data.get("content", ""),
                data.get("tool_used", default_tool),
                data.get("actual_url", default_url),
            )
        except json.JSONDecodeError:
            pass
    return raw, default_tool, default_url
