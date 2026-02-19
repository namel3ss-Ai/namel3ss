from __future__ import annotations

from copy import deepcopy
from typing import Any

from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER, normalize_page_layout_dict
from namel3ss.ui.manifest.display_mode import (
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

def apply_display_mode_filter(
    manifest: dict,
    *,
    display_mode: str,
    diagnostics_enabled: bool = False,
    diagnostics_categories: tuple[str, ...] | None = None,
) -> dict:
    mode = normalize_display_mode(display_mode, default=DISPLAY_MODE_STUDIO)
    diagnostics_on = bool(diagnostics_enabled)
    filtered = deepcopy(manifest if isinstance(manifest, dict) else {})
    filtered["mode"] = mode
    filtered["diagnostics_enabled"] = diagnostics_on
    if mode == DISPLAY_MODE_STUDIO and diagnostics_on:
        _strip_internal_action_source(filtered.get("actions"))
        return filtered

    pages = filtered.get("pages")
    kept_element_ids: set[str] = set()
    categories = set(diagnostics_categories or ())
    if isinstance(pages, list):
        filtered_pages: list[dict] = []
        for page in pages:
            page_result = _filter_page(page, diagnostics_enabled=diagnostics_on, diagnostics_categories=categories)
            if page_result is None:
                continue
            page_payload, page_element_ids = page_result
            filtered_pages.append(page_payload)
            kept_element_ids.update(page_element_ids)
        filtered["pages"] = filtered_pages
        _filter_navigation(filtered, filtered_pages)

    actions = filtered.get("actions")
    if isinstance(actions, dict):
        filtered["actions"] = _filter_actions(
            actions,
            kept_element_ids,
            diagnostics_enabled=diagnostics_on,
            diagnostics_categories=categories,
        )
    _strip_internal_action_source(filtered.get("actions"))
    return filtered


def _filter_page(
    page: Any,
    *,
    diagnostics_enabled: bool,
    diagnostics_categories: set[str],
) -> tuple[dict, set[str]] | None:
    if not isinstance(page, dict):
        return None
    if bool(page.get("diagnostics")) and not diagnostics_enabled:
        return None
    if _is_debug_only(page, diagnostics_enabled=diagnostics_enabled, diagnostics_categories=diagnostics_categories):
        return None
    next_page = dict(page)
    page_element_ids: set[str] = set()
    layout = next_page.get("layout")
    if isinstance(layout, dict):
        normalized_layout = normalize_page_layout_dict(layout)
        filtered_layout: dict[str, list[dict]] = {}
        for slot_name in PAGE_LAYOUT_SLOT_ORDER:
            filtered_elements, element_ids = _filter_elements(
                normalized_layout.get(slot_name, []),
                diagnostics_enabled=diagnostics_enabled,
                diagnostics_categories=diagnostics_categories,
            )
            filtered_layout[slot_name] = filtered_elements
            page_element_ids.update(element_ids)
        next_page["layout"] = filtered_layout
        next_page.pop("elements", None)
    else:
        elements = next_page.get("elements")
        if isinstance(elements, list):
            filtered_elements, element_ids = _filter_elements(
                elements,
                diagnostics_enabled=diagnostics_enabled,
                diagnostics_categories=diagnostics_categories,
            )
            next_page["elements"] = filtered_elements
            page_element_ids.update(element_ids)
        else:
            next_page.pop("elements", None)
    diagnostics_blocks = next_page.get("diagnostics_blocks")
    if isinstance(diagnostics_blocks, list):
        if diagnostics_enabled:
            filtered_blocks, block_ids = _filter_elements(
                diagnostics_blocks,
                diagnostics_enabled=diagnostics_enabled,
                diagnostics_categories=diagnostics_categories,
            )
            next_page["diagnostics_blocks"] = filtered_blocks
            page_element_ids.update(block_ids)
        else:
            next_page.pop("diagnostics_blocks", None)
    if "layout" in next_page and not isinstance(next_page.get("layout"), dict):
        next_page.pop("layout", None)
    return next_page, page_element_ids


def _filter_elements(
    elements: list[Any],
    *,
    diagnostics_enabled: bool,
    diagnostics_categories: set[str],
) -> tuple[list[dict], set[str]]:
    kept: list[dict] = []
    kept_ids: set[str] = set()
    for entry in elements:
        if not isinstance(entry, dict):
            continue
        if _is_debug_only(entry, diagnostics_enabled=diagnostics_enabled, diagnostics_categories=diagnostics_categories):
            continue
        if entry.get("visible") is False:
            continue
        element = dict(entry)
        for child_key in ("children", "sidebar", "main", "then_children", "else_children"):
            children = element.get(child_key)
            if isinstance(children, list):
                filtered_children, child_ids = _filter_elements(
                    children,
                    diagnostics_enabled=diagnostics_enabled,
                    diagnostics_categories=diagnostics_categories,
                )
                element[child_key] = filtered_children
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
        return
    active_page = navigation.get("active_page")
    if isinstance(active_page, dict):
        slug = active_page.get("slug")
        if isinstance(slug, str) and slug and slug not in page_slugs:
            manifest.pop("navigation", None)
            return
    sidebar = navigation.get("sidebar")
    if isinstance(sidebar, list):
        filtered_sidebar = []
        for entry in sidebar:
            if not isinstance(entry, dict):
                continue
            target_slug = entry.get("target_slug")
            if isinstance(target_slug, str) and target_slug and target_slug in page_slugs:
                filtered_sidebar.append(dict(entry))
        if filtered_sidebar:
            navigation["sidebar"] = filtered_sidebar
        else:
            navigation.pop("sidebar", None)
    if not navigation:
        manifest.pop("navigation", None)


def _filter_actions(
    actions: dict[str, Any],
    kept_element_ids: set[str],
    *,
    diagnostics_enabled: bool,
    diagnostics_categories: set[str],
) -> dict[str, dict]:
    filtered: dict[str, dict] = {}
    for action_id in sorted(actions):
        action = actions.get(action_id)
        if not isinstance(action, dict):
            continue
        if _is_debug_action(action, diagnostics_enabled=diagnostics_enabled, diagnostics_categories=diagnostics_categories):
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


def _is_debug_action(action: dict, *, diagnostics_enabled: bool, diagnostics_categories: set[str]) -> bool:
    if _debug_marker_hidden(
        action.get("debug_only"),
        diagnostics_enabled=diagnostics_enabled,
        diagnostics_categories=diagnostics_categories,
    ):
        return True
    if diagnostics_enabled:
        return False
    action_type = action.get("type")
    return isinstance(action_type, str) and action_type in _SYSTEM_DEBUG_ACTION_TYPES


def _is_debug_only(entry: dict, *, diagnostics_enabled: bool, diagnostics_categories: set[str]) -> bool:
    if _debug_marker_hidden(
        entry.get("debug_only"),
        diagnostics_enabled=diagnostics_enabled,
        diagnostics_categories=diagnostics_categories,
    ):
        return True
    if diagnostics_enabled:
        return False
    element_type = entry.get("type")
    if not isinstance(element_type, str) or element_type not in _IMPLICIT_DEBUG_ELEMENT_TYPES:
        return False
    if "debug_only" in entry and entry.get("debug_only") is False:
        return False
    return True


def _debug_marker_hidden(
    marker: object,
    *,
    diagnostics_enabled: bool,
    diagnostics_categories: set[str],
) -> bool:
    if marker is False or marker is None:
        return False
    if isinstance(marker, str):
        if not diagnostics_enabled:
            return True
        if not diagnostics_categories:
            return False
        return marker not in diagnostics_categories
    if bool(marker):
        return not diagnostics_enabled
    return False


__all__ = ["apply_display_mode_filter"]
