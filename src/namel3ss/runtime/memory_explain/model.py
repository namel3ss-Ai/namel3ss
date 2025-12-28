from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Explanation:
    title: str
    lines: List[str] = field(default_factory=list)
    related_ids: Optional[List[str]] = None

    def as_dict(self) -> dict:
        payload = {"title": self.title, "lines": list(self.lines)}
        if self.related_ids:
            payload["related_ids"] = list(self.related_ids)
        return payload


__all__ = ["Explanation"]
