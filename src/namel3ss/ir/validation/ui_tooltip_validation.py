from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import Page, SliderItem, TabsItem, TooltipItem
from namel3ss.ir.model.ui_layout import ConditionalBlock, LayoutDrawer, LayoutGrid, LayoutRow, LayoutStack, LayoutSticky, SidebarLayout


_MISSING_CAPABILITY_MESSAGE = (
    "Capability missing: ui.tooltip is required to use 'tooltip' components. "
    "Add 'capability is ui.tooltip' to the manifest."
)


@dataclass(frozen=True)
class _TooltipUsage:
    line: int | None
    column: int | None


def validate_ui_tooltip(pages: list[Page], capabilities: tuple[str, ...]) -> None:
    usage: _TooltipUsage | None = None
    for page in pages:
        usage = _walk_page_items(page.items, usage)
    if usage is not None and "ui.tooltip" not in set(capabilities or ()):
        raise Namel3ssError(_MISSING_CAPABILITY_MESSAGE, line=usage.line, column=usage.column)


def _walk_page_items(items: list, usage: _TooltipUsage | None) -> _TooltipUsage | None:
    _validate_tooltip_anchor_uniqueness(items)
    for item in items:
        if isinstance(item, TooltipItem):
            if not item.text.strip():
                raise Namel3ssError("tooltip text cannot be empty.", line=item.line, column=item.column)
            if usage is None:
                usage = _TooltipUsage(line=item.line, column=item.column)
        if isinstance(item, SliderItem) and isinstance(item.help_text, str) and item.help_text.strip():
            if usage is None:
                usage = _TooltipUsage(line=item.line, column=item.column)
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                _validate_tooltip_anchor_uniqueness(tab.children)
                usage = _walk_page_items(tab.children, usage)
            continue
        if isinstance(item, ConditionalBlock):
            usage = _walk_page_items(item.then_children, usage)
            if item.else_children:
                usage = _walk_page_items(item.else_children, usage)
            continue
        if isinstance(item, SidebarLayout):
            if item.sidebar:
                usage = _walk_page_items(item.sidebar, usage)
            if item.main:
                usage = _walk_page_items(item.main, usage)
            continue
        if isinstance(item, (LayoutStack, LayoutRow, LayoutGrid, LayoutSticky, LayoutDrawer)):
            usage = _walk_page_items(item.children, usage)
            continue
        children = getattr(item, "children", None)
        if isinstance(children, list):
            usage = _walk_page_items(children, usage)
    return usage


def _validate_tooltip_anchor_uniqueness(items: list) -> None:
    anchors: dict[str, tuple[int | None, int | None]] = {}
    for item in items:
        anchor: str | None = None
        if isinstance(item, TooltipItem):
            anchor = item.anchor_label.strip()
            if not anchor:
                continue
        elif isinstance(item, SliderItem):
            if not (isinstance(item.help_text, str) and item.help_text.strip()):
                continue
            anchor = item.label.strip()
            if not anchor:
                continue
        if anchor is None:
            continue
        previous = anchors.get(anchor)
        if previous is None:
            anchors[anchor] = (getattr(item, "line", None), getattr(item, "column", None))
            continue
        raise Namel3ssError(
            f"Duplicate tooltips attached to control '{anchor}'.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )


__all__ = ["validate_ui_tooltip"]

