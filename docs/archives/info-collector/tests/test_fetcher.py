from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from scripts.fetcher import Fetcher, FetchResult, _parse_piped_raw, _detect_content_quality
from scripts.lib.utils import compute_url_hash


_SAMPLE_CONFIG = {
    "sources": {
        "1": {"sources": [{"name": "arXiv", "domain": "arxiv.org", "fetch_strategy": "arxiv", "fetch": {"tools": ["exa_web_fetch_exa", "webfetch", "playwright"]}}]},
        "2": {"sources": [{"name": "GitHub", "domain": "github.com", "fetch_strategy": "github", "fetch": {"tools": ["exa_web_fetch_exa", "webfetch", "playwright"]}}]},
        "3": {"sources": [{"name": "Medium", "domain": "medium.com", "fetch": {"tools": ["webfetch", "exa_web_fetch_exa", "playwright"]}}]},
        "4": {"sources": [{"name": "Reddit", "domain": "reddit.com", "fetch": {"tools": ["webfetch", "playwright"]}}]},
    },
    "fetch_defaults": {
        "source_dir": ".workdir/sources/",
        "shallow_threshold": 2000,
        "playwright_enabled": True,
        "playwright_channel": "chrome",
        "playwright_timeout": 30000,
    },
}


@pytest.fixture
def workdir(tmp_path):
    w = tmp_path / ".workdir"
    w.mkdir()
    (w / "sources").mkdir()
    return w


@pytest.fixture
def fetcher(workdir):
    return Fetcher(workdir, _SAMPLE_CONFIG)


class TestFetchAutonomous:
    def test_requests_success(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 3000):
            result = fetcher.fetch("https://example.com/paper", tier=2)
        assert result.fetch_failed is False
        assert result.char_count >= 2000
        assert result.source_file is not None
        assert (workdir / result.source_file).exists()

    def test_requests_failure_fallback_to_playwright(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.fetch_failed is False
        assert result.tool_used == "playwright"

    def test_all_tools_exhausted(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value=None):
                result = fetcher.fetch("https://example.com/paper", tier=2)
        assert result.fetch_failed is True
        assert result.source_file is None
        assert result.char_count == 0

    def test_content_insufficient_triggers_next_tool(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="short"):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.content_insufficient is False
        assert result.tool_used == "playwright"
        assert result.char_count >= 2000

    def test_no_playwright_flag_skips_playwright(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000) as mock_pw:
                result = fetcher.fetch("https://medium.com/@user/article", tier=3, no_playwright=True)
        mock_pw.assert_not_called()
        assert result.fetch_failed is True

    def test_url_hash_uses_original_url(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 3000):
            result = fetcher.fetch("https://arxiv.org/abs/2503.15223", tier=1)
        assert result.url_hash == compute_url_hash("https://arxiv.org/abs/2503.15223")

    def test_url_rewrite_from_strategy(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 3000):
            result = fetcher.fetch("https://arxiv.org/abs/2503.15223", tier=1)
        assert result.actual_url != result.url
        assert "ar5iv" in result.actual_url

    def test_idempotent_overwrite(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="aaa" * 1000):
            result1 = fetcher.fetch("https://example.com/page", tier=2)
        with patch("scripts.fetcher._fetch_requests", return_value="bbb" * 1000):
            result2 = fetcher.fetch("https://example.com/page", tier=2)
        content = (workdir / result2.source_file).read_text(encoding="utf-8")
        assert "bbb" in content

    def test_strategy_tools_order_respected(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.tool_used == "playwright"

    def test_exa_web_fetch_exa_skipped(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 3000) as mock_req:
            result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.fetch_failed is False
        assert result.tool_used == "webfetch"


class TestBestShallowContent:
    def test_shallow_content_saved_not_discarded(self, fetcher, workdir):
        """All tools return < threshold → save best shallow content, not fetch_failed."""
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 500):
            with patch("scripts.fetcher._try_playwright", return_value="y" * 300):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.fetch_failed is False
        assert result.content_insufficient is True
        assert result.char_count >= 500
        assert result.tool_used == "webfetch"
        assert (workdir / result.source_file).exists()

    def test_best_shallow_picks_longest(self, fetcher, workdir):
        """requests returns 300 chars, playwright returns 800 chars → pick playwright."""
        with patch("scripts.fetcher._fetch_requests", return_value="x" * 300):
            with patch("scripts.fetcher._try_playwright", return_value="y" * 800):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.fetch_failed is False
        assert result.content_insufficient is True
        assert result.char_count >= 800
        assert result.tool_used == "playwright"

    def test_all_none_returns_fetch_failed(self, fetcher, workdir):
        """All tools return None → fetch_failed, no shallow content."""
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value=None):
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        assert result.fetch_failed is True
        assert result.char_count == 0


