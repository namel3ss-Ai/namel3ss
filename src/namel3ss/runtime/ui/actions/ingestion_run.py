from __future__ import annotations

from typing import Optional
from types import SimpleNamespace

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.api import run_ingestion_progressive
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
from namel3ss.runtime.backend.job_queue import run_job_queue
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
        policy_decl=getattr(program_ir, "policy", None),
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
    job_traces: list[dict] = []
    job_ctx = _build_job_context(program_ir, state, job_traces, config=config)
    result = run_ingestion_progressive(
        upload_id=str(upload_id) if isinstance(upload_id, str) else "",
        mode=str(mode) if isinstance(mode, str) else None,
        state=state,
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        secret_values=secret_values,
        job_ctx=job_ctx,
        config=config,
    )
    report = result["report"]
    traces.extend(_build_traces(report))
    run_job_queue(job_ctx)
    if job_traces:
        traces.extend(job_traces)
    if isinstance(upload_id, str):
        report = state.get("ingestion", {}).get(upload_id, report)
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
    provenance = report.get("provenance") if isinstance(report.get("provenance"), dict) else {}
    source_name = provenance.get("source_name") if isinstance(provenance, dict) else None
    traces = [
        {
            "type": TraceEventType.INGESTION_STARTED,
            "upload_id": upload_id,
            "method": method_used,
            "detected": detected,
            "source_name": source_name,
        },
    ]
    traces.extend(_progress_traces(report))
    traces.append(
        {
            "type": TraceEventType.INGESTION_QUALITY_GATE,
            "upload_id": upload_id,
            "status": status,
            "reasons": reasons,
            "source_name": source_name,
        }
    )
    return traces


def _progress_traces(report: dict) -> list[dict]:
    events = report.get("progress")
    if not isinstance(events, list):
        return []
    traces: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        trace = {
            "type": TraceEventType.INGESTION_PROGRESS,
            "title": event.get("title"),
            "upload_id": event.get("upload_id"),
            "source_name": event.get("source_name"),
            "ingestion_phase": event.get("phase"),
        }
        if "status" in event:
            trace["status"] = event.get("status")
        traces.append(trace)
    return traces


def _build_job_context(program_ir, state: dict, traces: list[dict], *, config: AppConfig | None) -> SimpleNamespace:
    return SimpleNamespace(
        job_queue=[],
        job_enqueue_counter=0,
        traces=traces,
        execution_steps=[],
        execution_step_counter=0,
        jobs={},
        job_order=[],
        observability=None,
        state=state,
        config=config,
        capabilities=getattr(program_ir, "capabilities", ()) or (),
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
    )


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
