from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.actions import _allocate_action_id
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext


def build_slider_component(
    item: ir.SliderItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
    state_ctx: StateContext,
    taken_actions: set[str],
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "slider", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    value_binding = _state_path_label(item.value)
    value, _ = state_ctx.value(item.value.path, default=item.min_value, register_default=True)
    normalized_value = _normalize_slider_value(value, min_value=item.min_value, max_value=item.max_value)
    action_id = _allocate_action_id(f"{element_id}.change", element_id, taken_actions)
    taken_actions.add(action_id)
    element = {
        "type": "slider",
        "id": element_id,
        "label": item.label,
        "min": float(item.min_value),
        "max": float(item.max_value),
        "step": float(item.step),
        "value_binding": value_binding,
        "value": normalized_value,
        "on_change_action": action_id,
        "action": {
            "id": action_id,
            "type": "call_flow",
            "flow": item.flow_name,
            "input_field": "value",
        },
        **base,
    }
    if isinstance(item.help_text, str) and item.help_text.strip():
        element["help_tooltip_id"] = f"{element_id}.tooltip"
        element["help_tooltip_text"] = item.help_text.strip()
    action = {
        "id": action_id,
        "type": "call_flow",
        "flow": item.flow_name,
        "input_field": "value",
        "debug_only": bool(getattr(item, "debug_only", False)),
    }
    return _attach_origin(element, item), {action_id: action}


def _normalize_slider_value(value: object, *, min_value: float, max_value: float) -> float:
    if isinstance(value, bool):
        return float(min_value)
    if isinstance(value, (int, float)):
        number = float(value)
        if number < min_value:
            return float(min_value)
        if number > max_value:
            return float(max_value)
        return round(number, 6)
    return float(min_value)


def _state_path_label(path: ir.StatePath) -> str:
    return f"state.{'.'.join(path.path)}"


__all__ = ["build_slider_component"]
