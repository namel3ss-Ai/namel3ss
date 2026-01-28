from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_orchestration_branch_started(
    *,
    branch_name: str,
    branch_id: str,
    call_kind: str,
    call_target: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.ORCHESTRATION_BRANCH_STARTED,
        "trace_version": TRACE_VERSION,
        "branch_name": branch_name,
        "branch_id": branch_id,
        "call_kind": call_kind,
        "call_target": call_target,
        "title": title,
        "lines": list(lines),
    }


def build_orchestration_branch_finished(
    *,
    branch_name: str,
    branch_id: str,
    status: str,
    title: str,
    lines: list[str],
    error_message: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.ORCHESTRATION_BRANCH_FINISHED,
        "trace_version": TRACE_VERSION,
        "branch_name": branch_name,
        "branch_id": branch_id,
        "status": status,
        "title": title,
        "lines": list(lines),
    }
    if error_message:
        event["error_message"] = error_message
    return event


def build_orchestration_merge_started(
    *,
    merge_id: str,
    policy: str,
    title: str,
    lines: list[str],
) -> dict:
    return {
        "type": TraceEventType.ORCHESTRATION_MERGE_STARTED,
        "trace_version": TRACE_VERSION,
        "merge_id": merge_id,
        "policy": policy,
        "title": title,
        "lines": list(lines),
    }


def build_orchestration_merge_finished(
    *,
    merge_id: str,
    policy: str,
    status: str,
    title: str,
    lines: list[str],
    selected: str | None = None,
    decision: dict | None = None,
    error_message: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.ORCHESTRATION_MERGE_FINISHED,
        "trace_version": TRACE_VERSION,
        "merge_id": merge_id,
        "policy": policy,
        "status": status,
        "title": title,
        "lines": list(lines),
    }
    if selected:
        event["selected"] = selected
    if decision:
        event["decision"] = dict(decision)
    if error_message:
        event["error_message"] = error_message
    return event


__all__ = [
    "build_orchestration_branch_started",
    "build_orchestration_branch_finished",
    "build_orchestration_merge_started",
    "build_orchestration_merge_finished",
]
