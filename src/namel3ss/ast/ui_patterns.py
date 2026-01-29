from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.pages import PageItem


@dataclass
class PatternParam(Node):
    name: str
    kind: str  # text | number | boolean | record | state
    optional: bool = False
    default: object | None = None


@dataclass
class PatternArgument(Node):
    name: str
    value: object


@dataclass
class PatternParamRef(Node):
    name: str


@dataclass
class UIPatternDecl(Node):
    name: str
    parameters: List[PatternParam]
    items: List[PageItem]


__all__ = ["PatternParam", "PatternArgument", "PatternParamRef", "UIPatternDecl"]
