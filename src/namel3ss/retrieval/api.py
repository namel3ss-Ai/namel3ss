from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.normalize import sanitize_text
from typing import TYPE_CHECKING

from namel3ss.ingestion.policy import (
    ACTION_RETRIEVAL_INCLUDE_WARN,
    PolicyDecision,
    evaluate_ingestion_policy,
    load_ingestion_policy,
)

if TYPE_CHECKING:
    from namel3ss.observability.context import ObservabilityContext


def run_retrieval(
    *,
    query: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    limit: int | None = None,
    secret_values: list[str] | None = None,
    identity: dict | None = None,
    policy_decision: PolicyDecision | None = None,
    policy_decl: object | None = None,
    observability: ObservabilityContext | None = None,
) -> dict:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    obs = observability
    span_id = None
    span_status = "ok"
    query_text = _normalize_query(query)
    if obs:
        span_id = obs.start_span(
            None,
            name="retrieval:run",
            kind="retrieval",
            details={"query_length": len(query_text)},
            timing_name="retrieval",
            timing_labels={"scope": "retrieval"},
        )
        obs.metrics.add("errors", value=0, labels={"scope": "retrieval"})
        obs.metrics.add("retries", value=0, labels={"scope": "retrieval"})
    try:
        entries = _read_index_entries(state)
        status_map = _read_ingestion_status(state)
        pass_entries: list[dict] = []
        warn_entries: list[dict] = []
        blocked = 0
        accept_summary = {"query_length": len(query_text), "limit": limit}
        _record_stage(obs, span_id, "retrieval:accept", accept_summary)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            text = entry.get("text")
            text_value = text if isinstance(text, str) else ""
            if query_text and query_text not in text_value.lower():
                continue
            upload_id = str(entry.get("upload_id") or "")
            quality = _quality_for_upload(status_map, upload_id)
            if quality == "block":
                blocked += 1
                continue
            chunk_id = entry.get("chunk_id")
            clean_text = sanitize_text(
                text_value,
                project_root=project_root,
                app_path=app_path,
                secret_values=secret_values,
            )
            result = {
                "upload_id": upload_id,
                "chunk_id": str(chunk_id or f"{upload_id}:{entry.get('order')}"),
                "quality": quality,
                "low_quality": quality == "warn",
                "text": clean_text,
            }
            if quality == "pass":
                pass_entries.append(result)
            else:
                warn_entries.append(result)
        decision = policy_decision or _resolve_warn_policy(
            project_root=project_root,
            app_path=app_path,
            identity=identity,
            policy_decl=policy_decl,
        )
        warn_allowed = bool(decision.allowed)
        excluded_warn = 0
        if pass_entries:
            results = pass_entries
            included_warn = False
            preferred = "pass"
        elif warn_allowed:
            results = warn_entries
            included_warn = bool(warn_entries)
            preferred = "warn" if warn_entries else "pass"
        else:
            results = []
            included_warn = False
            preferred = "pass"
            excluded_warn = len(warn_entries)
        select_summary = {
            "excluded_blocked": blocked,
            "excluded_warn": excluded_warn,
            "warn_allowed": warn_allowed,
        }
        _record_stage(obs, span_id, "retrieval:select_sources", select_summary)
        retrieve_summary = {"matched_results": len(results)}
        _record_stage(obs, span_id, "retrieval:retrieve", retrieve_summary)
        rank_summary = {"ordering": "index_order", "tie_break": "ingestion_order"}
        _record_stage(obs, span_id, "retrieval:rank", rank_summary)
        shape_summary = {"result_count": len(results), "schema_keys": _result_schema_keys(results)}
        _record_stage(obs, span_id, "retrieval:shape", shape_summary)
        report_summary = {"preferred_quality": preferred, "included_warn": included_warn}
        _record_stage(obs, span_id, "retrieval:report", report_summary)
        if limit is not None:
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
                raise Namel3ssError(_limit_message())
            results = results[:limit]
        if obs:
            obs.record_event(
                event_kind="run",
                scope="retrieval",
                outcome="ok",
                identifiers={"query_length": len(query_text)},
                payload={
                    "result_count": len(results),
                    "limit": limit,
                    "preferred_quality": preferred,
                    "included_warn": included_warn,
                    "excluded_blocked": blocked,
                    "excluded_warn": excluded_warn,
                    "warn_allowed": warn_allowed,
                },
            )
            obs.metrics.increment("requests", labels={"scope": "retrieval", "outcome": "ok"})
        return {
            "query": query_text,
            "preferred_quality": preferred,
            "included_warn": included_warn,
            "excluded_blocked": blocked,
            "excluded_warn": excluded_warn,
            "warn_allowed": warn_allowed,
            "warn_policy": _policy_summary(decision),
            "results": results,
        }
    except Exception as err:
        span_status = "error"
        if obs:
            obs.record_event(
                event_kind="run",
                scope="retrieval",
                outcome="failed",
                identifiers={"query_length": len(query_text)},
                payload={
                    "error_kind": err.__class__.__name__,
                    "error_category": _error_category(err),
                },
            )
            obs.metrics.increment("requests", labels={"scope": "retrieval", "outcome": "failed"})
            obs.metrics.increment("errors", labels={"scope": "retrieval"})
        raise
    finally:
        if obs and span_id:
            obs.end_span(None, span_id, status=span_status)


