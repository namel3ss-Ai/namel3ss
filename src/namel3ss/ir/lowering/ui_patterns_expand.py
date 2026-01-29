from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.ui_patterns_materialize import (
    materialize_item,
    materialize_tab,
)
from namel3ss.ir.lowering.ui_patterns_values import (
    resolve_pattern_params,
    resolve_visibility,
)
from namel3ss.ui.patterns.model import PatternDefinition


@dataclass(frozen=True)
class PatternContext:
    name: str
    invocation_id: str


def expand_pattern_items(
    items: list[ast.PageItem],
    pattern_index: dict[str, PatternDefinition],
    *,
    page_name: str,
    allow_tabs: bool,
    allow_overlays: bool,
    columns_only: bool,
    flow_names: set[str],
    page_names: set[str],
    record_names: set[str],
    context_module: str | None,
) -> list[ast.PageItem]:
    return _expand_items(
        items,
        pattern_index,
        page_name=page_name,
        allow_tabs=allow_tabs,
        allow_overlays=allow_overlays,
        columns_only=columns_only,
        flow_names=flow_names,
        page_names=page_names,
        record_names=record_names,
        context_module=context_module,
        page_path_prefix=[],
        pattern_context=None,
        pattern_path_prefix=None,
        base_origin=None,
        param_values=None,
        param_defs=None,
        stack=[],
    )


def _expand_items(
    items: list[ast.PageItem],
    pattern_index: dict[str, PatternDefinition],
    *,
    page_name: str,
    allow_tabs: bool,
    allow_overlays: bool,
    columns_only: bool,
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
) -> list[ast.PageItem]:
    expanded: list[ast.PageItem] = []
    for idx, item in enumerate(items):
        item_page_path = page_path_prefix + [idx]
        item_pattern_path = (pattern_path_prefix or []) + [idx] if pattern_context else None
        invocation_path = item_page_path
        if pattern_context is not None and item_pattern_path is not None:
            invocation_path = page_path_prefix + item_pattern_path
        if isinstance(item, ast.UsePatternItem):
            expanded.extend(
                _expand_use_pattern(
                    item,
                    pattern_index,
                    page_name=page_name,
                    allow_tabs=allow_tabs,
                    allow_overlays=allow_overlays,
                    columns_only=columns_only,
                    flow_names=flow_names,
                    page_names=page_names,
                    record_names=record_names,
                    context_module=context_module,
                    invocation_path=invocation_path,
                    param_values=param_values,
                    param_defs=param_defs,
                    base_origin=base_origin,
                    stack=stack,
                )
            )
            continue
        working = materialize_item(
            item,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            param_values=param_values,
            param_defs=param_defs,
        )
        if working is None:
            continue
        if columns_only and not isinstance(working, ast.ColumnItem):
            raise Namel3ssError("Rows may only contain columns", line=working.line, column=working.column)
        if isinstance(working, ast.TabsItem) and not allow_tabs:
            raise Namel3ssError("Tabs may only appear at the page root", line=working.line, column=working.column)
        if isinstance(working, (ast.ModalItem, ast.DrawerItem)) and not allow_overlays:
            raise Namel3ssError("Overlays may only appear at the page root", line=working.line, column=working.column)
        working = _expand_item_children(
            working,
            pattern_index,
            page_name=page_name,
            allow_tabs=allow_tabs,
            allow_overlays=allow_overlays,
            flow_names=flow_names,
            page_names=page_names,
            record_names=record_names,
            context_module=context_module,
            page_path_prefix=item_page_path,
            pattern_context=pattern_context,
            pattern_path_prefix=item_pattern_path,
            base_origin=base_origin,
            param_values=param_values,
            param_defs=param_defs,
            stack=stack,
        )
        if pattern_context and item_pattern_path is not None:
            working = _attach_pattern_origin(working, pattern_context, item_pattern_path, base_origin)
        expanded.append(working)
    return expanded


