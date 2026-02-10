from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from .base import _base_element
from .actions.ids import _element_id


def build_grid_item(
    item: ir.GridItem,
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
    base = _base_element(_element_id(page_slug, "grid", path), page_name, page_slug, index, item)
    element = {
        "type": "grid",
        "columns": list(getattr(item, "columns", []) or []),
        "children": children,
        **base,
    }
    return _attach_origin(element, item), actions


def build_loading_item(item: ir.LoadingItem, *, page_name: str, page_slug: str, path: List[int]) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    base = _base_element(_element_id(page_slug, "loading", path), page_name, page_slug, index, item)
    element = {
        "type": "loading",
        "variant": str(getattr(item, "variant", "spinner") or "spinner"),
        "aria": {"role": "status", "busy": True},
        **base,
    }
    return _attach_origin(element, item), {}


def build_badge_item(
    item: ir.BadgeItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    state_ctx: StateContext,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "badge", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    source = f"state.{'.'.join(item.source.path)}"
    value, _ = state_ctx.value(item.source.path, default=None, register_default=True)
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        raise Namel3ssError("Badges expect text values bound from state.<path>.", line=item.line, column=item.column)
    style = str(getattr(item, "style", "neutral") or "neutral")
    element = {
        "type": "badge",
        "source": source,
        "text": text,
        "style": style,
        **base,
    }
    return _attach_origin(element, item), {}


def build_snackbar_item(item: ir.SnackbarItem, *, page_name: str, page_slug: str, path: List[int]) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    base = _base_element(_element_id(page_slug, "snackbar", path), page_name, page_slug, index, item)
    element = {
        "type": "snackbar",
        "message": str(getattr(item, "message", "") or ""),
        "duration_ms": int(getattr(item, "duration", 3000) or 3000),
        "aria": {"role": "status", "live": "polite"},
        **base,
    }
    return _attach_origin(element, item), {}


def build_icon_item(item: ir.IconItem, *, page_name: str, page_slug: str, path: List[int]) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    role = str(getattr(item, "role", "decorative") or "decorative")
    label = getattr(item, "label", None)
    base = _base_element(_element_id(page_slug, "icon", path), page_name, page_slug, index, item)
    element = {
        "type": "icon",
        "name": str(getattr(item, "name", "") or ""),
        "size": str(getattr(item, "size", "medium") or "medium"),
        "role": role,
        "aria": {
            "hidden": role == "decorative",
            "label": label if role == "semantic" else None,
        },
        **base,
    }
    return _attach_origin(element, item), {}


def build_lightbox_item(item: ir.LightboxItem, *, page_name: str, page_slug: str, path: List[int]) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    base = _base_element(_element_id(page_slug, "lightbox", path), page_name, page_slug, index, item)
    element = {
        "type": "lightbox",
        "images": list(getattr(item, "images", []) or []),
        "start_index": int(getattr(item, "start_index", 0) or 0),
        "keyboard_navigation": True,
        **base,
    }
    return _attach_origin(element, item), {}


__all__ = [
    "build_grid_item",
    "build_icon_item",
    "build_lightbox_item",
    "build_loading_item",
    "build_snackbar_item",
    "build_badge_item",
]
