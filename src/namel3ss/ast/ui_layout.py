from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from namel3ss.ast.expressions import Expression
from namel3ss.ast.pages import PageItem

if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.ast.ui_patterns import PatternParamRef


@dataclass
class LayoutStack(PageItem):
    children: list["PageItem"]
    direction: str = "vertical"


@dataclass
class LayoutRow(PageItem):
    children: list["PageItem"]


@dataclass
class LayoutColumn(PageItem):
    children: list["PageItem"]


@dataclass
class LayoutGrid(PageItem):
    columns: int
    children: list["PageItem"]


@dataclass
class SidebarLayout(PageItem):
    sidebar: list["PageItem"]
    main: list["PageItem"]


@dataclass
class LayoutDrawer(PageItem):
    title: str
    children: list["PageItem"]


@dataclass
class LayoutSticky(PageItem):
    position: str  # top | bottom
    children: list["PageItem"]


@dataclass
class ConditionalBlock(PageItem):
    condition: Expression | "PatternParamRef"
    then_children: list["PageItem"]
    else_children: list["PageItem"] | None = None
