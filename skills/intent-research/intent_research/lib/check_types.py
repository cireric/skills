from __future__ import annotations


class CheckResult:
    __slots__ = ("name", "level", "message")

    _LEVEL_PREFIX = {"PASS": "  [PASS]", "WARN": "  [ADVISORY]", "BLOCKER": "  [BLOCKER]"}

    def __init__(self, name: str, level: str, message: str = "") -> None:
        self.name = name
        self.level = level
        self.message = message

    @property
    def prefix(self) -> str:
        return self._LEVEL_PREFIX.get(self.level, "  [???]")

    def __repr__(self) -> str:
        return f"CheckResult({self.name!r}, {self.level!r}, {self.message!r})"
