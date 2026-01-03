from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorCheck:
    id: str
    status: str
    message: str
    fix: str
    category: str = "project"
    code: str | None = None

    def __post_init__(self) -> None:
        if self.code is None:
            object.__setattr__(self, "code", self.id)


__all__ = ["DoctorCheck"]
