from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import ButtonItem, Page, TabsItem
from namel3ss.ir.model.ui_layout import ConditionalBlock, LayoutDrawer, LayoutGrid, LayoutRow, LayoutStack, LayoutSticky, SidebarLayout
from namel3ss.ir.model.ui_navigation import NavigationSidebar


@dataclass(frozen=True)
class _NavigationUsage:
    line: int | None
    column: int | None


def validate_ui_navigation(
    pages: list[Page],
    navigation: NavigationSidebar | None,
    capabilities: tuple[str, ...],
) -> None:
    usage: _NavigationUsage | None = None
    if navigation is not None:
        usage = _NavigationUsage(line=getattr(navigation, "line", None), column=getattr(navigation, "column", None))
    for page in pages:
        if getattr(page, "ui_navigation", None) is not None and usage is None:
            page_nav = getattr(page, "ui_navigation", None)
            usage = _NavigationUsage(line=getattr(page_nav, "line", None), column=getattr(page_nav, "column", None))
        usage = _walk_page_items(page.items, usage)
    if usage is not None and "ui_navigation" not in set(capabilities or ()):
        raise Namel3ssError(
            "Navigation requires capability ui_navigation. Add 'ui_navigation' to the capabilities list.",
            line=usage.line,
            column=usage.column,
        )


def _walk_page_items(items: list, usage: _NavigationUsage | None) -> _NavigationUsage | None:
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


def _track_usage(item: object, usage: _NavigationUsage | None) -> _NavigationUsage | None:
    if usage is not None:
        return usage
    if isinstance(item, ButtonItem):
        action_kind = str(getattr(item, "action_kind", "call_flow") or "call_flow")
        if action_kind in {"navigate_to", "go_back"}:
            return _NavigationUsage(line=getattr(item, "line", None), column=getattr(item, "column", None))
    return usage


__all__ = ["validate_ui_navigation"]
