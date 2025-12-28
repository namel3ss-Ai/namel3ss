from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ImpactItem:
    memory_id: str
    short_text: str
    space: str
    phase_id: str
    depth: int
    reason: str
    parent_id: Optional[str] = None


@dataclass(frozen=True)
class ImpactResult:
    title: str
    items: List[ImpactItem] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    path_lines: List[str] = field(default_factory=list)


__all__ = ["ImpactItem", "ImpactResult"]
