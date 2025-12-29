from __future__ import annotations


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
        items.append(item)
    return items


def build_actions_export(manifest: dict) -> dict:
    actions = manifest.get("actions") if isinstance(manifest, dict) else {}
    actions_map = actions if isinstance(actions, dict) else {}
    return {
        "schema_version": ACTIONS_EXPORT_VERSION,
        "actions": build_actions_list(actions_map),
    }


__all__ = ["ACTIONS_EXPORT_VERSION", "build_actions_export", "build_actions_list"]
