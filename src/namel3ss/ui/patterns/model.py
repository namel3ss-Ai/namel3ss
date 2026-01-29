from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from namel3ss.ast import nodes as ast

PatternBuilder = Callable[[dict[str, object], List[int]], List[ast.PageItem]]


@dataclass(frozen=True)
class PatternDefinition:
    name: str
    parameters: List[ast.PatternParam]
    items: List[ast.PageItem] | None = None
    builder: PatternBuilder | None = None


__all__ = ["PatternBuilder", "PatternDefinition"]
