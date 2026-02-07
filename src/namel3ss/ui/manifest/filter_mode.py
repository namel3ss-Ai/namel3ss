from __future__ import annotations

from copy import deepcopy
from typing import Any

from namel3ss.ui.manifest.display_mode import (
    DISPLAY_MODE_PRODUCTION,
    DISPLAY_MODE_STUDIO,
    normalize_display_mode,
)

_INTERNAL_ACTION_SOURCE_KEY = "_source_element_id"

_IMPLICIT_DEBUG_ELEMENT_TYPES = {
    "thinking",
    "citations",
    "memory",
}

_SYSTEM_DEBUG_ACTION_TYPES = {
    "retrieval_run",
    "ingestion_review",
    "ingestion_skip",
    "upload_replace",
}


def apply_display_mode_filter(manifest: dict, *, display_mode: str) -> dict:
    mode = normalize_display_mode(display_mode, default=DISPLAY_MODE_STUDIO)
    filtered = deepcopy(manifest if isinstance(manifest, dict) else {})
    filtered["mode"] = mode
    if mode == DISPLAY_MODE_STUDIO:
        _strip_internal_action_source(filtered.get("actions"))
        return filtered

    pages = filtered.get("pages")
    kept_element_ids: set[str] = set()
    if isinstance(pages, list):
        filtered_pages: list[dict] = []
        for page in pages:
            page_result = _filter_page(page)
            if page_result is None:
                continue
            page_payload, page_element_ids = page_result
            filtered_pages.append(page_payload)
            kept_element_ids.update(page_element_ids)
        filtered["pages"] = filtered_pages
        _filter_navigation(filtered, filtered_pages)

    actions = filtered.get("actions")
    if isinstance(actions, dict):
        filtered["actions"] = _filter_actions(actions, kept_element_ids)
    _strip_internal_action_source(filtered.get("actions"))
    return filtered


def _filter_page(page: Any) -> tuple[dict, set[str]] | None:
    if not isinstance(page, dict):
        return None
    if _is_debug_only(page):
        return None
    next_page = dict(page)
    page_element_ids: set[str] = set()
    elements = next_page.get("elements")
    if isinstance(elements, list):
        filtered_elements, element_ids = _filter_elements(elements)
        next_page["elements"] = filtered_elements
        page_element_ids.update(element_ids)
    return next_page, page_element_ids


def _filter_elements(elements: list[Any]) -> tuple[list[dict], set[str]]:
    kept: list[dict] = []
    kept_ids: set[str] = set()
    for entry in elements:
        if not isinstance(entry, dict):
            continue
        if _is_debug_only(entry):
            continue
        element = dict(entry)
        children = element.get("children")
        if isinstance(children, list):
            filtered_children, child_ids = _filter_elements(children)
            element["children"] = filtered_children
            kept_ids.update(child_ids)
        element_id = element.get("element_id")
        if isinstance(element_id, str) and element_id:
            kept_ids.add(element_id)
        kept.append(element)
    return kept, kept_ids


def _filter_navigation(manifest: dict, pages: list[dict]) -> None:
    navigation = manifest.get("navigation")
    if not isinstance(navigation, dict):
        return
    page_slugs = {
        page.get("slug")
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("slug"), str)
    }
    if not page_slugs:
        manifest.pop("navigation", None)
        return
    active = navigation.get("active")
    if isinstance(active, str) and active not in page_slugs:
        manifest.pop("navigation", None)


def _filter_actions(actions: dict[str, Any], kept_element_ids: set[str]) -> dict[str, dict]:
    filtered: dict[str, dict] = {}
    for action_id in sorted(actions):
        action = actions.get(action_id)
        if not isinstance(action, dict):
            continue
        if _is_debug_action(action):
            continue
        source_element = action.get(_INTERNAL_ACTION_SOURCE_KEY)
        if isinstance(source_element, str) and source_element and source_element not in kept_element_ids:
            continue
        filtered[action_id] = dict(action)
    return filtered


def _strip_internal_action_source(actions: Any) -> None:
    if not isinstance(actions, dict):
        return
    for entry in actions.values():
        if isinstance(entry, dict):
            entry.pop(_INTERNAL_ACTION_SOURCE_KEY, None)


def _is_debug_action(action: dict) -> bool:
    if bool(action.get("debug_only")):
        return True
    action_type = action.get("type")
    return isinstance(action_type, str) and action_type in _SYSTEM_DEBUG_ACTION_TYPES


def _is_debug_only(entry: dict) -> bool:
    if bool(entry.get("debug_only")):
        return True
    element_type = entry.get("type")
    return isinstance(element_type, str) and element_type in _IMPLICIT_DEBUG_ELEMENT_TYPES


__all__ = ["apply_display_mode_filter"]
