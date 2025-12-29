from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.lang.keywords import KEYWORDS


@dataclass(frozen=True)
class Token:
    type: str
    value: Optional[object]
    line: int
    column: int

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.type}, {self.value}, {self.line}:{self.column})"
