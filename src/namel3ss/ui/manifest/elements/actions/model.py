from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode

from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.action_availability import evaluate_action_availability
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode

from ..base import _base_element
from .ids import _allocate_action_id, _button_action_id, _element_id, _input_action_id, _link_action_id
from .validate import validate_image_reference


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


def build_text_input_item(
    item: ir.TextInputItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "input", path)
    base_action_id = _input_action_id(page_slug, item.name)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    enabled, availability = evaluate_action_availability(
        getattr(item, "availability_rule", None),
        state_ctx,
        mode,
        warnings,
        line=item.line,
        column=item.column,
    )
    action_entry = {
        "id": action_id,
        "type": "call_flow",
        "flow": item.flow_name,
        "input_field": item.name,
        "input_type": "text",
    }
    if availability is not None:
        action_entry["enabled"] = enabled
        action_entry["availability"] = availability
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "input",
        "input_type": "text",
        "name": item.name,
        "id": action_id,
        "action_id": action_id,
        "action": {"type": "call_flow", "flow": item.flow_name, "input_field": item.name},
        **base,
    }
    if availability is not None:
        element["enabled"] = enabled
        element["action"]["enabled"] = enabled
    return _attach_origin(element, item), {action_id: action_entry}


def build_button_item(
    item: ir.ButtonItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "button_item", path)
    base_action_id = _button_action_id(page_slug, item.label)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    enabled, availability = evaluate_action_availability(
        getattr(item, "availability_rule", None),
        state_ctx,
        mode,
        warnings,
        line=item.line,
        column=item.column,
    )
    action_entry = {"id": action_id, "type": "call_flow", "flow": item.flow_name}
    if availability is not None:
        action_entry["enabled"] = enabled
        action_entry["availability"] = availability
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "button",
        "label": item.label,
        "id": action_id,
        "action_id": action_id,
        "action": {"type": "call_flow", "flow": item.flow_name},
        **base,
    }
    if availability is not None:
        element["enabled"] = enabled
        element["action"]["enabled"] = enabled
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
    intent = validate_image_reference(
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
    "build_divider_item",
    "build_image_item",
    "build_link_item",
    "build_text_item",
    "build_text_input_item",
    "build_title_item",
]
