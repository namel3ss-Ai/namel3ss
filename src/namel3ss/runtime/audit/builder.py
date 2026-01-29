from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from namel3ss.ingestion.policy import (
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_REVIEW,
    ACTION_INGESTION_RUN,
    ACTION_INGESTION_SKIP,
    ACTION_RETRIEVAL_INCLUDE_WARN,
    ACTION_UPLOAD_REPLACE,
    PolicyDecision,
    evaluate_ingestion_policy,
    load_ingestion_policy,
)
from namel3ss.ingestion.policy_inspection import inspect_ingestion_policy
from namel3ss.runtime.auth.identity_model import build_identity_summary
from namel3ss.traces.schema import TraceEventType
from namel3ss.utils.path_display import display_path_hint

from .model import DecisionModel, DecisionStep
from .retrieval import build_retrieval_step


_POLICY_ACTIONS = [
    ACTION_INGESTION_RUN,
    ACTION_INGESTION_OVERRIDE,
    ACTION_INGESTION_REVIEW,
    ACTION_INGESTION_SKIP,
    ACTION_RETRIEVAL_INCLUDE_WARN,
    ACTION_UPLOAD_REPLACE,
]


def build_decision_model(
    *,
    state: dict | None,
    traces: Iterable[dict] | None,
    project_root: str | Path | None,
    app_path: str | Path | None,
    policy_decl: object | None,
    identity: dict | None,
    upload_id: str | None,
    query: str | None,
    secret_values: list[str] | None = None,
) -> DecisionModel:
    state_value = _safe_state(state)
    trace_items = _safe_traces(traces)
    identity_summary = build_identity_summary(identity)

    policy_info = inspect_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    policy = load_ingestion_policy(project_root, app_path, policy_decl=policy_decl)
    policy_rules = _policy_rule_map(policy_info)
    trace_policy = _policy_trace_outcomes(trace_items)

    inputs = _build_inputs(
        project_root=project_root,
        app_path=app_path,
        identity=identity_summary,
        upload_id=upload_id,
        query=query,
        state=state_value,
    )

    decisions: list[DecisionStep] = []
    decisions.extend(_upload_decisions(state_value, upload_id))
    decisions.extend(_upload_trace_decisions(trace_items, upload_id))
    decisions.extend(_ingestion_decisions(state_value, upload_id))
    decisions.extend(_review_decisions(state_value, trace_items, upload_id))

    policy_steps, policy_decisions = _policy_decisions(
        policy,
        policy_rules,
        trace_policy,
        identity,
    )
    decisions.extend(policy_steps)

    retrieval_step, retrieval_outcome = build_retrieval_step(
        state_value,
        policy_decisions.get(ACTION_RETRIEVAL_INCLUDE_WARN),
        policy_rules.get(ACTION_RETRIEVAL_INCLUDE_WARN),
        query=query,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    if retrieval_step is not None:
        decisions.append(retrieval_step)

    outcomes = _build_outcomes(state_value, policy_decisions, retrieval_outcome, upload_id)
    return DecisionModel(inputs=inputs, decisions=decisions, policies=policy_info, outcomes=outcomes)


def _build_inputs(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    identity: dict,
    upload_id: str | None,
    query: str | None,
    state: dict,
) -> dict:
    payload: dict[str, object] = {}
    if app_path is not None:
        base = Path(project_root) if project_root else None
        payload["app"] = {"path": display_path_hint(app_path, base=base)}
    if identity:
        payload["identity"] = identity
    subject: dict[str, object] = {}
    if upload_id:
        subject["upload_id"] = upload_id
    if query is not None:
        subject["query"] = query
    if subject:
        payload["subject"] = subject
    payload["state"] = _state_summary(state)
    return payload


def _state_summary(state: dict) -> dict:
    uploads = state.get("uploads") if isinstance(state, dict) else None
    ingestion = state.get("ingestion") if isinstance(state, dict) else None
    index = state.get("index") if isinstance(state, dict) else None
    chunks = index.get("chunks") if isinstance(index, dict) else None
    return {
        "uploads": _count_upload_entries(uploads),
        "ingestion_reports": len(ingestion) if isinstance(ingestion, dict) else 0,
        "index_chunks": len(chunks) if isinstance(chunks, list) else 0,
    }


def _count_upload_entries(uploads: object) -> int:
    if not isinstance(uploads, dict):
        return 0
    total = 0
    for entry in uploads.values():
        if isinstance(entry, list):
            total += len(entry)
    return total


def _upload_decisions(state: dict, upload_id: str | None) -> list[DecisionStep]:
    uploads = state.get("uploads")
    if not isinstance(uploads, dict):
        return []
    steps: list[DecisionStep] = []
    for upload_name in sorted(uploads.keys(), key=lambda item: str(item)):
        entries = uploads.get(upload_name)
        if not isinstance(entries, list):
            continue
        for entry in sorted(entries, key=_upload_sort_key):
            if not isinstance(entry, dict):
                continue
            checksum = _upload_checksum(entry)
            if upload_id and checksum and checksum != upload_id:
                continue
            step_id = f"upload:{upload_name}:{checksum or 'unknown'}"
            inputs = {
                "upload_name": upload_name,
                "name": entry.get("name"),
                "size": entry.get("size"),
                "type": entry.get("type"),
                "checksum": checksum,
            }
            preview = entry.get("preview")
            if isinstance(preview, dict):
                inputs["preview"] = preview
            progress = entry.get("progress")
            if isinstance(progress, dict):
                inputs["progress"] = progress
            state_value = entry.get("state")
            if isinstance(state_value, str):
                inputs["state"] = state_value
            error = entry.get("error")
            if isinstance(error, dict):
                inputs["error"] = error
            steps.append(
                DecisionStep(
                    id=step_id,
                    category="upload",
                    subject=checksum,
                    inputs=inputs,
                    rules=["metadata recorded"],
                    outcome={"selected": True},
                )
            )
    return steps


_UPLOAD_TRACE_TYPES = {
    "upload_state",
    "upload_progress",
    "upload_preview",
    "upload_error",
    "upload_received",
    "upload_stored",
}


def _upload_trace_decisions(traces: list[dict], upload_id: str | None) -> list[DecisionStep]:
    steps: list[DecisionStep] = []
    for idx, trace in enumerate(traces, start=1):
        event_type = trace.get("type")
        if event_type not in _UPLOAD_TRACE_TYPES:
            continue
        subject = _trace_upload_id(trace)
        if upload_id:
            if subject is None or subject != upload_id:
                continue
        step_id = f"upload:event:{idx}:{event_type}"
        inputs = _upload_trace_inputs(trace)
        outcome = _upload_trace_outcome(trace)
        steps.append(
            DecisionStep(
                id=step_id,
                category="upload",
                subject=subject,
                inputs=inputs,
                rules=[event_type],
                outcome=outcome,
            )
        )
    return steps


def _trace_upload_id(trace: dict) -> str | None:
    for key in ("upload_id", "checksum"):
        value = trace.get(key)
        if isinstance(value, str) and value:
            return value
    preview = trace.get("preview")
    if isinstance(preview, dict):
        value = preview.get("checksum")
        if isinstance(value, str) and value:
            return value
    return None


def _upload_trace_inputs(trace: dict) -> dict:
    inputs: dict[str, object] = {}
    for key in (
        "name",
        "content_type",
        "bytes",
        "checksum",
        "stored_path",
        "state",
        "bytes_received",
        "total_bytes",
        "percent_complete",
    ):
        if key in trace:
            inputs[key] = trace.get(key)
    preview = trace.get("preview")
    if isinstance(preview, dict):
        inputs["preview"] = preview
    error = trace.get("error")
    if isinstance(error, dict):
        inputs["error"] = error
    return inputs


def _upload_trace_outcome(trace: dict) -> dict:
    event_type = trace.get("type")
    if event_type == "upload_state":
        state = trace.get("state")
        return {"state": state} if state else {}
    if event_type == "upload_progress":
        progress = trace.get("percent_complete")
        return {"progress": progress} if progress is not None else {}
    if event_type == "upload_preview":
        return {"preview": True}
    if event_type == "upload_error":
        error = trace.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        return {"error": code} if isinstance(code, str) and code else {}
    if event_type == "upload_received":
        return {"received": True}
    if event_type == "upload_stored":
        return {"stored": True}
    return {}


def _upload_sort_key(entry: object) -> tuple[str, str]:
    if not isinstance(entry, dict):
        return ("", "")
    name = str(entry.get("name") or "")
    checksum = _upload_checksum(entry)
    return (name, checksum or "")


def _upload_checksum(entry: dict) -> str | None:
    value = entry.get("checksum") or entry.get("id")
    if isinstance(value, str) and value:
        return value
    return None


def _ingestion_decisions(state: dict, upload_id: str | None) -> list[DecisionStep]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return []
    steps: list[DecisionStep] = []
    for uid in sorted(ingestion.keys(), key=lambda item: str(item)):
        report = ingestion.get(uid)
        if not isinstance(report, dict):
            continue
        uid_text = str(uid)
        if upload_id and uid_text != upload_id:
            continue
        reasons = _string_list(report.get("reasons"))
        rules = ["quality gate"] + reasons if reasons else ["quality gate"]
        inputs = {
            "upload_id": uid_text,
            "method_used": report.get("method_used"),
            "detected": report.get("detected"),
            "signals": report.get("signals"),
        }
        steps.append(
            DecisionStep(
                id=f"ingestion:{uid_text}",
                category="ingestion",
                subject=uid_text,
                inputs=inputs,
                rules=rules,
                outcome={"status": report.get("status")},
            )
        )
    return steps


def _review_decisions(state: dict, traces: list[dict], upload_id: str | None) -> list[DecisionStep]:
    steps: list[DecisionStep] = []
    review_events = _trace_events(traces, TraceEventType.INGESTION_REVIEWED)
    for idx, event in enumerate(review_events, start=1):
        steps.append(
            DecisionStep(
                id=f"review:ingestion_review:{idx}",
                category="review",
                subject=None,
                inputs={},
                rules=["review requested"],
                outcome={"status": "run", "count": event.get("count")},
            )
        )
    seen_skips: set[str] = set()
    skip_events = _trace_events(traces, TraceEventType.INGESTION_SKIPPED)
    for event in skip_events:
        uid = event.get("upload_id")
        if not isinstance(uid, str) or not uid:
            continue
        if upload_id and uid != upload_id:
            continue
        seen_skips.add(uid)
        steps.append(
            DecisionStep(
                id=f"review:ingestion_skip:{uid}",
                category="review",
                subject=uid,
                inputs={"upload_id": uid},
                rules=_string_list(event.get("reasons")),
                outcome={"status": "skipped", "quality": event.get("status")},
            )
        )
    replace_events = _trace_events(traces, TraceEventType.UPLOAD_REPLACE_REQUESTED)
    for event in replace_events:
        uid = event.get("upload_id")
        if not isinstance(uid, str) or not uid:
            continue
        if upload_id and uid != upload_id:
            continue
        steps.append(
            DecisionStep(
                id=f"review:upload_replace:{uid}",
                category="review",
                subject=uid,
                inputs={"upload_id": uid},
                rules=["replacement requested"],
                outcome={"status": "requested"},
            )
        )
    steps.extend(_inferred_skip_decisions(state, seen_skips, upload_id))
    return steps


def _inferred_skip_decisions(state: dict, seen_skips: set[str], upload_id: str | None) -> list[DecisionStep]:
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        return []
    steps: list[DecisionStep] = []
    for uid, report in ingestion.items():
        if not isinstance(report, dict):
            continue
        uid_text = str(uid)
        if upload_id and uid_text != upload_id:
            continue
        if uid_text in seen_skips:
            continue
        method_used = report.get("method_used")
        reasons = _string_list(report.get("reasons"))
        if method_used != "skip" and "skipped" not in reasons:
            continue
        steps.append(
            DecisionStep(
                id=f"review:ingestion_skip:{uid_text}",
                category="review",
                subject=uid_text,
                inputs={"upload_id": uid_text},
                rules=reasons or ["skipped"],
                outcome={"status": "skipped", "quality": report.get("status")},
            )
        )
    return steps


def _policy_decisions(
    policy,
    policy_rules: dict[str, dict],
    trace_policy: dict[str, dict],
    identity: dict | None,
) -> tuple[list[DecisionStep], dict[str, PolicyDecision]]:
    steps: list[DecisionStep] = []
    decisions: dict[str, PolicyDecision] = {}
    for action in _POLICY_ACTIONS:
        evaluated = evaluate_ingestion_policy(policy, action, identity)
        trace = trace_policy.get(action)
        decision = evaluated
        source = "policy"
        if trace is not None:
            allowed = trace.get("outcome") == "allowed"
            reason = trace.get("reason") or evaluated.reason
            decision = replace(evaluated, allowed=allowed, reason=reason, source="trace")
            source = "trace"
        decisions[action] = decision
        rule = policy_rules.get(action)
        required = list(decision.required_permissions)
        outcome = {
            "decision": "allowed" if decision.allowed else "denied",
            "reason": decision.reason,
            "required_permissions": required,
            "source": source,
        }
        inputs = {"action": action}
        rules = [rule] if rule else []
        steps.append(
            DecisionStep(
                id=f"policy:{action}",
                category="policy",
                subject=action,
                inputs=inputs,
                rules=rules,
                outcome=outcome,
            )
        )
    return steps, decisions


def _build_outcomes(
    state: dict,
    policy_decisions: dict[str, PolicyDecision],
    retrieval_outcome: dict | None,
    upload_id: str | None,
) -> dict:
    ingestion = state.get("ingestion")
    status_counts = {"pass": 0, "warn": 0, "block": 0}
    upload_status = None
    if isinstance(ingestion, dict):
        for uid, report in ingestion.items():
            if not isinstance(report, dict):
                continue
            status = report.get("status")
            if status in status_counts:
                status_counts[status] += 1
            if upload_id and str(uid) == upload_id:
                upload_status = status
    policy_denied = [
        action for action, decision in policy_decisions.items() if not decision.allowed
    ]
    outcomes: dict[str, object] = {
        "ingestion": {"counts": status_counts},
        "policy_denials": sorted(policy_denied),
    }
    if upload_status is not None:
        outcomes["ingestion"]["upload_status"] = upload_status
    if retrieval_outcome is not None:
        outcomes["retrieval"] = {
            "results": len(retrieval_outcome.get("results") or []),
            "preferred_quality": retrieval_outcome.get("preferred_quality"),
            "included_warn": retrieval_outcome.get("included_warn"),
            "excluded_blocked": retrieval_outcome.get("excluded_blocked"),
            "excluded_warn": retrieval_outcome.get("excluded_warn"),
        }
    return outcomes


def _policy_rule_map(policy_info: dict) -> dict[str, dict]:
    effective = policy_info.get("effective") if isinstance(policy_info, dict) else None
    if not isinstance(effective, list):
        return {}
    mapping: dict[str, dict] = {}
    for entry in effective:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        if isinstance(action, str) and action:
            mapping[action] = dict(entry)
    return mapping


def _policy_trace_outcomes(traces: list[dict]) -> dict[str, dict]:
    outcomes: dict[str, dict] = {}
    for trace in traces:
        if trace.get("type") != TraceEventType.AUTHORIZATION_CHECK:
            continue
        subject = trace.get("subject")
        if not isinstance(subject, str) or not subject.startswith("policy:"):
            continue
        action = subject.split("policy:", 1)[1]
        outcomes[action] = {
            "outcome": trace.get("outcome"),
            "reason": trace.get("reason"),
        }
    return outcomes


def _trace_events(traces: list[dict], event_type: str) -> list[dict]:
    return [trace for trace in traces if isinstance(trace, dict) and trace.get("type") == event_type]


def _safe_state(state: dict | None) -> dict:
    return state if isinstance(state, dict) else {}


def _safe_traces(traces: Iterable[dict] | None) -> list[dict]:
    items = list(traces or [])
    return [item for item in items if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


__all__ = ["build_decision_model"]
