from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class ResponsiveBreakpoint(Node):
    name: str
    width: int


@dataclass
class ResponsiveDecl(Node):
    breakpoints: list[ResponsiveBreakpoint]


__all__ = ["ResponsiveBreakpoint", "ResponsiveDecl"]
