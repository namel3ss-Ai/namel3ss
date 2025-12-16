from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Finding:
    code: str
    message: str
    line: Optional[int]
    column: Optional[int]
    severity: str = "error"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
        }
