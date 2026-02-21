from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import (
    ACTION_INGESTION_REVIEW,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_error,
    policy_trace,
)
from namel3ss.ingestion.review import build_ingestion_review
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.traces.schema import TraceEventType
from namel3ss.ui.manifest import build_manifest
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_STUDIO


def handle_ingestion_review_action(
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
    ui_mode: str = DISPLAY_MODE_STUDIO,
    diagnostics_enabled: bool = False,
) -> dict:
    _require_uploads_capability(program_ir)
    if not isinstance(payload, dict):
        raise Namel3ssError(_payload_type_message())
    policy = load_ingestion_policy(
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        policy_decl=getattr(program_ir, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_INGESTION_REVIEW, identity)
    traces = [policy_trace(ACTION_INGESTION_REVIEW, decision)]
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
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
            error=policy_error(ACTION_INGESTION_REVIEW, decision),
        )
    upload_id = payload.get("upload_id")
    review = build_ingestion_review(
        state,
        upload_id=upload_id if isinstance(upload_id, str) else None,
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        secret_values=secret_values,
    )
    reports = review.get("reports") if isinstance(review, dict) else []
    traces.extend(
        [
        {
            "type": TraceEventType.INGESTION_REVIEWED,
            "count": len(reports) if isinstance(reports, list) else 0,
        }
        ]
    )
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"ingestion_review": review},
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
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
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
            why="Ingestion review inspects uploaded content.",
            fix="Add uploads to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Ingestion review payload must be an object.",
        why="Ingestion review expects an optional upload_id.",
        fix='Send {} or {"upload_id":"<checksum>"}.',
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
    ui_mode: str,
    diagnostics_enabled: bool,
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
        display_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    ensure_json_serializable(response)
    response = finalize_run_payload(response, secret_values)
    return response


__all__ = ["handle_ingestion_review_action"]
