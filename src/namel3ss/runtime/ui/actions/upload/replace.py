from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import (
    ACTION_UPLOAD_REPLACE,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_error,
    policy_trace,
)
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.traces.schema import TraceEventType
from namel3ss.ui.manifest import build_manifest
from namel3ss.errors.payload import build_error_from_exception


def handle_upload_replace_action(
    program_ir,
    *,
    action_id: str,
    payload: dict,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    config: AppConfig | None = None,
    identity: dict | None = None,
    auth_context: object | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    _require_uploads_capability(program_ir)
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_type_message())
    upload_id = payload.get("upload_id")
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    policy = load_ingestion_policy(
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        policy_decl=getattr(program_ir, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_UPLOAD_REPLACE, identity)
    traces = [policy_trace(ACTION_UPLOAD_REPLACE, decision)]
    if not decision.allowed:
        return _policy_denied_response(
            program_ir,
            state,
            store,
            runtime_theme,
            traces=traces,
            config=config,
            identity=identity,
            auth_context=auth_context,
            secret_values=secret_values,
            error=policy_error(ACTION_UPLOAD_REPLACE, decision),
        )
    result = {"upload_id": upload_id.strip(), "status": "placeholder"}
    traces.extend(
        [
            {
                "type": TraceEventType.UPLOAD_REPLACE_REQUESTED,
                "upload_id": upload_id.strip(),
            }
        ]
    )
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"upload_replace": result},
        traces=traces,
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


def _require_uploads_capability(program_ir) -> None:
    caps = getattr(program_ir, "capabilities", ()) or ()
    if "uploads" in caps:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Upload replace applies to uploaded files.",
            fix="Add uploads to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Upload replace payload must be an object.",
        why="Upload replace expects an upload_id.",
        fix='Send {"upload_id":"<checksum>"}.',
        example='{"upload_id":"<checksum>"}',
    )


def _upload_id_message() -> str:
    return build_guidance_message(
        what="Upload replace requires an upload_id.",
        why="Replacement targets a specific upload.",
        fix="Provide the upload checksum.",
        example='{"upload_id":"<checksum>"}',
    )


def _policy_denied_response(
    program_ir,
    state: dict,
    store: Storage,
    runtime_theme: Optional[str],
    *,
    traces: list[dict],
    config: AppConfig | None,
    identity: dict | None,
    auth_context: object | None,
    secret_values: list[str] | None,
    error: Namel3ssError,
) -> dict:
    error_payload = build_error_from_exception(error, kind="runtime")
    response = build_run_payload(
        ok=False,
        flow_name=None,
        state=state,
        result=None,
        traces=traces,
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
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


__all__ = ["handle_upload_replace_action"]
