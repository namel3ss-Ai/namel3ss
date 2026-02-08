from __future__ import annotations

from typing import Dict

from namel3ss.ui.manifest.actions import (
    _allocate_action_id,
    _ingestion_action_id,
    _upload_action_id,
    _upload_clear_action_id,
)
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO
from namel3ss.ui.manifest.upload_analysis import manifest_has_upload_elements


def public_upload_request(entry: dict) -> dict:
    return {
        "name": str(entry.get("name") or ""),
        "accept": [str(value) for value in entry.get("accept", []) if isinstance(value, str)],
        "multiple": bool(entry.get("multiple", False)),
        "required": bool(entry.get("required", False)),
        "label": str(entry.get("label") or "Upload"),
        "preview": bool(entry.get("preview", False)),
    }


def inject_default_upload_control(
    *,
    pages: list[dict],
    actions: Dict[str, dict],
    taken_actions: set[str],
    state: dict,
    capabilities: tuple[str, ...],
    display_mode: str,
) -> bool:
    if display_mode != DISPLAY_MODE_STUDIO:
        return False
    if "uploads" not in capabilities:
        return False
    if not pages:
        return False
    if manifest_has_upload_elements(pages):
        return False
    first_page = pages[0]
    if not isinstance(first_page, dict):
        return False
    page_slug = str(first_page.get("slug") or first_page.get("name") or "page")
    page_name = str(first_page.get("name") or page_slug)
    upload_name = "default_upload"
    select_action_id = _allocate_action_id(_upload_action_id(page_slug, upload_name), f"page.{page_slug}.upload.injected", taken_actions)
    clear_action_id = _allocate_action_id(_upload_clear_action_id(page_slug, upload_name), f"page.{page_slug}.upload.injected", taken_actions)
    ingestion_action_id = _allocate_action_id(_ingestion_action_id(page_slug, upload_name), f"page.{page_slug}.upload.injected", taken_actions)
    target_elements = first_page.get("elements")
    if not isinstance(target_elements, list):
        layout = first_page.get("layout")
        if not isinstance(layout, dict):
            layout = {}
            first_page["layout"] = layout
        target_elements = layout.get("main")
        if not isinstance(target_elements, list):
            target_elements = []
            layout["main"] = target_elements
    index = len(target_elements)
    target_elements.append(
        {
            "type": "upload",
            "name": upload_name,
            "accept": [],
            "multiple": False,
            "required": False,
            "label": "Upload",
            "preview": False,
            "files": _upload_files_for_name(state, upload_name),
            "id": select_action_id,
            "action_id": select_action_id,
            "clear_action_id": clear_action_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "element_id": f"page.{page_slug}.upload.injected",
            "debug_only": True,
            "studio_injected": True,
        }
    )
    actions[select_action_id] = {
        "id": select_action_id,
        "type": "upload_select",
        "name": upload_name,
        "multiple": False,
        "required": False,
        "debug_only": True,
    }
    actions[clear_action_id] = {
        "id": clear_action_id,
        "type": "upload_clear",
        "name": upload_name,
        "debug_only": True,
    }
    actions[ingestion_action_id] = {
        "id": ingestion_action_id,
        "type": "ingestion_run",
        "debug_only": True,
    }
    taken_actions.update({select_action_id, clear_action_id, ingestion_action_id})
    return True


def _upload_files_for_name(state: dict, upload_name: str) -> list[dict]:
    if not isinstance(state, dict):
        return []
    uploads = state.get("uploads")
    if not isinstance(uploads, dict):
        return []
    return _normalize_upload_entries(uploads.get(upload_name))


def _normalize_upload_entries(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        if _looks_like_upload_entry(raw):
            return [raw]
        return [entry for entry in raw.values() if isinstance(entry, dict)]
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    return []


def _looks_like_upload_entry(entry: dict) -> bool:
    identifier = entry.get("id") if isinstance(entry.get("id"), str) and entry.get("id") else entry.get("checksum")
    name = entry.get("name")
    return isinstance(identifier, str) and bool(identifier) and isinstance(name, str) and bool(name)


__all__ = ["inject_default_upload_control", "public_upload_request"]
