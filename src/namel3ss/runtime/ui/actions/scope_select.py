from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest


def handle_scope_select_action(
    program_ir,
    *,
    action_id: str,
    action: dict,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    target_path = _parse_target_path(action, action_id)
    active = _parse_active(payload)
    _assign_state_path(state, target_path, active)
    target_label = f"state.{'.'.join(target_path)}"
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"target_state": target_label, "active": active},
        traces=[],
        project_root=getattr(program_ir, "project_root", None),
    )
    response["ui"] = build_manifest(
        program_ir,
        config=config,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        identity=identity,
        auth_context=auth_context,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


def _parse_target_path(action: dict, action_id: str) -> list[str]:
    target_state = action.get("target_state")
    if not isinstance(target_state, str) or not target_state.startswith("state."):
        raise Namel3ssError(f"Scope selector action '{action_id}' has an invalid target_state.")
    parts = [part for part in target_state.split(".")[1:] if part]
    if not parts:
        raise Namel3ssError(f"Scope selector action '{action_id}' has an invalid target_state.")
    return parts


def _parse_active(payload: dict) -> list[str]:
    active = payload.get("active") if isinstance(payload, dict) else None
    if active is None:
        return []
    if isinstance(active, str):
        return [active] if active else []
    if not isinstance(active, list):
        raise Namel3ssError("Scope selector payload requires active: [<id>, ...].")
    normalized: list[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(active):
        if not isinstance(entry, str):
            raise Namel3ssError(f"Scope selector payload value {idx} must be text.")
        if entry in seen:
            continue
        seen.add(entry)
        normalized.append(entry)
    return normalized


def _assign_state_path(state: dict, path: list[str], value: object) -> None:
    cursor: dict = state
    for segment in path[:-1]:
        next_value = cursor.get(segment)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[segment] = next_value
        cursor = next_value
    cursor[path[-1]] = value


__all__ = ["handle_scope_select_action"]
