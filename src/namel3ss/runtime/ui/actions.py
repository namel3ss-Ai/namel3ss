from __future__ import annotations

import json
from typing import Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.records.service import save_record_with_errors
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest


def handle_action(
    program_ir: ir.Program,
    *,
    action_id: str,
    payload: Optional[dict] = None,
    state: Optional[dict] = None,
    store: Optional[MemoryStore] = None,
) -> dict:
    """Execute a UI action against the program."""
    if payload is not None and not isinstance(payload, dict):
        raise Namel3ssError("Payload must be a dictionary")

    store = store or MemoryStore()
    working_state = {} if state is None else state
    manifest = build_manifest(program_ir, state=working_state, store=store)
    actions: Dict[str, dict] = manifest.get("actions", {})
    if action_id not in actions:
        raise Namel3ssError(f"Unknown action '{action_id}'")

    action = actions[action_id]
    action_type = action.get("type")
    if action_type == "call_flow":
        return _handle_call_flow(program_ir, action, payload or {}, working_state, store, manifest)
    if action_type == "submit_form":
        return _handle_submit_form(program_ir, action, payload or {}, working_state, store, manifest)
    raise Namel3ssError(f"Unsupported action type '{action_type}'")


def _ensure_json_serializable(data: dict) -> None:
    try:
        json.dumps(data)
    except Exception as exc:  # pragma: no cover - guard rail
        raise Namel3ssError(f"Response is not JSON-serializable: {exc}")


def _handle_call_flow(
    program_ir: ir.Program,
    action: dict,
    payload: dict,
    state: dict,
    store: MemoryStore,
    manifest: dict,
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
    )
    traces = [_trace_to_dict(t) for t in result.traces]
    response = {
        "ok": True,
        "state": result.state,
        "result": result.last_value,
        "ui": build_manifest(program_ir, state=result.state, store=store),
        "traces": traces,
    }
    _ensure_json_serializable(response)
    return response


def _handle_submit_form(
    program_ir: ir.Program,
    action: dict,
    payload: dict,
    state: dict,
    store: MemoryStore,
    manifest: dict,
) -> dict:
    if "values" not in payload or not isinstance(payload.get("values"), dict):
        raise Namel3ssError("Submit form payload must include a 'values' dictionary")
    record = action.get("record")
    if not isinstance(record, str):
        raise Namel3ssError("Invalid record reference in form action")
    values = payload["values"]
    state_key = record.lower()
    state[state_key] = values
    schemas = {schema.name: schema for schema in program_ir.records}
    saved, errors = save_record_with_errors(record, values, schemas, state, store)
    if errors:
        response = {
            "ok": False,
            "state": state,
            "errors": errors,
            "ui": build_manifest(program_ir, state=state, store=store),
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
        "ui": build_manifest(program_ir, state=state, store=store),
        "traces": [],
    }
    _ensure_json_serializable(response)
    return response


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    return dict(trace)
