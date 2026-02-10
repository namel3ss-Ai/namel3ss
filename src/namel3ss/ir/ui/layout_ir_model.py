from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Union


@dataclass(frozen=True)
class InteractionBindingIR:
    on_click: str | None = None
    keyboard_shortcut: str | None = None
    selected_item: str | None = None


@dataclass(frozen=True)
class ActionIR:
    id: str
    event: str
    node_id: str
    target: str
    line: int | None = None
    column: int | None = None


@dataclass
class LiteralItemIR:
    id: str
    text: str
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class FormIR:
    id: str
    name: str
    wizard: bool = False
    sections: list[str] = field(default_factory=list)
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class TableIR:
    id: str
    name: str
    reorderable_columns: bool = False
    fixed_header: bool = False
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class CardIR:
    id: str
    name: str
    expandable: bool = False
    collapsed: bool = False
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class NavigationTabsIR:
    id: str
    name: str
    dynamic_from_state: str | None = None
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class MediaIR:
    id: str
    name: str
    inline_crop: bool = False
    annotation: bool = False
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class SidebarIR:
    id: str
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class MainIR:
    id: str
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class DrawerIR:
    id: str
    side: str = "right"
    trigger_id: str = ""
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class StickyIR:
    id: str
    position: str = "bottom"
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class ScrollAreaIR:
    id: str
    axis: str = "vertical"
    children: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class TwoPaneIR:
    id: str
    primary: list["LayoutElementIR"] = field(default_factory=list)
    secondary: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


@dataclass
class ThreePaneIR:
    id: str
    left: list["LayoutElementIR"] = field(default_factory=list)
    center: list["LayoutElementIR"] = field(default_factory=list)
    right: list["LayoutElementIR"] = field(default_factory=list)
    bindings: InteractionBindingIR = field(default_factory=InteractionBindingIR)
    line: int | None = None
    column: int | None = None


LayoutElementIR = Union[
    CardIR,
    DrawerIR,
    FormIR,
    LiteralItemIR,
    MainIR,
    MediaIR,
    NavigationTabsIR,
    ScrollAreaIR,
    SidebarIR,
    StickyIR,
    TableIR,
    ThreePaneIR,
    TwoPaneIR,
]


@dataclass
class PageLayoutIR:
    name: str
    state_paths: list[str] = field(default_factory=list)
    elements: list[LayoutElementIR] = field(default_factory=list)
    actions: list[ActionIR] = field(default_factory=list)


def slugify_layout_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "page"


def stable_layout_id(
    page_name: str,
    kind: str,
    *,
    line: int | None,
    column: int | None,
    path: tuple[int, ...],
) -> str:
    slug = slugify_layout_name(page_name)
    encoded_path = ".".join(str(segment) for segment in path)
    payload = f"{slug}|{kind}|{line or 0}|{column or 0}|{encoded_path}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"layout.{slug}.{kind}.{digest}"


__all__ = [
    "ActionIR",
    "CardIR",
    "DrawerIR",
    "FormIR",
    "InteractionBindingIR",
    "LayoutElementIR",
    "LiteralItemIR",
    "MainIR",
    "MediaIR",
    "NavigationTabsIR",
    "PageLayoutIR",
    "ScrollAreaIR",
    "SidebarIR",
    "StickyIR",
    "TableIR",
    "ThreePaneIR",
    "TwoPaneIR",
    "slugify_layout_name",
    "stable_layout_id",
]
