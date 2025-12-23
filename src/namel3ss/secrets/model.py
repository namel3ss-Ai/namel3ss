from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecretRef:
    name: str
    source: str
    target: str
    available: bool


__all__ = ["SecretRef"]
