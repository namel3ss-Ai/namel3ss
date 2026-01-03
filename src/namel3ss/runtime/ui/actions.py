from __future__ import annotations

from typing import Dict, Optional

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.records.service import save_record_with_errors
from namel3ss.runtime.records.state_paths import set_state_record
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.compatibility import validate_spec_version
from namel3ss.ui.manifest import build_manifest
from namel3ss.utils.json_tools import dumps as json_dumps
from namel3ss.secrets import collect_secret_values
from namel3ss.observe import actor_summary, record_event, summarize_value
from namel3ss.errors.payload import build_error_payload
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
import time
from pathlib import Path

SUBMIT_RESERVED_KEYS = {"values", "errors", "ok", "result", "state", "traces"}


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
    source: str | None = None,
    raise_on_error: bool = True,
) -> tuple[dict, Exception | None]:
    """Execute a UI action against the program."""
    start_time = time.time()
    if payload is not None and not isinstance(payload, dict):
        raise Namel3ssError(_action_payload_message())
    validate_spec_version(program_ir)

    action_error: Exception | None = None
    resolved_config = config or load_config(
        app_path=getattr(program_ir, "app_path", None),
        root=getattr(program_ir, "project_root", None),
    )
    secret_values = collect_secret_values(resolved_config)
    store = resolve_store(store, config=resolved_config)
    identity = resolve_identity(resolved_config, getattr(program_ir, "identity", None))
    actor = actor_summary(identity)
    project_root = getattr(program_ir, "project_root", None)
    working_state = store.load_state() if state is None else state
    manifest = build_manifest(
        program_ir,
        state=working_state,
        store=store,
        runtime_theme=runtime_theme,
        identity=identity,
    )
    actions: Dict[str, dict] = manifest.get("actions", {})
    if action_id not in actions:
        raise Namel3ssError(_unknown_action_message(action_id, actions))

    action = actions[action_id]
    action_type = action.get("type")
    try:
        if action_type == "call_flow":
            response, action_error = _handle_call_flow(
                program_ir,
                action,
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
                secret_values=secret_values,
                source=source,
                raise_on_error=raise_on_error,
            )
            if action_error and raise_on_error:
                raise action_error
            if action_error:
                _record_engine_error(project_root, action_id, actor, action_error, secret_values)
        elif action_type == "submit_form":
            response = _handle_submit_form(
                program_ir,
                action,
                payload or {},
                working_state,
                store,
                manifest,
                runtime_theme,
                identity=identity,
                secret_values=secret_values,
            )
        else:
            raise Namel3ssError(f"Unsupported action type '{action_type}'")
    except Exception as err:
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


def _ensure_json_serializable(data: dict) -> None:
    try:
        json_dumps(data)
    except Exception as exc:  # pragma: no cover - guard rail
        raise Namel3ssError(f"Response is not JSON-serializable: {exc}")


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
    secret_values: list[str] | None = None,
    source: str | None = None,
    raise_on_error: bool = True,
) -> dict:
    flow_name = action.get("flow")
    if not isinstance(flow_name, str):
        raise Namel3ssError("Invalid flow reference in action")
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
        source=source,
        project_root=getattr(program_ir, "project_root", None),
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
        state=state_payload if isinstance(state_payload, dict) else {},
        store=store,
        runtime_theme=next_runtime_theme,
        persisted_theme=next_runtime_theme if allow_theme_override and preference_store else None,
        identity=identity,
    )
    _ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response, None


def _handle_submit_form(
    program_ir: ir.Program,
    action: dict,
    payload: dict,
    state: dict,
    store: Storage,
    manifest: dict,
    runtime_theme: Optional[str],
    identity: dict | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    payload = _normalize_submit_payload(payload)
    record = action.get("record")
    if not isinstance(record, str):
        raise Namel3ssError("Invalid record reference in form action")
    values = payload["values"]
    trace = _submit_form_trace(record, values)
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
            traces=[trace],
            project_root=getattr(program_ir, "project_root", None),
            error_payload=error_payload,
        )
        response["errors"] = errors
        response["ui"] = build_manifest(
            program_ir,
            state=state,
            store=store,
            runtime_theme=runtime_theme,
            identity=identity,
        )
        response.pop("error", None)
        response.pop("message", None)
        _ensure_json_serializable(response)
        response = finalize_run_payload(response, secret_values)
        return response

    record_id = saved.get("id") if isinstance(saved, dict) else None
    record_id = record_id or (saved.get("_id") if isinstance(saved, dict) else None)
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"record": record, "id": record_id},
        traces=[trace],
        project_root=getattr(program_ir, "project_root", None),
    )
    response["ui"] = build_manifest(
        program_ir,
        state=state,
        store=store,
        runtime_theme=runtime_theme,
        identity=identity,
    )
    _ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


def _submit_form_trace(record: str, values: dict) -> dict:
    fields = sorted({str(key) for key in values.keys()})
    return {"type": "submit_form", "record": record, "ok": True, "fields": fields}


def _normalize_submit_payload(payload: dict | None) -> dict:
    payload = payload or {}
    if not isinstance(payload, dict):
        raise Namel3ssError(_submit_payload_type_message())
    if "values" in payload:
        if not isinstance(payload.get("values"), dict):
            raise Namel3ssError(_missing_values_message({"values"}))
        return payload
    reserved = {key for key in payload if key in SUBMIT_RESERVED_KEYS}
    if reserved:
        raise Namel3ssError(_missing_values_message(reserved))
    return {"values": payload}


def _submit_payload_type_message() -> str:
    return build_guidance_message(
        what="Submit form payload was not a JSON object.",
        why="Form submissions need a dictionary of field values; numbers, strings, or lists cannot be mapped to fields.",
        fix='Send {"values": {...}} or a flat object that can be wrapped automatically.',
        example='{"values":{"email":"ada@example.com"}} (or {"email":"ada@example.com"})',
    )


def _missing_values_message(reserved_keys: set[str]) -> str:
    reserved_note = f" Payload included reserved keys: {', '.join(sorted(reserved_keys))}." if reserved_keys else ""
    return build_guidance_message(
        what="Submit form payload is missing a 'values' object.",
        why="Form submissions read values from the 'values' key; other top-level keys are ignored." + reserved_note,
        fix='Send {"values": {...}} or pass a flat object so it can be wrapped automatically.',
        example='{"values":{"email":"ada@example.com"}} (or {"email":"ada@example.com"})',
    )


def _action_payload_message() -> str:
    return build_guidance_message(
        what="Action payload was not a JSON object.",
        why="UI actions expect a dictionary of inputs; arrays, numbers, or strings cannot be unpacked into fields.",
        fix='Send {} for empty payloads or pass an object like {"values":{"name":"Ada"}}.',
        example='n3 app.ai page.home.button.run "{}"',
    )


def _unknown_action_message(action_id: str, actions: Dict[str, dict]) -> str:
    available = sorted(actions.keys())
    sample = ", ".join(available[:5]) if available else "none"
    if len(available) > 5:
        sample += ", …"
    why = f"The manifest exposes actions: {sample}." if available else "No actions were generated for this app."
    example = f"n3 app.ai {available[0]} {{}}" if available else "n3 app.ai actions"
    return build_guidance_message(
        what=f"Unknown action '{action_id}'.",
        why=why,
        fix="Use an action id from `n3 app.ai actions` or define the action in app.ai.",
        example=example,
    )
