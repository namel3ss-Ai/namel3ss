from __future__ import annotations

from dataclasses import dataclass
from typing import List

from namel3ss.ast.base import Node
from namel3ss.ast.pages import PageItem


@dataclass
class UIPackFragment(Node):
    name: str
    items: List[PageItem]


@dataclass
class UIPackDecl(Node):
    name: str
    version: str
    fragments: List[UIPackFragment]


__all__ = ["UIPackDecl", "UIPackFragment"]
