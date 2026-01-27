from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.api import run_ingestion
from namel3ss.ingestion.policy import (
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_RUN,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_error,
    policy_trace,
)
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validate import ensure_json_serializable
from namel3ss.traces.schema import TraceEventType
from namel3ss.ui.manifest import build_manifest


def handle_ingestion_run_action(
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
    mode = payload.get("mode")
    policy = load_ingestion_policy(
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_INGESTION_RUN, identity)
    traces = [policy_trace(ACTION_INGESTION_RUN, decision)]
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
            error=policy_error(ACTION_INGESTION_RUN, decision),
        )
    mode_value = mode.strip().lower() if isinstance(mode, str) else ""
    if mode_value in {"layout", "ocr"}:
        override = evaluate_ingestion_policy(policy, ACTION_INGESTION_OVERRIDE, identity)
        traces.append(policy_trace(ACTION_INGESTION_OVERRIDE, override))
        if not override.allowed:
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
                error=policy_error(ACTION_INGESTION_OVERRIDE, override, mode=mode_value),
            )
    result = run_ingestion(
        upload_id=str(upload_id) if isinstance(upload_id, str) else "",
        mode=str(mode) if isinstance(mode, str) else None,
        state=state,
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        secret_values=secret_values,
    )
    report = result["report"]
    traces.extend(_build_traces(report))
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"ingestion": report},
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


def _build_traces(report: dict) -> list[dict]:
    upload_id = report.get("upload_id")
    detected = report.get("detected")
    method_used = report.get("method_used")
    status = report.get("status")
    reasons = report.get("reasons")
    traces = [
        {
            "type": TraceEventType.INGESTION_STARTED,
            "upload_id": upload_id,
            "method": method_used,
            "detected": detected,
        },
        {
            "type": TraceEventType.INGESTION_QUALITY_GATE,
            "upload_id": upload_id,
            "status": status,
            "reasons": reasons,
        },
    ]
    return traces


def _require_uploads_capability(program_ir) -> None:
    caps = getattr(program_ir, "capabilities", ()) or ()
    if "uploads" in caps:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Ingestion runs on uploaded files and requires the uploads capability.",
            fix="Add uploads to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Ingestion payload must be an object.",
        why="Ingestion expects upload_id and optional mode in a JSON object.",
        fix='Send {"upload_id":"<checksum>"} or include {"mode":"primary"}',
        example='{"upload_id":"<checksum>","mode":"primary"}',
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


__all__ = ["handle_ingestion_run_action"]
