from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.actions import _allocate_action_id, _ingestion_action_id, _upload_action_id
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin

from .base import _base_element


def build_upload_item(
    item: ir.UploadItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "upload", path)
    base_action_id = _upload_action_id(page_slug, item.name)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    ingestion_base = _ingestion_action_id(page_slug, item.name)
    ingestion_action_id = _allocate_action_id(ingestion_base, element_id, taken_actions)
    base = _base_element(element_id, page_name, page_slug, index, item)
    multiple = bool(item.multiple)
    element = {
        "type": "upload",
        "name": item.name,
        "accept": list(item.accept or []),
        "multiple": multiple,
        "id": action_id,
        "action_id": action_id,
        **base,
    }
    action_entry = {
        "id": action_id,
        "type": "upload_select",
        "name": item.name,
        "multiple": multiple,
    }
    ingestion_entry = {
        "id": ingestion_action_id,
        "type": "ingestion_run",
    }
    return _attach_origin(element, item), {action_id: action_entry, ingestion_action_id: ingestion_entry}


__all__ = ["build_upload_item"]