def _expand_use_pattern(
    item: ast.UsePatternItem,
    pattern_index: dict[str, PatternDefinition],
    *,
    page_name: str,
    allow_tabs: bool,
    allow_overlays: bool,
    columns_only: bool,
    flow_names: set[str],
    page_names: set[str],
    record_names: set[str],
    context_module: str | None,
    invocation_path: list[int],
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    base_origin: dict | None,
    stack: list[str],
) -> list[ast.PageItem]:
    pattern = pattern_index.get(item.pattern_name)
    if pattern is None:
        raise Namel3ssError(
            f"Unknown pattern '{item.pattern_name}' on page '{page_name}'",
            line=item.line,
            column=item.column,
        )
    if pattern.name in stack:
        raise Namel3ssError(
            f"Pattern expansion cycle detected: {' -> '.join(stack + [pattern.name])}",
            line=item.line,
            column=item.column,
        )
    invocation_id = _format_invocation_id(page_name, invocation_path)
    values = resolve_pattern_params(
        pattern,
        item.arguments,
        param_values=param_values,
        param_defs=param_defs,
        line=item.line,
        column=item.column,
    )
    visibility = resolve_visibility(item.visibility, param_values=param_values, param_defs=param_defs)
    base_items = pattern.builder(values, invocation_path) if pattern.builder else list(pattern.items or [])
    next_origin = _merge_origin(base_origin, getattr(item, "origin", None))
    expanded = _expand_items(
        base_items,
        pattern_index,
        page_name=page_name,
        allow_tabs=allow_tabs,
        allow_overlays=allow_overlays,
        columns_only=columns_only,
        flow_names=flow_names,
        page_names=page_names,
        record_names=record_names,
        context_module=context_module,
        page_path_prefix=invocation_path,
        pattern_context=PatternContext(pattern.name, invocation_id),
        pattern_path_prefix=[],
        base_origin=next_origin,
        param_values=values,
        param_defs={param.name: param for param in pattern.parameters},
        stack=stack + [pattern.name],
    )
    if visibility is not None:
        _ensure_no_top_level_visibility(expanded, item)
        expanded = [_apply_visibility(entry, visibility) for entry in expanded]
    return expanded


def _expand_item_children(
    item: ast.PageItem,
    pattern_index: dict[str, PatternDefinition],
    *,
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
    if isinstance(item, ast.SectionItem):
        item.children = _expand_items(
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
        item.children = _expand_items(
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
        item.children = _expand_items(
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
        item.children = _expand_items(
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
    if isinstance(item, ast.ColumnItem):
        item.children = _expand_items(
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
            tab_item.children = _expand_items(
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
    if isinstance(item, (ast.ModalItem, ast.DrawerItem, ast.ComposeItem, ast.ChatItem)):
        item.children = _expand_items(
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


def _merge_origin(base: dict | None, override: dict | None) -> dict | None:
    if base is None and override is None:
        return None
    merged: dict = {}
    if base:
        merged.update(base)
    if override:
        merged.update(override)
    return merged


def _attach_pattern_origin(
    item: ast.PageItem,
    context: PatternContext,
    element_path: list[int],
    base_origin: dict | None,
) -> ast.PageItem:
    existing = getattr(item, "origin", None)
    origin = _merge_origin(base_origin, existing) or {}
    origin.update(
        {
            "pattern": context.name,
            "invocation": context.invocation_id,
            "element": _format_element_path(element_path),
        }
    )
    setattr(item, "origin", origin)
    return item


def _ensure_no_top_level_visibility(items: list[ast.PageItem], source: ast.PageItem) -> None:
    for entry in items:
        if getattr(entry, "visibility", None) is not None:
            raise Namel3ssError(
                "Pattern visibility cannot be combined with item visibility",
                line=source.line,
                column=source.column,
            )


def _apply_visibility(item: ast.PageItem, visibility: ast.StatePath) -> ast.PageItem:
    item.visibility = visibility
    return item


def _format_invocation_id(page_name: str, path: list[int]) -> str:
    path_text = ".".join(str(entry) for entry in path)
    return f"page:{page_name}:pattern:{path_text}" if path_text else f"page:{page_name}:pattern"


def _format_element_path(path: list[int]) -> str:
    return ".".join(str(entry) for entry in path)


__all__ = ["PatternContext", "expand_pattern_items"]
