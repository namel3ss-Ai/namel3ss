from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolsWithPack:
    tools_called: int
    allowed: list[dict]
    blocked: list[dict]
    errors: list[dict]
    none_used: bool
    notes: list[str]

    def as_dict(self) -> dict:
        return {
            "tools_called": self.tools_called,
            "allowed": list(self.allowed),
            "blocked": list(self.blocked),
            "errors": list(self.errors),
            "none_used": self.none_used,
            "notes": list(self.notes),
        }


__all__ = ["ToolsWithPack"]
