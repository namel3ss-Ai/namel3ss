from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextEdit:
    file: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    text: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "start": {"line": self.start_line, "column": self.start_column},
            "end": {"line": self.end_line, "column": self.end_column},
            "text": self.text,
        }


__all__ = ["TextEdit"]
