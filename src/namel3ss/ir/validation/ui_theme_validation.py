from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.capabilities import has_ui_theming_capability
from namel3ss.ir.model.pages import Page, TabsItem, ThemeSettingsPageItem
from namel3ss.ir.model.ui_layout import ConditionalBlock, LayoutDrawer, LayoutGrid, LayoutRow, LayoutStack, LayoutSticky, SidebarLayout


@dataclass(frozen=True)
class _ThemeUsage:
    line: int | None
    column: int | None


def validate_ui_theme(pages: list[Page], capabilities: tuple[str, ...]) -> None:
    usage: _ThemeUsage | None = None
    for page in pages:
        if getattr(page, "theme_tokens", None) is not None and usage is None:
            theme_tokens = getattr(page, "theme_tokens", None)
            usage = _ThemeUsage(line=getattr(theme_tokens, "line", None), column=getattr(theme_tokens, "column", None))
        if getattr(page, "ui_theme_overrides", None) is not None and usage is None:
            overrides = getattr(page, "ui_theme_overrides", None)
            usage = _ThemeUsage(line=getattr(overrides, "line", None), column=getattr(overrides, "column", None))
        usage = _walk_page_items(page.items, usage)
    if usage is not None and not has_ui_theming_capability(capabilities):
        raise Namel3ssError(
            "Token customization requires capability ui_theme or ui.theming. Add one token to the capabilities list.",
            line=usage.line,
            column=usage.column,
        )


def _walk_page_items(items: list, usage: _ThemeUsage | None) -> _ThemeUsage | None:
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


def _track_usage(item: object, usage: _ThemeUsage | None) -> _ThemeUsage | None:
    if usage is not None:
        return usage
    if isinstance(item, ThemeSettingsPageItem):
        return _ThemeUsage(line=getattr(item, "line", None), column=getattr(item, "column", None))
    theme_overrides = getattr(item, "theme_overrides", None)
    if theme_overrides is not None:
        return _ThemeUsage(line=getattr(theme_overrides, "line", None), column=getattr(theme_overrides, "column", None))
    return usage


__all__ = ["validate_ui_theme"]
