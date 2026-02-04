from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.runtime.storage.base import Storage
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest.visibility import apply_visibility, evaluate_visibility
from namel3ss.validation import ValidationMode

from .base import _base_element


def build_tabs_item(
    item: ir.TabsItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    media_registry: dict,
    media_mode,
    warnings: list | None,
    taken_actions: set[str],
    build_children,
    parent_visible: bool,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "tabs", path)
    tabs: list[dict] = []
    action_map: Dict[str, dict] = {}
    labels: list[str] = []
    for idx, tab in enumerate(item.tabs):
        labels.append(tab.label)
        tab_predicate_visible, tab_visibility = evaluate_visibility(
            getattr(tab, "visibility", None),
            getattr(tab, "visibility_rule", None),
            state_ctx,
            mode,
            warnings,
            line=tab.line,
            column=tab.column,
        )
        tab_visible = parent_visible and tab_predicate_visible
        children, actions = build_children(
            tab.children,
            record_map,
            page_name,
            page_slug,
            path + [idx],
            store,
            identity,
            state_ctx,
            mode,
            media_registry,
            media_mode,
            warnings,
            taken_actions,
            parent_visible=tab_visible,
        )
        action_map.update(actions)
        tab_base = _base_element(_element_id(page_slug, "tab", path + [idx]), page_name, page_slug, idx, tab)
        tab_element = _attach_origin(
            {
                "type": "tab",
                "label": tab.label,
                "children": children,
                **tab_base,
            },
            tab,
        )
        tabs.append(apply_visibility(tab_element, tab_visible, tab_visibility))
    default_label = item.default or (labels[0] if labels else "")
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = {
        "type": "tabs",
        "tabs": labels,
        "default": default_label,
        "active": default_label,
        "children": tabs,
        **base,
    }
    return _attach_origin(element, item), action_map


__all__ = ["build_tabs_item"]
