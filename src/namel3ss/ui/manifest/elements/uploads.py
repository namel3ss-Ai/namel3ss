from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.actions import (
    _allocate_action_id,
    _ingestion_action_id,
    _upload_action_id,
    _upload_clear_action_id,
)
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext

from .base import _base_element


def build_upload_item(
    item: ir.UploadItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
    state_ctx: StateContext,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "upload", path)
    base_action_id = _upload_action_id(page_slug, item.name)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    clear_base = _upload_clear_action_id(page_slug, item.name)
    clear_action_id = _allocate_action_id(clear_base, element_id, taken_actions)
    ingestion_base = _ingestion_action_id(page_slug, item.name)
    ingestion_action_id = _allocate_action_id(ingestion_base, element_id, taken_actions)
    base = _base_element(element_id, page_name, page_slug, index, item)
    multiple = bool(item.multiple)
    required = bool(getattr(item, "required", False))
    preview = bool(getattr(item, "preview", False))
    label = str(getattr(item, "label", "") or "Upload")
    files = _selected_upload_entries(state_ctx.state, item.name)
    element = {
        "type": "upload",
        "name": item.name,
        "accept": list(item.accept or []),
        "multiple": multiple,
        "required": required,
        "label": label,
        "preview": preview,
        "files": files,
        "id": action_id,
        "action_id": action_id,
        "clear_action_id": clear_action_id,
        **base,
    }
    action_entry = {
        "id": action_id,
        "type": "upload_select",
        "name": item.name,
        "multiple": multiple,
        "required": required,
    }
    clear_entry = {
        "id": clear_action_id,
        "type": "upload_clear",
        "name": item.name,
    }
    ingestion_entry = {
        "id": ingestion_action_id,
        "type": "ingestion_run",
    }
    return _attach_origin(element, item), {
        action_id: action_entry,
        clear_action_id: clear_entry,
        ingestion_action_id: ingestion_entry,
    }


def _selected_upload_entries(state: dict, upload_name: str) -> list[dict]:
    if not isinstance(state, dict):
        return []
    uploads = state.get("uploads")
    if not isinstance(uploads, dict):
        return []
    raw = uploads.get(upload_name)
    return _normalize_upload_entries(raw)


def _normalize_upload_entries(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        if _looks_like_upload_entry(raw):
            return [raw]
        entries: list[dict] = []
        for value in raw.values():
            if isinstance(value, dict):
                entries.append(value)
        return entries
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    return []


def _looks_like_upload_entry(value: dict) -> bool:
    identifier = value.get("id") if isinstance(value.get("id"), str) and value.get("id") else value.get("checksum")
    name = value.get("name")
    return isinstance(identifier, str) and bool(identifier) and isinstance(name, str) and bool(name)


__all__ = ["build_upload_item"]
