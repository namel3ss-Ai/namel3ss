from __future__ import annotations

from typing import Optional

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import (
    ACTION_RETRIEVAL_INCLUDE_WARN,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_trace,
)
from namel3ss.production_contract import build_run_payload
from namel3ss.retrieval.api import run_retrieval
from namel3ss.runtime.retrieval.trace_collector import diagnostics_trace_enabled
from namel3ss.runtime.run_pipeline import finalize_run_payload
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.ui.actions.validation.validate import ensure_json_serializable
from namel3ss.traces.schema import TraceEventType
from namel3ss.ui.manifest import build_manifest


def handle_retrieval_run_action(
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
    query = payload.get("query")
    limit = payload.get("limit")
    tier = payload.get("tier")
    filter_tags = payload.get("filter_tags")
    capabilities = tuple(getattr(program_ir, "capabilities", ()) or ())
    policy = load_ingestion_policy(
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        policy_decl=getattr(program_ir, "policy", None),
    )
    decision = evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, identity)
    result = run_retrieval(
        query=query,
        limit=limit,
        tier=tier,
        filter_tags=filter_tags,
        state=state,
        project_root=getattr(program_ir, "project_root", None),
        app_path=getattr(program_ir, "app_path", None),
        secret_values=secret_values,
        identity=identity,
        policy_decision=decision,
        config=config,
        capabilities=capabilities,
        diagnostics_trace_enabled=diagnostics_trace_enabled(capabilities),
    )
    traces = [policy_trace(ACTION_RETRIEVAL_INCLUDE_WARN, decision)]
    traces.extend(_build_traces(result))
    response = build_run_payload(
        ok=True,
        flow_name=None,
        state=state,
        result={"retrieval": result},
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


def _build_traces(result: dict) -> list[dict]:
    preferred = result.get("preferred_quality")
    included_warn = result.get("included_warn")
    excluded_blocked = result.get("excluded_blocked")
    warn_allowed = result.get("warn_allowed")
    excluded_warn = result.get("excluded_warn")
    warn_policy = result.get("warn_policy")
    tier = result.get("tier") if isinstance(result.get("tier"), dict) else {}
    traces = [
        {
            "type": TraceEventType.RETRIEVAL_STARTED,
        },
        {
            "type": TraceEventType.RETRIEVAL_TIER_SELECTED,
            "tier": tier.get("requested"),
            "selected": tier.get("selected"),
            "reason": tier.get("reason"),
            "available": tier.get("available"),
            "counts": tier.get("counts"),
        },
        {
            "type": TraceEventType.RETRIEVAL_QUALITY_POLICY,
            "preferred": preferred,
            "included_warn": included_warn,
            "excluded_blocked": excluded_blocked,
            "warn_allowed": warn_allowed,
            "excluded_warn": excluded_warn,
            "warn_policy": warn_policy,
        },
    ]
    retrieval_plan = result.get("retrieval_plan")
    if isinstance(retrieval_plan, dict):
        traces.append(
            {
                "type": TraceEventType.RETRIEVAL_PLAN,
                "retrieval_plan": retrieval_plan,
            }
        )
    retrieval_trace = result.get("retrieval_trace")
    if isinstance(retrieval_trace, list):
        traces.append(
            {
                "type": TraceEventType.RETRIEVAL_TRACE,
                "retrieval_trace": [entry for entry in retrieval_trace if isinstance(entry, dict)],
            }
        )
    trust_score_details = result.get("trust_score_details")
    if isinstance(trust_score_details, dict):
        traces.append(
            {
                "type": TraceEventType.TRUST_SCORE_COMPUTED,
                "trust_score_details": trust_score_details,
            }
        )
    return traces


def _require_uploads_capability(program_ir) -> None:
    caps = getattr(program_ir, "capabilities", ()) or ()
    if "uploads" in caps:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Retrieval runs on ingested uploads and requires the uploads capability.",
            fix="Add uploads to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


def _payload_type_message() -> str:
    return build_guidance_message(
        what="Retrieval payload must be an object.",
        why="Retrieval expects an object with query, optional limit, and optional tier.",
        fix='Send {"query":"..."} or include {"limit":10,"tier":"auto"}.',
        example='{"query":"invoice","limit":5,"tier":"auto"}',
    )


__all__ = ["handle_retrieval_run_action"]
