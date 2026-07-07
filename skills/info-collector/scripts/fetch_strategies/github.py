from __future__ import annotations
import re


class GithubStrategy:
    _REPO_RE = re.compile(r"github\.com/([^/]+/[^/]+)(?:/.*)?$")
    _REPO_WITH_PATH_RE = re.compile(r"github\.com/([^/]+/[^/]+)/(.+)")

    def rewrite_url(self, url: str) -> str:
        m = self._REPO_WITH_PATH_RE.search(url)
        if m:
            return url
        m = self._REPO_RE.search(url)
        if m:
            repo = m.group(1)
            return f"https://github.com/{repo}/blob/main/README.md"
        return url

    def tools(self) -> list[str]:
        return ["webfetch", "exa_web_fetch_exa"]

    def retries(self, tier: int) -> int:
        return 2 if tier <= 2 else 1
