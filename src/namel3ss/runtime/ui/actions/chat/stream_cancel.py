from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.runtime.ui.state.chat_shell import ensure_chat_shell_state, request_chat_stream_cancel
from namel3ss.runtime.ui.state.state_target import (
    assign_state_path,
    enforce_persistent_ui_write_permission,
    parse_optional_path,
    state_path_label,
)
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_chat_stream_cancel_action(
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
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> dict:
    ensure_chat_shell_state(state)
    target_path = parse_optional_path(
        action,
        key="target_state",
        action_id=action_id,
        action_name="Chat stream cancel",
    )
    if target_path is not None:
        enforce_persistent_ui_write_permission(program_ir, target_path, action_type="chat.stream.cancel")
    stream_state = request_chat_stream_cancel(state)
    if target_path is not None:
        assign_state_path(state, target_path, bool(stream_state.get("cancel_requested")))
    result = {"stream_state": dict(stream_state)}
    if target_path is not None:
        result["target_state"] = state_path_label(target_path)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result=result,
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
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


__all__ = ["handle_chat_stream_cancel_action"]
