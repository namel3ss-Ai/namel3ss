from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast.base import Node


@dataclass
class NavigationItem(Node):
    label: str
    page_name: str


@dataclass
class NavigationSidebar(Node):
    items: list[NavigationItem]


__all__ = ["NavigationItem", "NavigationSidebar"]
