from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import Page, TabsItem
from namel3ss.ir.model.ui_layout import ConditionalBlock, LayoutDrawer, LayoutGrid, LayoutRow, LayoutStack, LayoutSticky, SidebarLayout


@dataclass(frozen=True)
class _RagUsage:
    line: int | None
    column: int | None


def validate_ui_rag(pages: list[Page], capabilities: tuple[str, ...]) -> None:
    usage: _RagUsage | None = None
    for page in pages:
        usage = _walk_page_items(page.items, usage)
    if usage is not None and "ui_rag" not in set(capabilities or ()):
        raise Namel3ssError(
            "rag_ui requires capability ui_rag. Add 'ui_rag' to the capabilities list.",
            line=usage.line,
            column=usage.column,
        )


def _walk_page_items(items: list, usage: _RagUsage | None) -> _RagUsage | None:
    for item in items:
        usage = _track_usage(item, usage)
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                usage = _track_usage(tab, usage)
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


def _track_usage(item: object, usage: _RagUsage | None) -> _RagUsage | None:
    if usage is not None:
        return usage
    if _is_rag_ui_origin(item):
        return _RagUsage(line=getattr(item, "line", None), column=getattr(item, "column", None))
    return usage


def _is_rag_ui_origin(item: object) -> bool:
    origin = getattr(item, "origin", None)
    return isinstance(origin, dict) and "rag_ui" in origin


__all__ = ["validate_ui_rag"]
