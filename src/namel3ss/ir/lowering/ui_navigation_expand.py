from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.ui_navigation import NavigationItem, NavigationSidebar


def lower_navigation_sidebar(
    sidebar: ast.NavigationSidebar | None,
    page_names: set[str],
    *,
    owner: str,
) -> NavigationSidebar | None:
    if sidebar is None:
        return None
    if not isinstance(sidebar, ast.NavigationSidebar):
        raise Namel3ssError(
            'Navigation sidebar must use: nav_sidebar: item "<label>" goes_to "<PageName>".',
            line=getattr(sidebar, "line", None),
            column=getattr(sidebar, "column", None),
        )
    lowered_items: list[NavigationItem] = []
    seen_labels: set[str] = set()
    for entry in sidebar.items:
        if not isinstance(entry, ast.NavigationItem):
            raise Namel3ssError(
                'Navigation items must use: item "<label>" goes_to "<PageName>".',
                line=getattr(entry, "line", None),
                column=getattr(entry, "column", None),
            )
        if entry.page_name not in page_names:
            raise Namel3ssError(
                f"{owner} navigation references unknown page '{entry.page_name}'.",
                line=entry.line,
                column=entry.column,
            )
        if entry.label in seen_labels:
            raise Namel3ssError(
                f"{owner} navigation item label '{entry.label}' is duplicated.",
                line=entry.line,
                column=entry.column,
            )
        seen_labels.add(entry.label)
        lowered_items.append(
            NavigationItem(
                label=entry.label,
                page_name=entry.page_name,
                line=entry.line,
                column=entry.column,
            )
        )
    return NavigationSidebar(items=lowered_items, line=sidebar.line, column=sidebar.column)


__all__ = ["lower_navigation_sidebar"]