class TestPipedMode:
    def test_piped_plain_text(self, fetcher, workdir):
        content = "# Paper Title\n\n" + "x" * 3000
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is False
        assert result.tool_used == "piped"
        assert (workdir / result.source_file).exists()

    def test_piped_skip_cleaning(self, fetcher, workdir):
        content = "# Title\n\nWe use cookies. " + "x" * 3000
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        saved = (workdir / result.source_file).read_text(encoding="utf-8")
        assert "cookies" in saved.lower()

    def test_piped_json_content(self, fetcher, workdir):
        data = json.dumps({"content": "# Title\n\n" + "x" * 3000, "tool_used": "exa_web_fetch_exa", "actual_url": "https://ar5iv.labs.arxiv.org/html/2503.15223"})
        result = fetcher.save_piped("https://arxiv.org/abs/2503.15223", data, tier=1)
        assert result.tool_used == "exa_web_fetch_exa"
        assert result.actual_url == "https://ar5iv.labs.arxiv.org/html/2503.15223"

    def test_piped_json_with_curly_content_not_double_parsed(self, fetcher, workdir):
        inner_content = "{json: true, data: [1,2,3]}\n" + "x" * 3000
        data = json.dumps({"content": inner_content, "tool_used": "exa_web_fetch_exa"})
        result = fetcher.save_piped("https://example.com/paper", data, tier=2)
        saved = (workdir / result.source_file).read_text(encoding="utf-8")
        assert inner_content in saved

    def test_piped_empty_stdin(self, fetcher, workdir):
        result = fetcher.save_piped("https://example.com/paper", "", tier=2)
        assert result.fetch_failed is True
        assert result.char_count == 0


class TestParsePipedRaw:
    def test_plain_text(self):
        content, tool, url = _parse_piped_raw("hello world", "piped", "https://example.com")
        assert content == "hello world"
        assert tool == "piped"
        assert url == "https://example.com"

    def test_json_content(self):
        raw = json.dumps({"content": "hello", "tool_used": "exa", "actual_url": "https://other.com"})
        content, tool, url = _parse_piped_raw(raw, "piped", "https://example.com")
        assert content == "hello"
        assert tool == "exa"
        assert url == "https://other.com"

    def test_empty_input(self):
        content, tool, url = _parse_piped_raw("", "piped", "https://example.com")
        assert content == ""
        assert tool == "piped"

    def test_invalid_json_starting_with_brace(self):
        content, tool, url = _parse_piped_raw("{not valid json}", "piped", "https://example.com")
        assert content == "{not valid json}"
        assert tool == "piped"


class TestTierInference:
    def test_infer_tier_arxiv(self, fetcher):
        tier = fetcher.infer_tier("https://arxiv.org/abs/2503.15223")
        assert tier == 1

    def test_infer_tier_github(self, fetcher):
        tier = fetcher.infer_tier("https://github.com/user/repo")
        assert tier == 2

    def test_infer_tier_unknown(self, fetcher):
        tier = fetcher.infer_tier("https://unknown-site.example.com/page")
        assert tier is None

    def test_cli_auto_infers_tier(self, fetcher, workdir):
        inferred = fetcher.infer_tier("https://arxiv.org/abs/2503.15223")
        assert inferred == 1


class TestPlaywrightConfig:
    def test_playwright_reads_channel_from_config(self, fetcher, workdir):
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000) as mock_pw:
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        mock_pw.assert_called_once_with(
            "https://medium.com/@user/article",
            timeout=30000,
            channel="chrome",
        )

    def test_playwright_enabled_false_skips_playwright(self, workdir):
        config = {**_SAMPLE_CONFIG, "fetch_defaults": {**_SAMPLE_CONFIG["fetch_defaults"], "playwright_enabled": False}}
        fetcher = Fetcher(workdir, config)
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000) as mock_pw:
                result = fetcher.fetch("https://medium.com/@user/article", tier=3)
        mock_pw.assert_not_called()
        assert result.fetch_failed is True

    def test_no_playwright_overrides_enabled_true(self, fetcher, workdir):
        """--no-playwright flag takes precedence over playwright_enabled=true."""
        with patch("scripts.fetcher._fetch_requests", return_value=None):
            with patch("scripts.fetcher._try_playwright", return_value="x" * 3000) as mock_pw:
                result = fetcher.fetch("https://medium.com/@user/article", tier=3, no_playwright=True)
        mock_pw.assert_not_called()
        assert result.fetch_failed is True


