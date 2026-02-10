from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class InteractionBindings:
    on_click: str | None = None
    keyboard_shortcut: str | None = None
    selected_item: str | None = None

    def has_bindings(self) -> bool:
        return bool(self.on_click or self.keyboard_shortcut or self.selected_item)


@dataclass(frozen=True)
class StateDefinitionNode:
    path: str
    line: int | None = None
    column: int | None = None


@dataclass
class LiteralItemNode:
    text: str
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class FormNode:
    name: str
    wizard: bool = False
    sections: list[str] = field(default_factory=list)
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class TableNode:
    name: str
    reorderable_columns: bool = False
    fixed_header: bool = False
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class CardNode:
    name: str
    expandable: bool = False
    collapsed: bool = False
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class NavigationTabsNode:
    name: str
    dynamic_from_state: str | None = None
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class MediaNode:
    name: str
    inline_crop: bool = False
    annotation: bool = False
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class SidebarNode:
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class MainNode:
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class DrawerNode:
    side: str = "right"
    trigger_id: str = ""
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class StickyNode:
    position: str = "bottom"
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class ScrollAreaNode:
    axis: str = "vertical"
    children: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class TwoPaneNode:
    primary: list["LayoutNode"] = field(default_factory=list)
    secondary: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


@dataclass
class ThreePaneNode:
    left: list["LayoutNode"] = field(default_factory=list)
    center: list["LayoutNode"] = field(default_factory=list)
    right: list["LayoutNode"] = field(default_factory=list)
    bindings: InteractionBindings = field(default_factory=InteractionBindings)
    line: int | None = None
    column: int | None = None


LayoutNode = Union[
    CardNode,
    DrawerNode,
    FormNode,
    LiteralItemNode,
    MainNode,
    MediaNode,
    NavigationTabsNode,
    ScrollAreaNode,
    SidebarNode,
    StickyNode,
    TableNode,
    ThreePaneNode,
    TwoPaneNode,
]


@dataclass
class PageNode:
    name: str
    states: list[StateDefinitionNode] = field(default_factory=list)
    children: list[LayoutNode] = field(default_factory=list)
    line: int | None = None
    column: int | None = None


__all__ = [
    "CardNode",
    "DrawerNode",
    "FormNode",
    "InteractionBindings",
    "LayoutNode",
    "LiteralItemNode",
    "MainNode",
    "MediaNode",
    "NavigationTabsNode",
    "PageNode",
    "ScrollAreaNode",
    "SidebarNode",
    "StateDefinitionNode",
    "StickyNode",
    "TableNode",
    "ThreePaneNode",
    "TwoPaneNode",
]
