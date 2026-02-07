from __future__ import annotations

from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.state_defaults import StateContext


def build_custom_component_element(
    item: ir.CustomComponentItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    state_ctx: StateContext,
) -> tuple[dict, Dict[str, dict]]:
    registry = getattr(state_ctx, "ui_plugin_registry", None)
    if registry is None:
        raise Namel3ssError(
            "Custom UI component registry is not initialized.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    props: dict[str, object] = {}
    for prop in list(getattr(item, "properties", []) or []):
        key = str(getattr(prop, "name", "") or "")
        if not key:
            continue
        props[key] = _resolve_component_prop_value(getattr(prop, "value", None), state_ctx, item)
    rendered = registry.render_component(item.component_name, props=props, state=state_ctx.state_snapshot())
    element_id = _element_id(page_slug, "custom_component", path)
    index = path[-1] if path else 0
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        **base,
        "type": "custom_component",
        "component": item.component_name,
        "plugin": item.plugin_name,
        "props": props,
        "nodes": rendered,
    }
    return element, {}


def _resolve_component_prop_value(value: object, state_ctx: StateContext, item: ir.PageItem) -> object:
    if isinstance(value, ir.StatePath):
        label = f"state.{'.'.join(value.path)}"
        if not state_ctx.has_value(value.path):
            raise Namel3ssError(
                f"Custom component property requires known state path '{label}'.",
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
            )
        try:
            resolved, _ = state_ctx.value(value.path, default=None, register_default=False)
            return resolved
        except KeyError as err:
            raise Namel3ssError(
                f"Custom component property requires known state path '{label}'.",
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
            ) from err
    if isinstance(value, ir.Literal):
        return value.value
    return value


__all__ = ["build_custom_component_element"]
