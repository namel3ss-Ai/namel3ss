from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.ui.manifest_overlay import _drawer_id, _modal_id


def _list_id(page_slug: str, record_name: str) -> str:
    return f"page.{page_slug}.list.{_slugify(record_name)}"


def _list_action_id(element_id: str, label: str) -> str:
    return f"{element_id}.action.{_slugify(label)}"


def _list_id_field(record: schema.RecordSchema) -> str:
    return "id" if "id" in record.field_map else "_id"


def _list_item_mapping(mapping: ir.ListItemMapping) -> dict:
    payload = {"primary": mapping.primary}
    if mapping.secondary is not None:
        payload["secondary"] = mapping.secondary
    if mapping.meta is not None:
        payload["meta"] = mapping.meta
    if mapping.icon is not None:
        payload["icon"] = mapping.icon
    return payload


def _build_list_actions(
    element_id: str,
    actions: list[ir.ListAction] | None,
) -> tuple[list[dict], Dict[str, dict]]:
    if not actions:
        return [], {}
    seen: set[str] = set()
    entries: list[dict] = []
    action_map: Dict[str, dict] = {}
    for action in actions:
        action_id = _list_action_id(element_id, action.label)
        if action_id in seen:
            raise Namel3ssError(
                f"List action '{action.label}' collides with another action id",
                line=action.line,
                column=action.column,
            )
        seen.add(action_id)
        if action.kind == "call_flow":
            entry = {"id": action_id, "type": "call_flow", "flow": action.flow_name}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "flow": action.flow_name})
            continue
        if action.kind in {"open_modal", "close_modal"}:
            target = _modal_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        if action.kind in {"open_drawer", "close_drawer"}:
            target = _drawer_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        raise Namel3ssError(
            f"List action '{action.label}' is not supported",
            line=action.line,
            column=action.column,
        )
    return entries, action_map


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed


__all__ = [
    "_list_id",
    "_list_action_id",
    "_list_id_field",
    "_list_item_mapping",
    "_build_list_actions",
]
