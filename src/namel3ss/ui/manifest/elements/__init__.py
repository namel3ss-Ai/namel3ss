from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.media import MediaValidationMode
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode
from .dispatch import page_item_to_manifest


def _build_children(
    children: List[ir.PageItem],
    record_map: Dict[str, schema.RecordSchema],
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
    parent_visible: bool = True,
) -> tuple[List[dict], Dict[str, dict]]:
    elements: List[dict] = []
    actions: Dict[str, dict] = {}
    for idx, child in enumerate(children):
        seen_before = set(taken_actions)
        element, child_actions, child_visible = page_item_to_manifest(
            child,
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
            parent_visible,
            _build_children,
        )
        elements.append(element)
        source_element_id = element.get("element_id") if isinstance(element, dict) else None
        debug_only_value = element.get("debug_only") if isinstance(element, dict) else None
        is_debug_only = bool(debug_only_value) and debug_only_value is not False
        if isinstance(source_element_id, str):
            for action_entry in child_actions.values():
                if isinstance(action_entry, dict):
                    action_entry.setdefault("_source_element_id", source_element_id)
                    if is_debug_only:
                        action_entry.setdefault("debug_only", debug_only_value if isinstance(debug_only_value, str) else True)
        for action_id, action_entry in child_actions.items():
            if action_id in seen_before:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
                    line=child.line,
                    column=child.column,
                )
            taken_actions.add(action_id)
            if child_visible:
                actions[action_id] = action_entry
    return elements, actions


__all__ = ["_build_children"]
