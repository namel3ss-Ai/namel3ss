from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from namel3ss.compatibility import validate_spec_version
from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.observe import actor_summary, record_event, summarize_value
from namel3ss.secrets import collect_secret_values
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.ui.actions.build.action_registry import dispatch_action
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.build.errors import record_engine_error
from namel3ss.runtime.ui.contracts.action_kind import canonical_action_kind
from namel3ss.runtime.ui.contracts.program_contract import ProgramContract
from namel3ss.runtime.ui.actions.validation.validate import (
    action_disabled_message,
    action_payload_message,
    unknown_action_message,
)
from namel3ss.runtime.ui.state.permissions import enforce_action_permission
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_action(
    program_ir: ProgramContract,
    *,
    action_id: str,
    payload: Optional[dict] = None,
    state: Optional[dict] = None,
    store: Optional[Storage] = None,
    runtime_theme: Optional[str] = None,
    memory_manager: MemoryManager | None = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    session: dict | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = True,
) -> tuple[dict, Exception | None]:
    start_time = time.time()
    if payload is not None and not isinstance(payload, dict):
        raise Namel3ssError(action_payload_message())
    validate_spec_version(program_ir)
    action_error: Exception | None = None
    resolved_config = config or load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    secret_values = collect_secret_values(resolved_config)
    store = resolve_store(store, config=resolved_config)
    identity = identity if identity is not None else resolve_identity(resolved_config, getattr(program_ir, "identity", None))
    actor = actor_summary(identity)
    project_root = getattr(program_ir, "project_root", None)
    working_state = store.load_state() if state is None else state
    manifest = build_manifest(
        program_ir,
        config=resolved_config,
        state=working_state,
        store=store,
        runtime_theme=runtime_theme,
        identity=identity,
        auth_context=auth_context,
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    actions: dict[str, dict] = manifest.get("actions", {})
    if action_id not in actions:
        raise Namel3ssError(unknown_action_message(action_id, actions))

    action = actions[action_id]
    if action.get("enabled") is False:
        predicate = None
        availability = action.get("availability")
        if isinstance(availability, dict):
            predicate = availability.get("predicate")
        raise Namel3ssError(action_disabled_message(action_id, predicate))
    action_type_raw = str(action.get("type") or "")
    action_type = canonical_action_kind(action_type_raw)
    try:
        enforce_action_permission(program_ir, action_type=action_type)
        dispatch = ActionDispatchContext(
            program_ir=program_ir,
            action=action,
            action_id=action_id,
            action_type=action_type,
            payload=payload or {},
            state=working_state,
            store=store,
            runtime_theme=runtime_theme,
            config=resolved_config,
            manifest=manifest,
            identity=identity,
            auth_context=auth_context,
            session=session,
            source=source,
            secret_values=secret_values,
            memory_manager=memory_manager,
            preference_store=preference_store,
            preference_key=preference_key,
            allow_theme_override=allow_theme_override,
            raise_on_error=raise_on_error,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
        response, action_error = dispatch_action(dispatch)
        if action_error and project_root:
            record_engine_error(project_root, action_id, actor, action_error, secret_values)
    except Exception as err:
        action_error = err
        if project_root:
            record_engine_error(project_root, action_id, actor, err, secret_values)
        raise
    finally:
        if project_root:
            resp = locals().get("response")
            if action_error is not None:
                status = "error"
            elif isinstance(resp, dict):
                status = "ok" if resp.get("ok", True) else "fail"
            else:
                status = "error"
            record_event(
                Path(str(project_root)),
                {
                    "type": "action_run",
                    "action_id": action_id,
                    "action_type": action_type,
                    "action_type_raw": action_type_raw,
                    "status": status,
                    "time_start": start_time,
                    "time_end": time.time(),
                    "actor": actor,
                    "input_summary": summarize_value(payload or {}, secret_values=secret_values),
                },
                secret_values=secret_values,
            )
    return response


__all__ = ["handle_action"]
