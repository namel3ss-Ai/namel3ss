from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import Page, TabsItem
from namel3ss.ir.model.ui_layout import (
    ConditionalBlock,
    LayoutColumn,
    LayoutDrawer,
    LayoutGrid,
    LayoutRow,
    LayoutStack,
    LayoutSticky,
    SidebarLayout,
)


@dataclass(frozen=True)
class _LayoutUsage:
    line: int | None
    column: int | None


def validate_ui_layout(pages: list[Page], capabilities: tuple[str, ...]) -> None:
    usage: _LayoutUsage | None = None
    for page in pages:
        usage = _walk_page_items(page.items, usage, in_sidebar=False, in_main=False, in_drawer=False, at_top_level=True)
    if usage is not None and "ui_layout" not in set(capabilities or ()):
        raise Namel3ssError(
            "UI layout requires capability ui_layout. Add 'ui_layout' to the capabilities list.",
            line=usage.line,
            column=usage.column,
        )


def _walk_page_items(
    items: list,
    usage: _LayoutUsage | None,
    *,
    in_sidebar: bool,
    in_main: bool,
    in_drawer: bool,
    at_top_level: bool,
) -> _LayoutUsage | None:
    for item in items:
        usage = _track_usage(item, usage)
        if isinstance(item, TabsItem):
            for tab in item.tabs:
                usage = _track_usage(tab, usage)
                usage = _walk_page_items(
                    tab.children,
                    usage,
                    in_sidebar=in_sidebar,
                    in_main=in_main,
                    in_drawer=in_drawer,
                    at_top_level=at_top_level,
                )
            continue
        if isinstance(item, ConditionalBlock):
            usage = _walk_page_items(
                item.then_children,
                usage,
                in_sidebar=in_sidebar,
                in_main=in_main,
                in_drawer=in_drawer,
                at_top_level=at_top_level,
            )
            if item.else_children:
                usage = _walk_page_items(
                    item.else_children,
                    usage,
                    in_sidebar=in_sidebar,
                    in_main=in_main,
                    in_drawer=in_drawer,
                    at_top_level=at_top_level,
                )
            continue
        if isinstance(item, SidebarLayout):
            if item.sidebar is None or item.main is None:
                raise Namel3ssError(
                    "sidebar_layout must declare both sidebar and main blocks.",
                    line=getattr(item, "line", None),
                    column=getattr(item, "column", None),
                )
            usage = _walk_page_items(
                item.sidebar,
                usage,
                in_sidebar=True,
                in_main=False,
                in_drawer=in_drawer,
                at_top_level=False,
            )
            usage = _walk_page_items(
                item.main,
                usage,
                in_sidebar=False,
                in_main=True,
                in_drawer=in_drawer,
                at_top_level=False,
            )
            continue
        if isinstance(item, LayoutDrawer):
            _validate_layout_drawer(item, in_sidebar=in_sidebar, in_main=in_main, in_drawer=in_drawer, at_top_level=at_top_level)
            usage = _walk_page_items(
                item.children,
                usage,
                in_sidebar=in_sidebar,
                in_main=in_main,
                in_drawer=True,
                at_top_level=False,
            )
            continue
        if isinstance(item, (LayoutStack, LayoutRow, LayoutColumn, LayoutGrid, LayoutSticky)):
            usage = _walk_page_items(
                item.children,
                usage,
                in_sidebar=in_sidebar,
                in_main=in_main,
                in_drawer=in_drawer,
                at_top_level=False,
            )
            continue
        children = getattr(item, "children", None)
        if isinstance(children, list):
            usage = _walk_page_items(
                children,
                usage,
                in_sidebar=in_sidebar,
                in_main=in_main,
                in_drawer=in_drawer,
                at_top_level=False,
            )
    return usage


def _track_usage(item: object, usage: _LayoutUsage | None) -> _LayoutUsage | None:
    if usage is not None:
        return usage
    if _is_rag_ui_origin(item):
        return usage
    if isinstance(item, (LayoutStack, LayoutRow, LayoutColumn, LayoutGrid, SidebarLayout, LayoutDrawer, LayoutSticky, ConditionalBlock)):
        return _LayoutUsage(line=getattr(item, "line", None), column=getattr(item, "column", None))
    show_when = getattr(item, "show_when", None)
    if show_when is not None and not _is_rag_ui_origin(item):
        return _LayoutUsage(line=getattr(item, "line", None), column=getattr(item, "column", None))
    return usage


def _is_rag_ui_origin(item: object) -> bool:
    origin = getattr(item, "origin", None)
    return isinstance(origin, dict) and "rag_ui" in origin


def _validate_layout_drawer(
    item: LayoutDrawer,
    *,
    in_sidebar: bool,
    in_main: bool,
    in_drawer: bool,
    at_top_level: bool,
) -> None:
    if in_drawer:
        raise Namel3ssError(
            "Drawers cannot be nested inside other drawers.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    if in_sidebar:
        raise Namel3ssError(
            "Drawers cannot appear inside sidebar blocks.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    if not at_top_level and not in_main:
        raise Namel3ssError(
            "Drawers may only appear at the top level or inside sidebar_layout main.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )


__all__ = ["validate_ui_layout"]
