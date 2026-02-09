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
        if columns_only and not isinstance(item, (ast.ColumnItem, ast.LayoutColumn)):
            raise Namel3ssError("Rows may only contain columns", line=item.line, column=item.column)
        if isinstance(item, ast.TabsItem) and not allow_tabs and not _is_rag_ui_origin(item):
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
    existing_origin = getattr(working, "origin", None)
    if isinstance(working, ast.ConditionalBlock):
        then_children = expand_page_items(
            working.then_children,
            pack_index,
            allow_tabs=allow_tabs,
            allow_overlays=allow_overlays,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        else_children = None
        if working.else_children is not None:
            else_children = expand_page_items(
                working.else_children,
                pack_index,
                allow_tabs=allow_tabs,
                allow_overlays=allow_overlays,
                columns_only=False,
                page_name=page_name,
                stack=stack,
                origin=origin,
            )
        working = replace(working, then_children=then_children, else_children=else_children)
    elif isinstance(working, ast.SidebarLayout):
        sidebar = expand_page_items(
            working.sidebar,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        main = expand_page_items(
            working.main,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page_name,
            stack=stack,
            origin=origin,
        )
        working = replace(working, sidebar=sidebar, main=main)
    elif isinstance(working, ast.SectionItem):
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
        previous = working
        working = replace(working, children=children)
        _copy_dynamic_style_metadata(previous, working)
    elif isinstance(working, ast.LayoutStack):
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
    elif isinstance(working, ast.LayoutRow):
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
    elif isinstance(working, ast.LayoutColumn):
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
    elif isinstance(working, ast.LayoutGrid):
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
    elif isinstance(working, ast.LayoutSticky):
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
            tab_origin = getattr(next_tab, "origin", None)
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
            elif tab_origin is not None:
                setattr(next_tab, "origin", tab_origin)
            tabs.append(next_tab)
        working = replace(working, tabs=tabs)
    elif isinstance(working, ast.LayoutDrawer):
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
    elif existing_origin is not None:
        setattr(working, "origin", existing_origin)
    return working


def _is_rag_ui_origin(item: object) -> bool:
    origin = getattr(item, "origin", None)
    return isinstance(origin, dict) and "rag_ui" in origin


def _copy_dynamic_style_metadata(source: ast.PageItem, target: ast.PageItem) -> None:
    variant = getattr(source, "variant", None)
    if variant is not None:
        setattr(target, "variant", variant)
    style_hooks = getattr(source, "style_hooks", None)
    if style_hooks is not None:
        setattr(target, "style_hooks", copy.deepcopy(style_hooks))


__all__ = ["build_pack_index", "expand_page_items"]