class TestFetchRequestsEncodingRepair:
    def test_gbk_content_redecoded(self):
        from scripts.fetcher import _fetch_requests
        gbk_bytes = "深度学习在自然语言处理中的应用".encode("gbk")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = gbk_bytes.decode("latin-1")
        mock_resp.content = gbk_bytes
        mock_resp.encoding = "latin-1"
        with patch("requests.get", return_value=mock_resp):
            with patch("markdownify.markdownify", side_effect=lambda x, **kw: x):
                result = _fetch_requests("https://36kr.com/p/test")
        assert result is not None
        assert "深度学习" in result

    def test_utf8_content_unchanged(self):
        from scripts.fetcher import _fetch_requests
        utf8_bytes = "深度学习在自然语言处理中的应用".encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = utf8_bytes.decode("utf-8")
        mock_resp.content = utf8_bytes
        mock_resp.encoding = "utf-8"
        with patch("requests.get", return_value=mock_resp):
            with patch("markdownify.markdownify", side_effect=lambda x, **kw: x):
                result = _fetch_requests("https://example.com/paper")
        assert result is not None
        assert "深度学习" in result


class TestDetectContentQuality:
    def test_empty_content_rejected(self):
        ok, reason = _detect_content_quality("")
        assert ok is False
        assert "empty" in reason

    def test_whitespace_only_rejected(self):
        ok, reason = _detect_content_quality("   \n  \n  ")
        assert ok is False

    def test_normal_content_accepted(self):
        content = "# Paper Title\n\n" + "x" * 3000
        ok, reason = _detect_content_quality(content)
        assert ok is True
        assert reason == "accepted"

    def test_short_content_accepted(self):
        ok, reason = _detect_content_quality("# Short\n\nSome text")
        assert ok is True
        assert reason == "accepted"

    def test_dot_padding_rejected(self):
        lines = ["# Title"] + [". . ."] * 10
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is False
        assert "padding" in reason.lower()

    def test_ellipsis_padding_rejected(self):
        lines = ["# Title"] + ["…"] * 10
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is False

    def test_english_template_sentences_rejected(self):
        lines = ["# Title"]
        for _ in range(10):
            lines.append("This source provides information about DeepSeek architecture and cost analysis.")
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is False
        assert "template" in reason.lower()

    def test_chinese_template_sentences_rejected(self):
        lines = ["# 标题"]
        for _ in range(10):
            lines.append("本来源提供了关于DeepSeek架构和成本分析的信息。")
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is False
        assert "template" in reason.lower()

    def test_chinese_alt_template_rejected(self):
        lines = ["# 标题"]
        for _ in range(10):
            lines.append("该来源提供了关于DeepSeek技术架构的详情。")
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is False

    def test_mixed_content_with_minor_padding_passes(self):
        content = "# Paper Title\n\nReal content here. " * 50 + "\n. . .\n"
        ok, reason = _detect_content_quality(content)
        assert ok is True

    def test_below_padding_threshold_passes(self):
        lines = ["# Title", "Real content line.", ". . .", "More real content."]
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is True

    def test_below_template_threshold_passes(self):
        lines = [
            "# Title",
            "This source provides information about the topic.",
            "Real analysis paragraph with substantive content.",
            "Another real paragraph with detailed findings.",
        ]
        content = "\n".join(lines)
        ok, reason = _detect_content_quality(content)
        assert ok is True


class TestPipedContentQualityGate:
    def test_piped_dot_padding_rejected(self, fetcher, workdir):
        lines = ["# Title"] + [". . ."] * 10
        content = "\n".join(lines)
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is True
        assert result.source_file is None

    def test_piped_template_english_rejected(self, fetcher, workdir):
        lines = ["# Title"]
        for _ in range(10):
            lines.append("This source provides information about the research topic.")
        content = "\n".join(lines)
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is True
        assert result.source_file is None

    def test_piped_template_chinese_rejected(self, fetcher, workdir):
        lines = ["# 标题"]
        for _ in range(10):
            lines.append("本来源提供了关于DeepSeek技术架构的信息。")
        content = "\n".join(lines)
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is True

    def test_piped_legitimate_content_passes(self, fetcher, workdir):
        content = "# Paper Title\n\n" + "x" * 3000
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is False
        assert (workdir / result.source_file).exists()

    def test_piped_short_but_real_content_passes(self, fetcher, workdir):
        content = "# Title\n\nSome real content about the topic."
        result = fetcher.save_piped("https://example.com/paper", content, tier=2)
        assert result.fetch_failed is False
        assert result.content_insufficient is True
