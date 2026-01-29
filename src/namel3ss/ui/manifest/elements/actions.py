from __future__ import annotations

from typing import Dict, List
from pathlib import Path

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode, validate_media_reference
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.actions import _allocate_action_id, _button_action_id, _link_action_id
from namel3ss.ui.manifest.canonical import _element_id, _slugify
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest_card import _build_card_actions, _build_card_stat
from namel3ss.ui.manifest_overlay import _drawer_id, _modal_id
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from .base import _base_element


def build_compose_item(
    item: ir.ComposeItem,
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
    element_id = _element_id(page_slug, "compose", path)
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
    element = {"type": "compose", "name": item.name, "slug": _slugify(item.name), "children": children, **base}
    return _attach_origin(element, item), actions


def build_title_item(
    item: ir.TitleItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "title", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    return (
        _attach_origin(
            {"type": "title", "value": item.value, **base},
            item,
        ),
        {},
    )


def build_text_item(
    item: ir.TextItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "text", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    return (
        _attach_origin(
            {"type": "text", "value": item.value, **base},
            item,
        ),
        {},
    )


def build_button_item(
    item: ir.ButtonItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "button_item", path)
    base_action_id = _button_action_id(page_slug, item.label)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    action_entry = {"id": action_id, "type": "call_flow", "flow": item.flow_name}
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "button",
        "label": item.label,
        "id": action_id,
        "action_id": action_id,
        "action": {"type": "call_flow", "flow": item.flow_name},
        **base,
    }
    return _attach_origin(element, item), {action_id: action_entry}


def build_link_item(
    item: ir.LinkItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "link_item", path)
    base_action_id = _link_action_id(page_slug, item.label)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    action_entry = {"id": action_id, "type": "open_page", "target": item.page_name}
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "link",
        "label": item.label,
        "target": item.page_name,
        "id": action_id,
        "action_id": action_id,
        "action": {"type": "open_page", "target": item.page_name},
        **base,
    }
    return _attach_origin(element, item), {action_id: action_entry}


def build_section_item(
    item: ir.SectionItem,
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
    base = _base_element(_element_id(page_slug, "section", path), page_name, page_slug, index, item)
    element = {"type": "section", "label": item.label or "", "children": children, **base}
    return _attach_origin(element, item), actions


def build_card_group_item(
    item: ir.CardGroupItem,
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
    base = _base_element(_element_id(page_slug, "card_group", path), page_name, page_slug, index, item)
    element = {"type": "card_group", "children": children, **base}
    return _attach_origin(element, item), actions


def build_card_item(
    item: ir.CardItem,
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
    element_id = _element_id(page_slug, "card", path)
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
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {"type": "card", "label": item.label or "", "children": children, **base}
    if item.stat is not None:
        element["stat"] = _build_card_stat(item.stat, identity, state_ctx, mode, warnings)
    if item.actions:
        action_entries, action_map = _build_card_actions(element_id, page_slug, item.actions)
        element["actions"] = action_entries
        actions.update(action_map)
    return _attach_origin(element, item), actions


def build_row_item(
    item: ir.RowItem,
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
    base = _base_element(_element_id(page_slug, "row", path), page_name, page_slug, index, item)
    element = {"type": "row", "children": children, **base}
    return _attach_origin(element, item), actions


def build_column_item(
    item: ir.ColumnItem,
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
    base = _base_element(_element_id(page_slug, "column", path), page_name, page_slug, index, item)
    element = {"type": "column", "children": children, **base}
    return _attach_origin(element, item), actions


def build_divider_item(
    item: ir.DividerItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    base = _base_element(_element_id(page_slug, "divider", path), page_name, page_slug, index, item)
    element = {"type": "divider", **base}
    return _attach_origin(element, item), {}


def build_modal_item(
    item: ir.ModalItem,
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
    element_id = _element_id(page_slug, "modal", path)
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
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "modal",
        "id": _modal_id(page_slug, item.label),
        "label": item.label,
        "open": False,
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_drawer_item(
    item: ir.DrawerItem,
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
    element_id = _element_id(page_slug, "drawer", path)
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
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "drawer",
        "id": _drawer_id(page_slug, item.label),
        "label": item.label,
        "open": False,
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_image_item(
    item: ir.ImageItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    media_registry: dict[str, Path],
    media_mode: MediaValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    base = _base_element(_element_id(page_slug, "image", path), page_name, page_slug, index, item)
    intent = validate_media_reference(
        item.src,
        registry=media_registry,
        role=item.role,
        mode=media_mode,
        warnings=warnings,
        line=item.line,
        column=item.column,
    )
    element = {"type": "image", **intent.as_dict(), **base}
    return _attach_origin(element, item), {}


__all__ = [
    "build_button_item",
    "build_link_item",
    "build_card_group_item",
    "build_card_item",
    "build_column_item",
    "build_compose_item",
    "build_divider_item",
    "build_drawer_item",
    "build_image_item",
    "build_modal_item",
    "build_row_item",
    "build_section_item",
    "build_text_item",
    "build_title_item",
]
