from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ir.model.base import Node


@dataclass
class BreakpointSpec(Node):
    names: tuple[str, ...]
    values: tuple[int, ...]


@dataclass
class ResponsiveLayout(Node):
    breakpoints: BreakpointSpec
    total_columns: int = 12


__all__ = ["BreakpointSpec", "ResponsiveLayout"]
