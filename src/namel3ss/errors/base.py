"""
Shared error types for Namel3ss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Namel3ssError(Exception):
    """Base error with optional source location."""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __str__(self) -> str:
        location = self._format_location()
        return f"{location}{self.message}" if location else self.message

    def _format_location(self) -> str:
        if self.line is None:
            return ""
        if self.end_line is None or self.end_column is None:
            return f"[line {self.line}, col {self.column or 1}] "
        return (
            f"[line {self.line}, col {self.column or 1} - "
            f"line {self.end_line}, col {self.end_column}] "
        )

