from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.elements.base import _base_element
from namel3ss.ui.manifest.origin import _attach_origin


def build_tooltip_component(
    item: ir.TooltipItem,
    *,
    page_name: str,
    page_slug: str,
    path: list[int],
) -> tuple[dict, dict]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "tooltip", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "tooltip",
        "id": element_id,
        "text": item.text,
        "collapsed_by_default": bool(item.collapsed_by_default),
        "anchor_control_label": item.anchor_label,
        **base,
    }
    return _attach_origin(element, item), {}


__all__ = ["build_tooltip_component"]

