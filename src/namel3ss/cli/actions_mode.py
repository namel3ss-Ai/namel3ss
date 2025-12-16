from __future__ import annotations

from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest


def list_actions(program_ir, json_mode: bool) -> tuple[dict | None, str | None]:
    manifest = build_manifest(program_ir, state={}, store=MemoryStore())
    actions = manifest.get("actions", {})
    sorted_ids = sorted(actions.keys())
    if json_mode:
        data = []
        for action_id in sorted_ids:
            entry = actions[action_id]
            item = {"id": action_id, "type": entry.get("type")}
            if entry.get("type") == "call_flow":
                item["flow"] = entry.get("flow")
            if entry.get("type") == "submit_form":
                item["record"] = entry.get("record")
            data.append(item)
        return (
            {
                "ok": True,
                "count": len(data),
                "actions": data,
            },
            None,
        )
    lines = []
    for action_id in sorted_ids:
        entry = actions[action_id]
        details: list[str] = []
        if entry.get("type") == "call_flow" and entry.get("flow"):
            details.append(f"flow={entry['flow']}")
        if entry.get("type") == "submit_form" and entry.get("record"):
            details.append(f"record={entry['record']}")
        detail_str = f"  {' '.join(details)}" if details else ""
        lines.append(f"{action_id}  {entry.get('type')} {detail_str}".rstrip())
    return None, "\n".join(lines)
