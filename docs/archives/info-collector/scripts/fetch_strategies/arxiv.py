from __future__ import annotations
import re


class ArxivStrategy:
    _PDF_RE = re.compile(r"arxiv\.org/pdf/([\d\.]+)")
    _ABS_RE = re.compile(r"arxiv\.org/abs/([\d\.]+)")

    def rewrite_url(self, url: str) -> str:
        for pattern in (self._PDF_RE, self._ABS_RE):
            m = pattern.search(url)
            if m:
                return f"https://ar5iv.labs.arxiv.org/html/{m.group(1)}"
        return url
