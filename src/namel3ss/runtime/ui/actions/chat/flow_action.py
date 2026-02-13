from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.upload.requirements import validate_required_uploads_for_flow
from namel3ss.runtime.ui.contracts.program_contract import ProgramContract
from namel3ss.runtime.ui.actions.validation.validate import (
    ensure_json_serializable,
    text_input_missing_message,
    text_input_type_message,
)
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_call_flow_action(
    program_ir: ProgramContract,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    memory_manager: MemoryManager | None = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    session: dict | None = None,
    secret_values: list[str] | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> tuple[dict, Exception | None]:
    flow_name = action.get("flow")
    if not isinstance(flow_name, str):
        raise Namel3ssError("Invalid flow reference in action")
    input_field = action.get("input_field")
    if isinstance(input_field, str):
        if input_field not in payload:
            raise Namel3ssError(text_input_missing_message(input_field))
        value = payload.get(input_field)
        if not isinstance(value, str):
            raise Namel3ssError(text_input_type_message(input_field))
    validate_required_uploads_for_flow(program_ir, flow_name, state)
    outcome = build_flow_payload(
        program_ir,
        flow_name,
        state=state,
        input=payload,
        store=store,
        memory_manager=memory_manager,
        runtime_theme=runtime_theme,
        preference_store=preference_store,
        preference_key=preference_key,
        config=config,
        identity=identity,
        auth_context=auth_context,
        session=session,
        source=source,
        project_root=getattr(program_ir, "project_root", None),
        action_id=action_id,
    )
    response = outcome.payload
    if outcome.error:
        if not raise_on_error:
            response = finalize_run_payload(response, secret_values)
        return response, outcome.error
    next_runtime_theme = outcome.runtime_theme if outcome.runtime_theme is not None else runtime_theme
    if allow_theme_override and preference_store and preference_key and next_runtime_theme:
        preference_store.save_theme(preference_key, next_runtime_theme)
    state_payload = response.get("state")
    response["ui"] = build_manifest(
        program_ir,
        config=config,
        state=state_payload if isinstance(state_payload, dict) else {},
        store=store,
        runtime_theme=next_runtime_theme,
        persisted_theme=next_runtime_theme if allow_theme_override and preference_store else None,
        identity=identity,
        auth_context=auth_context,
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response, None


__all__ = ["handle_call_flow_action"]
