from __future__ import annotations

from dataclasses import dataclass

from namel3ss.pkg.versions import Semver


@dataclass(frozen=True)
class PackVersion:
    raw: str
    kind: str
    semver: Semver | None


@dataclass(frozen=True)
class VersionComparison:
    status: str
    reason: str | None


__all__ = ["PackVersion", "VersionComparison"]
