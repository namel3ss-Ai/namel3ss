from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DoctorCheck:
    id: str
    status: str
    message: str
    fix: str


__all__ = ["DoctorCheck"]
