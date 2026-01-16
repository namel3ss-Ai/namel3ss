from __future__ import annotations

from typing import List, Dict

from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin

from .base import _base_element


def build_number_item(
    item: ir.NumberItem,
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "number", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    entries: list[dict] = []
    for idx, entry in enumerate(item.entries):
        entry_id = f"{element_id}.entry.{idx}"
        if entry.kind == "count":
            entries.append(
                {
                    "id": entry_id,
                    "kind": "count",
                    "record": entry.record_name,
                    "label": entry.label,
                }
            )
        else:
            entries.append(
                {
                    "id": entry_id,
                    "kind": "phrase",
                    "value": entry.value,
                }
            )
    element = {"type": "number", "entries": entries, **base}
    return _attach_origin(element, item), {}


__all__ = ["build_number_item"]
