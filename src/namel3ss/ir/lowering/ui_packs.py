from __future__ import annotations

from dataclasses import replace
import copy

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def build_pack_index(packs: list[ast.UIPackDecl]) -> dict[str, ast.UIPackDecl]:
    index: dict[str, ast.UIPackDecl] = {}
    for pack in packs:
        if pack.name in index:
            raise Namel3ssError(
                f"ui_pack '{pack.name}' is declared more than once",
                line=pack.line,
                column=pack.column,
            )
        index[pack.name] = pack
    return index


def expand_page_items(
    items: list[ast.PageItem],
    pack_index: dict[str, ast.UIPackDecl],
    *,
    allow_tabs: bool,
    allow_overlays: bool,
    columns_only: bool,
    page_name: str,
    stack: list[str] | None = None,
    origin: dict | None = None,
) -> list[ast.PageItem]:
    stack = stack or []
    expanded: list[ast.PageItem] = []
    for item in items:
        if isinstance(item, ast.UseUIPackItem):
            pack = pack_index.get(item.pack_name)
            if pack is None:
                raise Namel3ssError(
                    f"Unknown ui_pack '{item.pack_name}' on page '{page_name}'",
                    line=item.line,
                    column=item.column,
                )
            fragment = _resolve_fragment(pack, item.fragment_name, page_name, item)
            key = f"{pack.name}:{fragment.name}"
            if key in stack:
                raise Namel3ssError(
                    f"ui_pack expansion cycle detected: {' -> '.join(stack + [key])}",
                    line=item.line,
                    column=item.column,
                )
            fragment_origin = {"pack": pack.name, "version": pack.version, "fragment": fragment.name}
            expanded.extend(
                expand_page_items(
                    fragment.items,
                    pack_index,
                    allow_tabs=allow_tabs,
                    allow_overlays=allow_overlays,
                    columns_only=columns_only,
                    page_name=page_name,
                    stack=stack + [key],
                    origin=fragment_origin,
                )
            )
            continue
        if columns_only and not isinstance(item, ast.ColumnItem):
            raise Namel3ssError("Rows may only contain columns", line=item.line, column=item.column)
        if isinstance(item, ast.TabsItem) and not allow_tabs:
            raise Namel3ssError("Tabs may only appear at the page root", line=item.line, column=item.column)
        if isinstance(item, (ast.ModalItem, ast.DrawerItem)) and not allow_overlays:
            raise Namel3ssError("Overlays may only appear at the page root", line=item.line, column=item.column)
        expanded.append(
            _expand_children(
                item,
                pack_index,
                allow_tabs=allow_tabs,
                allow_overlays=allow_overlays,
                page_name=page_name,
                stack=stack,
                origin=origin,
            )
        )
    return expanded


def _resolve_fragment(
    pack: ast.UIPackDecl,
    fragment_name: str,
    page_name: str,
    item: ast.PageItem,
) -> ast.UIPackFragment:
    for fragment in pack.fragments:
        if fragment.name == fragment_name:
            return fragment
    raise Namel3ssError(
        f"ui_pack '{pack.name}' has no fragment '{fragment_name}' (page '{page_name}')",
        line=item.line,
        column=item.column,
    )


def _expand_children(
    item: ast.PageItem,
    pack_index: dict[str, ast.UIPackDecl],
    *,
    allow_tabs: bool,
    allow_overlays: bool,
    page_name: str,
    stack: list[str],
    origin: dict | None,
) -> ast.PageItem:
    working = copy.deepcopy(item) if origin is not None else item
    if isinstance(working, ast.SectionItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.CardGroupItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.CardItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.RowItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=True,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.ColumnItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.TabsItem):
        tabs: list[ast.TabItem] = []
        for tab in working.tabs:
            next_tab = copy.deepcopy(tab) if origin is not None else tab
            children = expand_page_items(
                next_tab.children,
                pack_index,
                allow_tabs=False,
                allow_overlays=False,
                columns_only=False,
                page_name=page_name,
                stack=stack,
                origin=origin,
            )
            next_tab = replace(next_tab, children=children)
            if origin is not None:
                setattr(next_tab, "origin", origin)
            tabs.append(next_tab)
        working = replace(working, tabs=tabs)
    elif isinstance(working, (ast.ModalItem, ast.DrawerItem)):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    elif isinstance(working, ast.ChatItem):
        children = expand_page_items(
            working.children,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, children=children)
    if origin is not None:
        setattr(working, "origin", origin)
    return working


__all__ = ["build_pack_index", "expand_page_items"]
