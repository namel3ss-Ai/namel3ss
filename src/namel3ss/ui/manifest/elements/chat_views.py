from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.runtime.storage.base import Storage
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest_chat import _chat_item_kind, _chat_item_to_manifest
from namel3ss.validation import ValidationMode

from .base import _base_element


def build_chat_item(
    item: ir.ChatItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict,
    media_mode,
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
    element_id = _element_id(page_slug, "chat", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {"type": "chat", "children": children, **base}
    return _attach_origin(element, item), actions


def build_chat_child_item(
    item: ir.PageItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]] | None:
    chat_kind = _chat_item_kind(item)
    if not chat_kind:
        return None
    element_id = _element_id(page_slug, chat_kind, path)
    result = _chat_item_to_manifest(
        item,
        element_id=element_id,
        page_name=page_name,
        page_slug=page_slug,
        index=path[-1] if path else 0,
        state_ctx=state_ctx,
        mode=mode,
        warnings=warnings,
    )
    if result is None:
        return None
    element, actions = result
    return _attach_origin(element, item), actions


__all__ = ["build_chat_item", "build_chat_child_item"]
