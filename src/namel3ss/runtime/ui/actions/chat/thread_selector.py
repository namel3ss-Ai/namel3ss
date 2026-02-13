from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.state.state_target import (
    assign_state_path,
    enforce_persistent_ui_write_permission,
    parse_optional_path,
    parse_target_path,
    read_state_path,
    state_path_label,
)
from namel3ss.runtime.ui.state.chat_shell import ensure_chat_shell_state, select_chat_thread
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest


def handle_chat_thread_select_action(
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
    ensure_chat_shell_state(state)
    target_path = parse_target_path(action, action_id=action_id, action_name="Chat thread select")
    options_path = parse_optional_path(action, key="options_state", action_id=action_id, action_name="Chat thread select")
    enforce_persistent_ui_write_permission(program_ir, target_path, action_type="chat.thread.select")
    thread_id = _parse_thread_id(payload)
    _validate_thread_id(thread_id, state=state, options_path=options_path)
    assign_state_path(state, target_path, thread_id)
    select_chat_thread(state, thread_id)
    target_label = state_path_label(target_path)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"target_state": target_label, "thread_id": thread_id},
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


def _parse_thread_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat thread payload must be an object.")
    thread_id = payload.get("thread_id")
    if isinstance(thread_id, str) and thread_id.strip():
        return thread_id.strip()
    active = payload.get("active")
    if isinstance(active, str) and active.strip():
        return active.strip()
    if isinstance(active, list):
        for idx, entry in enumerate(active):
            if not isinstance(entry, str):
                raise Namel3ssError(f"Chat thread payload value {idx} must be text.")
            if entry.strip():
                return entry.strip()
    raise Namel3ssError("Chat thread payload requires thread_id or active with one thread id.")


def _validate_thread_id(thread_id: str, *, state: dict, options_path: list[str] | None) -> None:
    if options_path is None:
        return
    value = read_state_path(state, options_path, default=[])
    if not isinstance(value, list):
        return
    known_ids: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        if isinstance(entry_id, str) and entry_id.strip():
            known_ids.add(entry_id.strip())
    if known_ids and thread_id not in known_ids:
        raise Namel3ssError(f'Unknown thread id "{thread_id}" for chat thread selection.')


__all__ = ["handle_chat_thread_select_action"]