def _normalize_query(query: str | None) -> str:
    if query is None:
        return ""
    if not isinstance(query, str):
        raise Namel3ssError(_query_message())
    return query.strip().lower()


def _read_index_entries(state: dict) -> list[dict]:
    index = state.get("index")
    if not isinstance(index, dict):
        return []
    entries = index.get("chunks")
    if not isinstance(entries, list):
        return []
    return entries


def _read_ingestion_status(state: dict) -> dict:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return {}
    return ingestion


def _quality_for_upload(status_map: dict, upload_id: str) -> str:
    if not upload_id:
        return "block"
    report = status_map.get(upload_id)
    if not isinstance(report, dict):
        return "block"
    status = report.get("status")
    if status in {"pass", "warn", "block"}:
        return status
    return "block"


def _resolve_warn_policy(
    *,
    project_root: str | None,
    app_path: str | None,
    identity: dict | None,
    policy_decl: object | None,
) -> PolicyDecision:
    policy = load_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    return evaluate_ingestion_policy(policy, ACTION_RETRIEVAL_INCLUDE_WARN, identity)


def _policy_summary(decision: PolicyDecision) -> dict:
    return {
        "action": ACTION_RETRIEVAL_INCLUDE_WARN,
        "decision": "allowed" if decision.allowed else "denied",
        "reason": decision.reason,
    }


def _result_schema_keys(results: list[dict]) -> list[str]:
    keys: set[str] = set()
    for entry in results:
        if isinstance(entry, dict):
            keys.update(str(key) for key in entry.keys())
    return sorted(keys)


def _record_stage(obs, parent_id: str | None, name: str, details: dict) -> None:
    if not obs:
        return
    span_id = obs.start_span(
        None,
        name=name,
        kind="retrieval_stage",
        details=details,
        parent_id=parent_id,
    )
    obs.end_span(None, span_id, status="ok")


def _error_category(err: Exception) -> str:
    if isinstance(err, Namel3ssError):
        details = err.details or {}
        category = str(details.get("category") or "").strip().lower()
        if category in {"input", "policy", "dependency", "internal"}:
            return category
        return "input"
    return "internal"


def _state_type_message() -> str:
    return build_guidance_message(
        what="State must be an object.",
        why="Retrieval reads indexed chunks and ingestion reports from state.",
        fix="Ensure state is a JSON object.",
        example='{"index":{"chunks":[]},"ingestion":{}}',
    )


def _query_message() -> str:
    return build_guidance_message(
        what="Retrieval query must be text.",
        why="Retrieval expects a text query or an empty string.",
        fix="Provide a string query.",
        example='{"query":"invoice"}',
    )


def _limit_message() -> str:
    return build_guidance_message(
        what="Retrieval limit must be a non-negative integer.",
        why="Retrieval limits the number of returned chunks deterministically.",
        fix="Provide a number like 10.",
        example='{"limit":10}',
    )


__all__ = ["run_retrieval"]
