from __future__ import annotations

from typing import Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.records.service import save_record_with_errors
from namel3ss.runtime.records.state_paths import set_state_record
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.ui.manifest import build_manifest
from namel3ss.utils.json_tools import dumps as json_dumps

SUBMIT_RESERVED_KEYS = {"values", "errors", "ok", "result", "state", "traces"}


def handle_action(
    program_ir: ir.Program,
    *,
    action_id: str,
    payload: Optional[dict] = None,
    state: Optional[dict] = None,
    store: Optional[Storage] = None,
    runtime_theme: Optional[str] = None,
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
) -> dict:
    """Execute a UI action against the program."""
    if payload is not None and not isinstance(payload, dict):
        raise Namel3ssError(_action_payload_message())

    store = resolve_store(store)
    working_state = store.load_state() if state is None else state
    manifest = build_manifest(program_ir, state=working_state, store=store, runtime_theme=runtime_theme)
    actions: Dict[str, dict] = manifest.get("actions", {})
    if action_id not in actions:
        raise Namel3ssError(_unknown_action_message(action_id, actions))

    action = actions[action_id]
    action_type = action.get("type")
    if action_type == "call_flow":
        return _handle_call_flow(
            program_ir,
            action,
            payload or {},
            working_state,
            store,
            manifest,
            runtime_theme,
            preference_store=preference_store,
            preference_key=preference_key,
            allow_theme_override=allow_theme_override,
        )
    if action_type == "submit_form":
        return _handle_submit_form(program_ir, action, payload or {}, working_state, store, manifest, runtime_theme)
    raise Namel3ssError(f"Unsupported action type '{action_type}'")


def _ensure_json_serializable(data: dict) -> None:
    try:
        json_dumps(data)
    except Exception as exc:  # pragma: no cover - guard rail
        raise Namel3ssError(f"Response is not JSON-serializable: {exc}")


def _handle_call_flow(
    program_ir: ir.Program,
    action: dict,
    payload: dict,
    state: dict,
    store: Storage,
    manifest: dict,
    runtime_theme: Optional[str],
    preference_store=None,
    preference_key: str | None = None,
    allow_theme_override: bool | None = None,
) -> dict:
    flow_name = action.get("flow")
    if not isinstance(flow_name, str):
        raise Namel3ssError("Invalid flow reference in action")
    result = execute_program_flow(
        program_ir,
        flow_name,
        state=state,
        input=payload,
        store=store,
        runtime_theme=runtime_theme,
        preference_store=preference_store,
        preference_key=preference_key,
    )
    traces = [_trace_to_dict(t) for t in result.traces]
    next_runtime_theme = result.runtime_theme if result.runtime_theme is not None else runtime_theme
    if allow_theme_override and preference_store and preference_key and next_runtime_theme:
        preference_store.save_theme(preference_key, next_runtime_theme)
    response = {
        "ok": True,
        "state": result.state,
        "result": result.last_value,
        "ui": build_manifest(
            program_ir,
            state=result.state,
            store=store,
            runtime_theme=next_runtime_theme,
            persisted_theme=next_runtime_theme if allow_theme_override and preference_store else None,
        ),
        "traces": traces,
    }
    _ensure_json_serializable(response)
    return response


def _handle_submit_form(
    program_ir: ir.Program,
    action: dict,
    payload: dict,
    state: dict,
    store: Storage,
    manifest: dict,
    runtime_theme: Optional[str],
) -> dict:
    payload = _normalize_submit_payload(payload)
    record = action.get("record")
    if not isinstance(record, str):
        raise Namel3ssError("Invalid record reference in form action")
    values = payload["values"]
    set_state_record(state, record, values)
    schemas = {schema.name: schema for schema in program_ir.records}
    saved, errors = save_record_with_errors(record, values, schemas, state, store)
    if errors:
        response = {
            "ok": False,
            "state": state,
            "errors": errors,
            "ui": build_manifest(program_ir, state=state, store=store, runtime_theme=runtime_theme),
            "traces": [],
        }
        _ensure_json_serializable(response)
        return response

    record_id = saved.get("id") if isinstance(saved, dict) else None
    record_id = record_id or (saved.get("_id") if isinstance(saved, dict) else None)
    response = {
        "ok": True,
        "state": state,
        "result": {"record": record, "id": record_id},
        "ui": build_manifest(program_ir, state=state, store=store, runtime_theme=runtime_theme),
        "traces": [],
    }
    _ensure_json_serializable(response)
    return response


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    return dict(trace)


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
