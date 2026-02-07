from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import time
from namel3ss.compatibility import validate_spec_version
from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.ir import nodes as ir
from namel3ss.observe import actor_summary, record_event, summarize_value
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.records.service import save_record_with_errors
from namel3ss.runtime.records.state_paths import set_state_record
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.observability.enablement import resolve_observability_context
from namel3ss.secrets import collect_secret_values
from namel3ss.ui.manifest import build_manifest
from namel3ss.runtime.ui.actions.form_policy import enforce_form_policy, submit_form_trace
from namel3ss.runtime.ui.actions.ingestion_review import handle_ingestion_review_action
from namel3ss.runtime.ui.actions.ingestion_run import handle_ingestion_run_action
from namel3ss.runtime.ui.actions.ingestion_skip import handle_ingestion_skip_action
from namel3ss.runtime.ui.actions.retrieval_run import handle_retrieval_run_action
from namel3ss.runtime.ui.actions.upload_select import handle_upload_select_action
from namel3ss.runtime.ui.actions.upload_replace import handle_upload_replace_action
from namel3ss.runtime.ui.actions.validate import (
    action_payload_message,
    action_disabled_message,
    ensure_json_serializable,
    normalize_submit_payload,
    text_input_missing_message,
    text_input_type_message,
    unknown_action_message,
)
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO

_SIMPLE_ACTIONS = {
    "ingestion_run": handle_ingestion_run_action,
    "ingestion_review": handle_ingestion_review_action,
    "ingestion_skip": handle_ingestion_skip_action,
    "retrieval_run": handle_retrieval_run_action,
    "upload_replace": handle_upload_replace_action,
}

def handle_action(
    program_ir: ir.Program,
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
) -> tuple[dict, Exception | None]:
    """Execute a UI action against the program."""
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
    )
    actions: Dict[str, dict] = manifest.get("actions", {})
    if action_id not in actions:
        raise Namel3ssError(unknown_action_message(action_id, actions))

    action = actions[action_id]
    if action.get("enabled") is False:
        predicate = None
        availability = action.get("availability")
        if isinstance(availability, dict):
            predicate = availability.get("predicate")
        raise Namel3ssError(action_disabled_message(action_id, predicate))
    action_type = action.get("type")
    obs = None
    owns_obs = False
    span_id = None
    span_status = "ok"
    try:
        if action_type == "call_flow":
            response, action_error = _handle_call_flow(
                program_ir,
                action,
                action_id,
                payload or {},
                working_state,
                store,
                manifest,
                runtime_theme,
                memory_manager=memory_manager,
                preference_store=preference_store,
                preference_key=preference_key,
                allow_theme_override=allow_theme_override,
                config=resolved_config,
                identity=identity,
                auth_context=auth_context,
                session=session,
                secret_values=secret_values,
                source=source,
                raise_on_error=raise_on_error,
                ui_mode=ui_mode,
            )
            if action_error and raise_on_error:
                raise action_error
            if action_error:
                _record_engine_error(project_root, action_id, actor, action_error, secret_values)
        elif action_type == "submit_form":
            obs, owns_obs = resolve_observability_context(
                None,
                project_root=project_root,
                app_path=getattr(program_ir, "app_path", None),
                config=resolved_config,
            )
            if obs and owns_obs:
                obs.start_session()
            if obs:
                span_id = obs.start_span(
                    None,
                    name=f"action:{action_id}",
                    kind="action",
                    details={"action_id": action_id, "type": "submit_form"},
                    timing_name="action",
                    timing_labels={"action": action_id, "type": "submit_form"},
                )
            try:
                response = _handle_submit_form(
                    program_ir,
                    action,
                    action_id,
                    payload or {},
                    working_state,
                    store,
                    manifest,
                    runtime_theme,
                    config=resolved_config,
                    identity=identity,
                    secret_values=secret_values,
                    source=source,
                    ui_mode=ui_mode,
                )
            except Exception:
                span_status = "error"
                raise
            finally:
                if obs and span_id:
                    obs.end_span(None, span_id, status=span_status)
                if obs and owns_obs:
                    obs.flush()
        elif action_type == "upload_select":
            response = handle_upload_select_action(
                program_ir,
                action=action,
                action_id=action_id,
                payload=payload or {},
                state=working_state,
                store=store,
                runtime_theme=runtime_theme,
                config=resolved_config,
                identity=identity,
                auth_context=auth_context,
                secret_values=secret_values,
            )
        elif action_type in _SIMPLE_ACTIONS:
            response = _handle_simple_action(
                _SIMPLE_ACTIONS[action_type],
                program_ir,
                action_id=action_id,
                payload=payload or {},
                state=working_state,
                store=store,
                runtime_theme=runtime_theme,
                config=resolved_config,
                identity=identity,
                auth_context=auth_context,
                secret_values=secret_values,
            )
        else:
            raise Namel3ssError(f"Unsupported action type '{action_type}'")
    except Exception as err:
        span_status = "error"
        action_error = err
        if project_root:
            _record_engine_error(project_root, action_id, actor, err, secret_values)
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
                    "status": status,
                    "time_start": start_time,
                    "time_end": time.time(),
                    "actor": actor,
                    "input_summary": summarize_value(payload or {}, secret_values=secret_values),
                },
                secret_values=secret_values,
            )
    return response

