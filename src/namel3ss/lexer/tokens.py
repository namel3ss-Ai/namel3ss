from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from namel3ss.lang.keywords import KEYWORDS

ESCAPED_IDENTIFIER = "IDENT_ESCAPED"


@dataclass(frozen=True)
class Token:
    type: str
    value: Optional[object]
    line: int
    column: int
    escaped: bool = False

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.type}, {self.value}, {self.line}:{self.column})"
