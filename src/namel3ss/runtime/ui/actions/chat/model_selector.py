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
from namel3ss.runtime.ui.state.chat_shell import ensure_chat_shell_state, select_chat_models
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_chat_model_select_action(
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
    target_path = parse_target_path(action, action_id=action_id, action_name="Chat model select")
    options_path = parse_optional_path(action, key="options_state", action_id=action_id, action_name="Chat model select")
    enforce_persistent_ui_write_permission(program_ir, target_path, action_type="chat.model.select")
    model_ids = _parse_model_ids(payload)
    _validate_model_ids(model_ids, state=state, options_path=options_path)
    assign_state_path(state, target_path, model_ids)
    model_ids = select_chat_models(state, model_ids)
    target_label = state_path_label(target_path)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"target_state": target_label, "model_ids": model_ids},
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


def _parse_model_ids(payload: dict) -> list[str]:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat model payload must be an object.")
    value = payload.get("model_ids")
    if value is None:
        value = payload.get("active")
    if value is None:
        value = payload.get("model_id")
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if value is None:
        return []
    if not isinstance(value, list):
        raise Namel3ssError("Chat model payload requires model_ids as text or a list of text ids.")
    normalized: list[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(value):
        if not isinstance(entry, str):
            raise Namel3ssError(f"Chat model payload value {idx} must be text.")
        candidate = entry.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _validate_model_ids(model_ids: list[str], *, state: dict, options_path: list[str] | None) -> None:
    if not model_ids or options_path is None:
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
    if not known_ids:
        return
    unknown = [entry for entry in model_ids if entry not in known_ids]
    if unknown:
        raise Namel3ssError(f'Unknown model id "{unknown[0]}" for chat model selection.')


__all__ = ["handle_chat_model_select_action"]
