from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.app_permissions_engine import require_permission


def parse_target_path(action: dict, *, action_id: str, action_name: str) -> list[str]:
    target_state = action.get("target_state")
    if not isinstance(target_state, str) or not target_state.startswith("state."):
        raise Namel3ssError(f"{action_name} action '{action_id}' has an invalid target_state.")
    parts = [part for part in target_state.split(".")[1:] if part]
    if not parts:
        raise Namel3ssError(f"{action_name} action '{action_id}' has an invalid target_state.")
    return parts


def parse_optional_path(
    action: dict,
    *,
    key: str,
    action_id: str,
    action_name: str,
) -> list[str] | None:
    raw = action.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.startswith("state."):
        raise Namel3ssError(f"{action_name} action '{action_id}' has an invalid {key}.")
    parts = [part for part in raw.split(".")[1:] if part]
    if not parts:
        raise Namel3ssError(f"{action_name} action '{action_id}' has an invalid {key}.")
    return parts


def read_state_path(state: dict, path: list[str], *, default: object = None) -> object:
    cursor: object = state
    for segment in path:
        if not isinstance(cursor, dict):
            return default
        if segment not in cursor:
            return default
        cursor = cursor[segment]
    return cursor


def assign_state_path(state: dict, path: list[str], value: object) -> None:
    cursor: dict = state
    for segment in path[:-1]:
        next_value = cursor.get(segment)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[segment] = next_value
        cursor = next_value
    cursor[path[-1]] = value


def enforce_persistent_ui_write_permission(program_ir, target_path: list[str], *, action_type: str) -> None:
    if len(target_path) < 2 or target_path[0] != "ui":
        return
    key = str(target_path[1] or "")
    scope_map = getattr(program_ir, "ui_state_scope_by_key", {}) or {}
    if scope_map.get(key) != "persistent":
        return
    require_permission(
        "ui_state.persistent_write",
        permissions=getattr(program_ir, "app_permissions", None),
        enabled=bool(getattr(program_ir, "app_permissions_enabled", False)),
        reason=f"ui action '{action_type}' writing state.ui.{key}",
    )


def state_path_label(path: list[str]) -> str:
    return f"state.{'.'.join(path)}"


__all__ = [
    "assign_state_path",
    "enforce_persistent_ui_write_permission",
    "parse_optional_path",
    "parse_target_path",
    "read_state_path",
    "state_path_label",
]
