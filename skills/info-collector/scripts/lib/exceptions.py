from __future__ import annotations


class InfoCollectorError(Exception):
    """Base exception for info-collector."""

    pass


class GateFailureError(InfoCollectorError):
    """Gate check failed with BLOCKER-level issues."""

    def __init__(self, phase: str, blockers: list[str]):
        self.phase = phase
        self.blockers = blockers
        super().__init__(f"Gate '{phase}' blocked: {'; '.join(blockers)}")


class ArtifactError(InfoCollectorError):
    """Artifact file missing, unreadable, or schema-invalid."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Artifact error at {path}: {reason}")
