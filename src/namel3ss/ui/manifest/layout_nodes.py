from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.visibility import evaluate_visibility
from namel3ss.validation import ValidationMode

from .elements.base import _base_element


def build_layout_stack(
    item: ir.LayoutStack,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_stack", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {
        "type": "layout.stack",
        "id": element_id,
        "direction": item.direction or "vertical",
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_layout_row(
    item: ir.LayoutRow,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_row", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {"type": "layout.row", "id": element_id, "children": children, **base}
    return _attach_origin(element, item), actions


def build_layout_column(
    item: ir.LayoutColumn,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_col", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {"type": "layout.col", "id": element_id, "children": children, **base}
    return _attach_origin(element, item), actions


def build_layout_grid(
    item: ir.LayoutGrid,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_grid", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {
        "type": "layout.grid",
        "id": element_id,
        "columns": int(item.columns),
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_sidebar_layout(
    item: ir.SidebarLayout,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_sidebar", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    sidebar_children, sidebar_actions = build_children(
        item.sidebar,
        record_map,
        page_name,
        page_slug,
        path + [0],
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    main_children, main_actions = build_children(
        item.main,
        record_map,
        page_name,
        page_slug,
        path + [1],
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    actions: Dict[str, dict] = {}
    actions.update(sidebar_actions)
    actions.update(main_actions)
    element = {
        "type": "layout.sidebar",
        "id": element_id,
        "sidebar": sidebar_children,
        "main": main_children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_layout_drawer(
    item: ir.LayoutDrawer,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_drawer", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {
        "type": "layout.drawer",
        "id": element_id,
        "title": item.title,
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_layout_sticky(
    item: ir.LayoutSticky,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "layout_sticky", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    children, actions = build_children(
        item.children,
        record_map,
        page_name,
        page_slug,
        path,
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible,
    )
    element = {
        "type": "layout.sticky",
        "id": element_id,
        "position": item.position,
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_conditional_block(
    item: ir.ConditionalBlock,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "conditional_if", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    condition_result, condition_info = evaluate_visibility(
        item.condition,
        None,
        state_ctx,
        mode,
        warnings,
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )
    then_children, then_actions = build_children(
        item.then_children,
        record_map,
        page_name,
        page_slug,
        path + [0],
        store,
        identity,
        state_ctx,
        mode,
        media_registry,
        media_mode,
        warnings,
        taken_actions,
        parent_visible=parent_visible and condition_result,
    )
    else_children: list[dict] = []
    actions: Dict[str, dict] = {}
    actions.update(then_actions)
    if item.else_children is not None:
        else_children, else_actions = build_children(
            item.else_children,
            record_map,
            page_name,
            page_slug,
            path + [1],
            store,
            identity,
            state_ctx,
            mode,
            media_registry,
            media_mode,
            warnings,
            taken_actions,
            parent_visible=parent_visible and (not condition_result),
        )
        actions.update(else_actions)
    element = {
        "type": "conditional.if",
        "id": element_id,
        "condition": condition_info or {"result": bool(condition_result)},
        "then_children": then_children,
        "else_children": else_children,
        **base,
    }
    return _attach_origin(element, item), actions


__all__ = [
    "build_conditional_block",
    "build_layout_column",
    "build_layout_drawer",
    "build_layout_grid",
    "build_layout_row",
    "build_layout_stack",
    "build_layout_sticky",
    "build_sidebar_layout",
]
