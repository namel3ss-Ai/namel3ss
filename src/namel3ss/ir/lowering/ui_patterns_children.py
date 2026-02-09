from __future__ import annotations

from collections.abc import Callable

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.ui_patterns_materialize import materialize_tab
from namel3ss.ir.lowering.ui_patterns_origin import PatternContext, _attach_pattern_origin
from namel3ss.ui.patterns.model import PatternDefinition

ExpandItems = Callable[
    [
        list[ast.PageItem],
        dict[str, PatternDefinition],
        str,
        bool,
        bool,
        bool,
        set[str],
        set[str],
        set[str],
        str | None,
        list[int],
        PatternContext | None,
        list[int] | None,
        dict | None,
        dict[str, object] | None,
        dict[str, ast.PatternParam] | None,
        list[str],
    ],
    list[ast.PageItem],
]


def expand_item_children(
    item: ast.PageItem,
    pattern_index: dict[str, PatternDefinition],
    *,
    expand_items: ExpandItems,
    page_name: str,
    allow_tabs: bool,
    allow_overlays: bool,
    flow_names: set[str],
    page_names: set[str],
    record_names: set[str],
    context_module: str | None,
    page_path_prefix: list[int],
    pattern_context: PatternContext | None,
    pattern_path_prefix: list[int] | None,
    base_origin: dict | None,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    stack: list[str],
) -> ast.PageItem:
    if isinstance(item, ast.ConditionalBlock):
        item.then_children = expand_items(
            item.then_children,
            pattern_index,
            page_name=page_name,
            allow_tabs=allow_tabs,
            allow_overlays=allow_overlays,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        if item.else_children is not None:
            item.else_children = expand_items(
                item.else_children,
                pattern_index,
                page_name=page_name,
                allow_tabs=allow_tabs,
                allow_overlays=allow_overlays,
                columns_only=False,
                flow_names=flow_names,
                page_names=page_names,
                record_names=record_names,
                context_module=context_module,
                page_path_prefix=page_path_prefix,
                pattern_context=pattern_context,
                pattern_path_prefix=pattern_path_prefix,
                base_origin=base_origin,
                param_values=param_values,
                param_defs=param_defs,
                stack=stack,
            )
        return item
    if isinstance(item, ast.SidebarLayout):
        item.sidebar = expand_items(
            item.sidebar,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        item.main = expand_items(
            item.main,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.SectionItem):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.CardGroupItem):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.CardItem):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.RowItem):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=True,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.LayoutStack):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.LayoutRow):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.LayoutColumn):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.LayoutGrid):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.LayoutSticky):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.ColumnItem):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, ast.TabsItem):
        tabs: list[ast.TabItem] = []
        for idx, tab in enumerate(item.tabs):
            tab_item = materialize_tab(tab, param_values=param_values, param_defs=param_defs)
            if tab_item is None:
                continue
            tab_item.children = expand_items(
                tab_item.children,
                pattern_index,
                page_name=page_name,
                allow_tabs=False,
                allow_overlays=False,
                columns_only=False,
                flow_names=flow_names,
                page_names=page_names,
                record_names=record_names,
                context_module=context_module,
                page_path_prefix=page_path_prefix + [idx],
                pattern_context=pattern_context,
                pattern_path_prefix=(pattern_path_prefix or []) + [idx] if pattern_context else None,
                base_origin=base_origin,
                param_values=param_values,
                param_defs=param_defs,
                stack=stack,
            )
            if pattern_context and pattern_path_prefix is not None:
                tab_item = _attach_pattern_origin(
                    tab_item,
                    pattern_context,
                    (pattern_path_prefix or []) + [idx],
                    base_origin,
                )
            tabs.append(tab_item)
        item.tabs = tabs
        if item.default and item.default not in {tab.label for tab in tabs}:
            item.default = None
        return item
    if isinstance(item, ast.LayoutDrawer):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    if isinstance(item, (ast.ModalItem, ast.DrawerItem, ast.ComposeItem, ast.ChatItem)):
        item.children = expand_items(
            item.children,
            pattern_index,
            page_name=page_name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=page_path_prefix,
            pattern_context=pattern_context,
            pattern_path_prefix=pattern_path_prefix,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        return item
    return item


__all__ = ["expand_item_children"]
