from __future__ import annotations


class DefaultStrategy:
    def rewrite_url(self, url: str) -> str:
        return url

    def tools(self) -> list[str]:
        return ["webfetch"]

    def retries(self, tier: int) -> int:
        return 2 if tier <= 2 else 1
