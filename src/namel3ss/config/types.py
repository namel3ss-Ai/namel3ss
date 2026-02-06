from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigSource:
    kind: str
    path: str | None = None


__all__ = ["ConfigSource"]
