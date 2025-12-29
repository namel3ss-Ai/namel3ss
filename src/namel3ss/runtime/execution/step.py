from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionStep:
    id: str
    kind: str
    what: str
    because: str | None = None
    data: dict = field(default_factory=dict)
    line: int | None = None
    column: int | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "what": self.what,
            "because": self.because,
            "data": dict(self.data or {}),
            "line": self.line,
            "column": self.column,
        }


__all__ = ["ExecutionStep"]
