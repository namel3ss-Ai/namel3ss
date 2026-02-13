from __future__ import annotations

from typing import Protocol, Sequence


class PageContract(Protocol):
    name: str
    items: Sequence[object]
    requires: object | None


class ProgramContract(Protocol):
    pages: Sequence[object]
    flows: Sequence[object]


__all__ = ["PageContract", "ProgramContract"]
