from __future__ import annotations

from typing import Dict

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import resolve_name
from namel3ss.module_loader.types import ModuleExports


def resolve_page_item(
    item: ast.PageItem,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    if isinstance(item, ast.FormItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.TableItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        if item.row_actions:
            for action in item.row_actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        return
    if isinstance(item, ast.ListItem):
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        if item.actions:
            for action in item.actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        return
    if isinstance(item, ast.ChartItem) and item.record_name:
        item.record_name = resolve_name(
            item.record_name,
            kind="record",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.UseUIPackItem):
        item.pack_name = resolve_name(
            item.pack_name,
            kind="ui_pack",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.ButtonItem):
        item.flow_name = resolve_name(
            item.flow_name,
            kind="flow",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=item.line,
            column=item.column,
        )
        return
    if isinstance(item, ast.ChatItem):
        for child in item.children:
            if isinstance(child, ast.ChatComposerItem):
                child.flow_name = resolve_name(
                    child.flow_name,
                    kind="flow",
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                    line=child.line,
                    column=child.column,
                )
        return
    if isinstance(item, ast.CardItem):
        if item.actions:
            for action in item.actions:
                if action.kind == "call_flow" and action.flow_name:
                    action.flow_name = resolve_name(
                        action.flow_name,
                        kind="flow",
                        module_name=module_name,
                        alias_map=alias_map,
                        local_defs=local_defs,
                        exports_map=exports_map,
                        context_label=context_label,
                        line=action.line,
                        column=action.column,
                    )
        for child in item.children:
            resolve_page_item(
                child,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(item, (ast.ModalItem, ast.DrawerItem)):
        for child in item.children:
            resolve_page_item(
                child,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        return
    if isinstance(item, ast.TabsItem):
        for tab in item.tabs:
            for child in tab.children:
                resolve_page_item(
                    child,
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                )
        return
    if isinstance(item, (ast.SectionItem, ast.CardGroupItem, ast.RowItem, ast.ColumnItem)):
        for child in item.children:
            resolve_page_item(
                child,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )


__all__ = ["resolve_page_item"]