def _handle_simple_action(
    handler,
    program_ir: ir.Program,
    *,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    config: AppConfig | None,
    identity: dict | None,
    auth_context: object | None,
    secret_values: list[str] | None,
) -> dict:
    return handler(
        program_ir,
        action_id=action_id,
        payload=payload,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        config=config,
        identity=identity,
        auth_context=auth_context,
        secret_values=secret_values,
    )

def _record_engine_error(
    project_root: str | Path | None,
    action_id: str,
    actor: dict,
    err: Exception,
    secret_values: list[str] | None,
) -> None:
    if not project_root:
        return
    record_event(
        Path(str(project_root)),
        {
            "type": "engine_error",
            "kind": err.__class__.__name__,
            "message": str(err),
            "action_id": action_id,
            "actor": actor,
            "time": time.time(),
        },
        secret_values=secret_values,
    )


def _form_error_payload(errors: list[dict]) -> dict:
    details = {"error_id": "form_validation", "form_errors": errors}
    return build_error_payload("Form validation failed.", kind="runtime", details=details)


def _handle_call_flow(
    program_ir: ir.Program,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    manifest: dict,
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
) -> dict:
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
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response, None


def _handle_submit_form(
    program_ir: ir.Program,
    action: dict,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    manifest: dict,
    runtime_theme: Optional[str],
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    secret_values: list[str] | None = None,
    source: str | None = None,
    ui_mode: str = DISPLAY_MODE_STUDIO,
) -> dict:
    payload = normalize_submit_payload(payload)
    record = action.get("record")
    if not isinstance(record, str):
        raise Namel3ssError("Invalid record reference in form action")
    values = payload["values"]
    trace = submit_form_trace(record, values)
    policy_trace, decision = enforce_form_policy(
        program_ir,
        manifest,
        action_id,
        record,
        payload,
        state,
        identity,
        auth_context,
    )
    if not decision.allowed:
        trace["ok"] = False
        error = Namel3ssError(
            decision.error_message or decision.message or "Mutation blocked by policy.",
            details={
                "category": "policy",
                "reason_code": decision.reason_code,
                "flow_name": policy_trace.get("flow_name"),
                "record": record,
                "action": "save",
                "step_id": policy_trace.get("step_id"),
            },
        )
        error_payload = build_error_from_exception(error, kind="runtime", source=source)
        response = build_run_payload(
            ok=False,
            flow_name=None,
            state=state,
            result=None,
            traces=[policy_trace, trace],
            project_root=getattr(program_ir, "project_root", None),
            error_payload=error_payload,
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
        )
        ensure_json_serializable(response)
        response = finalize_run_payload(response, secret_values)
        return response
    set_state_record(state, record, values)
    schemas = {schema.name: schema for schema in program_ir.records}
    saved, errors = save_record_with_errors(record, values, schemas, state, store, identity=identity)
    if errors:
        trace["ok"] = False
        trace["errors"] = [err.get("field") for err in errors if err.get("field")]
        error_payload = _form_error_payload(errors)
        response = build_run_payload(
            ok=False,
            flow_name=None,
            state=state,
            result=None,
            traces=[policy_trace, trace],
            project_root=getattr(program_ir, "project_root", None),
            error_payload=error_payload,
        )
        response["errors"] = errors
        response["ui"] = build_manifest(
            program_ir,
            config=config,
            state=state,
            store=store,
            runtime_theme=runtime_theme,
            identity=identity,
            auth_context=auth_context,
            display_mode=ui_mode,
        )
        response.pop("error", None)
        response.pop("message", None)
        ensure_json_serializable(response)
        response = finalize_run_payload(response, secret_values)
        return response

    record_id = saved.get("id") if isinstance(saved, dict) else None
    record_id = record_id or (saved.get("_id") if isinstance(saved, dict) else None)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"record": record, "id": record_id},
        traces=[policy_trace, trace],
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
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response
__all__ = ["handle_action"]
