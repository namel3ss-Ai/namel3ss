from __future__ import annotations

import json
from pathlib import Path

from namel3ss.tools_with.builder import build_tools_with_pack
from namel3ss.tools_with.model import ToolsWithPack


def build_tools_pack(traces: list, *, project_root: str | None) -> ToolsWithPack:
    return build_tools_with_pack(traces, project_root=project_root)


def load_tools_pack(path: Path) -> ToolsWithPack | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return ToolsWithPack(
        tools_called=int(payload.get("tools_called") or 0),
        allowed=_list_of_dicts(payload.get("allowed")),
        blocked=_list_of_dicts(payload.get("blocked")),
        errors=_list_of_dicts(payload.get("errors")),
        none_used=bool(payload.get("none_used", False)),
        notes=[str(item) for item in payload.get("notes") or []],
    )


def _list_of_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


__all__ = ["ToolsWithPack", "build_tools_pack", "load_tools_pack"]
