import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from lib.api import CrawlResult, crawl_url, _run_async
from lib.browser import BrowserManager


class TestBrowserManagerConfig:
    def test_custom_user_agent(self):
        from lib.browser import BrowserManager, DEFAULT_USER_AGENT
        manager = BrowserManager(headless=True, user_agent="CustomUA/1.0")
        assert manager._user_agent == "CustomUA/1.0"

    def test_default_user_agent(self):
        from lib.browser import BrowserManager, DEFAULT_USER_AGENT
        manager = BrowserManager(headless=True)
        assert manager._user_agent is None

    def test_custom_browser_channel(self):
        from lib.browser import BrowserManager
        manager = BrowserManager(headless=True, browser_channel="chromium")
        assert manager._browser_channel == "chromium"

    def test_default_browser_channel(self):
        from lib.browser import BrowserManager
        manager = BrowserManager(headless=True)
        assert manager._browser_channel == "chrome"

    def test_custom_viewport(self):
        from lib.browser import BrowserManager
        manager = BrowserManager(headless=True, viewport_width=1280, viewport_height=720)
        assert manager._viewport_width == 1280
        assert manager._viewport_height == 720

    def test_custom_locale(self):
        from lib.browser import BrowserManager
        manager = BrowserManager(headless=True, locale="en-US", timezone="America/New_York")
        assert manager._locale == "en-US"
        assert manager._timezone == "America/New_York"


class TestCrawlResult:
    def test_defaults(self):
        r = CrawlResult(success=True)
        assert r.files == []
        assert r.error is None
        assert r.article_count == 0

    def test_failure(self):
        r = CrawlResult(success=False, error="boom")
        assert r.error == "boom"


class TestCrawlUrlValidation:
    def test_missing_output_dir(self):
        try:
            crawl_url(url="https://example.com", output_dir=None)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "output_dir" in str(e)


class TestRunAsyncErrorHandling:
    def test_returns_crawl_result_on_exception(self):
        async def fail():
            raise RuntimeError("test error")

        result = _run_async(fail())
        assert isinstance(result, CrawlResult)
        assert result.success is False
        assert "test error" in result.error

    def test_returns_crawl_result_on_keyboard_interrupt(self):
        async def interrupt():
            raise KeyboardInterrupt()

        result = _run_async(interrupt())
        assert isinstance(result, CrawlResult)
        assert result.success is False


class TestBrowserManagerImportError:
    def test_missing_playwright(self):
        with patch.dict("sys.modules", {"playwright.async_api": None}):
            from lib.browser import async_playwright as orig
            import lib.browser as bm
            saved = bm.async_playwright
            bm.async_playwright = None
            try:
                manager = BrowserManager()
                assert False, "Should have raised ImportError"
            except ImportError as e:
                assert "playwright" in str(e)
            finally:
                bm.async_playwright = saved
