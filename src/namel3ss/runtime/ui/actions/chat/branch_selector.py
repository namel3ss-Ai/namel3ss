from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.runtime.ui.state.chat_shell import ensure_chat_shell_state, select_chat_branch
from namel3ss.runtime.ui.state.state_target import (
    assign_state_path,
    enforce_persistent_ui_write_permission,
    parse_target_path,
    state_path_label,
)
from namel3ss.ui.manifest import build_manifest


def handle_chat_branch_select_action(
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
    target_path = parse_target_path(action, action_id=action_id, action_name="Chat branch select")
    enforce_persistent_ui_write_permission(program_ir, target_path, action_type="chat.branch.select")
    message_id = _parse_message_id(payload)
    message_id = select_chat_branch(state, message_id)
    assign_state_path(state, target_path, message_id)
    target_label = state_path_label(target_path)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"message_id": message_id, "target_state": target_label},
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


def _parse_message_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat branch payload must be an object.")
    message_id = payload.get("message_id")
    if isinstance(message_id, str) and message_id.strip():
        return message_id.strip()
    active = payload.get("active")
    if isinstance(active, str) and active.strip():
        return active.strip()
    if isinstance(active, list):
        for idx, entry in enumerate(active):
            if not isinstance(entry, str):
                raise Namel3ssError(f"Chat branch payload value {idx} must be text.")
            if entry.strip():
                return entry.strip()
    raise Namel3ssError("Chat branch payload requires message_id or active with one message id.")


__all__ = ["handle_chat_branch_select_action"]
