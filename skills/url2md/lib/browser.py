"""浏览器配置与风控规避."""

from __future__ import annotations

from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment]


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class BrowserManager:
    """浏览器管理器."""

    def __init__(self, headless: bool = True):
        if async_playwright is None:
            raise ImportError("playwright not installed. Run: venv-pip install playwright")
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def create_context(
        self,
        cookies_file: str | None = None,
        user_agent: str | None = None,
    ) -> BrowserContext:
        """创建浏览器上下文."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
        if self._context is None:
            self._context = await self._browser.new_context(
                user_agent=user_agent or DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
        if cookies_file and Path(cookies_file).exists():
            import json

            with open(cookies_file, encoding="utf-8") as f:
                cookies = json.load(f)
                await self._context.add_cookies(cookies)
        return self._context

    async def save_cookies(self, cookies_file: str) -> None:
        """保存 cookies 到文件."""
        if self._context is None:
            return
        cookies = await self._context.cookies()
        path = Path(cookies_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

    async def new_page(self) -> Page:
        """创建新页面."""
        if self._context is None:
            await self.create_context()
        if self._context is None:
            raise RuntimeError("Browser context not available")
        return await self._context.new_page()

    async def close(self) -> None:
        """关闭浏览器."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
