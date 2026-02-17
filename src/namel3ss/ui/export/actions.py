from __future__ import annotations

from namel3ss.ui.export.guard import filter_export_actions


ACTIONS_EXPORT_VERSION = "1"


def build_actions_list(actions: dict) -> list[dict]:
    items: list[dict] = []
    for action_id in sorted(actions.keys()):
        entry = actions.get(action_id)
        if not isinstance(entry, dict):
            entry = {}
        action_type = entry.get("type") or ""
        item = {"id": action_id, "type": action_type}
        if action_type == "call_flow":
            flow = entry.get("flow")
            if flow is not None:
                item["flow"] = flow
        if action_type == "submit_form":
            record = entry.get("record")
            if record is not None:
                item["record"] = record
        if action_type == "upload_select":
            name = entry.get("name")
            if isinstance(name, str) and name:
                item["name"] = name
            multiple = entry.get("multiple")
            if isinstance(multiple, bool):
                item["multiple"] = multiple
            required = entry.get("required")
            if isinstance(required, bool):
                item["required"] = required
        if action_type == "upload_clear":
            name = entry.get("name")
            if isinstance(name, str) and name:
                item["name"] = name
        items.append(item)
    return items


def build_actions_export(manifest: dict) -> dict:
    actions = manifest.get("actions") if isinstance(manifest, dict) else {}
    actions_map = actions if isinstance(actions, dict) else {}
    filtered_actions, skipped = filter_export_actions(actions_map)
    return {
        "schema_version": ACTIONS_EXPORT_VERSION,
        "actions": build_actions_list(filtered_actions),
        "skipped": skipped,
    }


__all__ = ["ACTIONS_EXPORT_VERSION", "build_actions_export", "build_actions_list"]
