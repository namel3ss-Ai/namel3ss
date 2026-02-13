from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.records.service import save_record_with_errors
from namel3ss.runtime.records.state_paths import set_state_record
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.build.errors import form_error_payload
from namel3ss.runtime.ui.state.form_policy import enforce_form_policy, submit_form_trace
from namel3ss.runtime.ui.actions.validation.validate import (
    ensure_json_serializable,
    normalize_submit_payload,
)
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_submit_form_action(
    program_ir,
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
    diagnostics_enabled: bool = False,
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
            diagnostics_enabled=diagnostics_enabled,
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
        error_payload = form_error_payload(errors)
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
            diagnostics_enabled=diagnostics_enabled,
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
        diagnostics_enabled=diagnostics_enabled,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


__all__ = ["handle_submit_form_action"]
