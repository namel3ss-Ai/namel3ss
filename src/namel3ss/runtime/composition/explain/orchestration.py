from __future__ import annotations

from namel3ss.traces.schema import TraceEventType

from namel3ss.runtime.composition.explain.bounds import (
    MAX_BRANCHES,
    MAX_MERGE_DETAILS,
    MAX_ORCHESTRATIONS,
    _apply_limit,
)
from namel3ss.runtime.composition.explain.redaction import _safe_text, _string


def _build_orchestration_summary(traces: list[dict]) -> dict:
    runs: dict[str, dict] = {}
    order: list[str] = []
    branch_index: dict[str, dict] = {}

    for trace in traces:
        trace_type = trace.get("type")
        if trace_type == TraceEventType.ORCHESTRATION_BRANCH_STARTED:
            branch_id = _string(trace.get("branch_id")) or ""
            key = _orchestration_key_from_branch(branch_id)
            run = _get_orchestration_run(runs, order, key)
            branch = {
                "branch_id": branch_id,
                "branch_name": _string(trace.get("branch_name")) or "",
                "call_kind": _string(trace.get("call_kind")) or "",
                "call_target": _string(trace.get("call_target")) or "",
                "status": "running",
            }
            run["branches"].append(branch)
            branch_index[branch_id] = branch
            continue
        if trace_type == TraceEventType.ORCHESTRATION_BRANCH_FINISHED:
            branch_id = _string(trace.get("branch_id")) or ""
            branch = branch_index.get(branch_id)
            if branch is None:
                key = _orchestration_key_from_branch(branch_id)
                run = _get_orchestration_run(runs, order, key)
                branch = {
                    "branch_id": branch_id,
                    "branch_name": _string(trace.get("branch_name")) or "",
                    "call_kind": "",
                    "call_target": "",
                    "status": "unknown",
                }
                run["branches"].append(branch)
                branch_index[branch_id] = branch
            status = trace.get("status")
            branch["status"] = status if isinstance(status, str) and status else "unknown"
            error_message = trace.get("error_message")
            if isinstance(error_message, str) and error_message:
                branch["error_message"] = _safe_text(error_message)
            continue
        if trace_type == TraceEventType.ORCHESTRATION_MERGE_STARTED:
            merge_id = _string(trace.get("merge_id")) or ""
            key = _orchestration_key_from_merge(merge_id)
            run = _get_orchestration_run(runs, order, key)
            policy = _string(trace.get("policy")) or ""
            run["merge"] = {
                "merge_id": merge_id,
                "policy": policy,
                "status": "running",
            }
            continue
        if trace_type == TraceEventType.ORCHESTRATION_MERGE_FINISHED:
            merge_id = _string(trace.get("merge_id")) or ""
            key = _orchestration_key_from_merge(merge_id)
            run = _get_orchestration_run(runs, order, key)
            merge = run.get("merge") or {
                "merge_id": merge_id,
                "policy": _string(trace.get("policy")) or "",
                "status": "unknown",
            }
            status = trace.get("status")
            merge["status"] = status if isinstance(status, str) and status else "unknown"
            selected = trace.get("selected")
            if isinstance(selected, str) and selected:
                merge["selected"] = selected
            decision = trace.get("decision") if isinstance(trace.get("decision"), dict) else None
            if decision:
                merge.update(_summarize_merge_decision(decision))
            error_message = trace.get("error_message")
            if isinstance(error_message, str) and error_message:
                merge["error_message"] = _safe_text(error_message)
            run["merge"] = merge
            continue

    ordered_runs = [runs[key] for key in order]
    limited_runs, truncated = _apply_limit(ordered_runs, MAX_ORCHESTRATIONS)
    for run in limited_runs:
        branches = run.get("branches") or []
        limited_branches, branch_truncated = _apply_limit(list(branches), MAX_BRANCHES)
        run["branches"] = limited_branches
        run["branch_total"] = len(branches)
        run["branches_truncated"] = branch_truncated
    return {
        "runs": limited_runs,
        "total_runs": len(ordered_runs),
        "runs_truncated": truncated,
    }


def _summarize_merge_decision(decision: dict) -> dict:
    summary = {
        "policy": _string(decision.get("policy")) or "",
        "status": _string(decision.get("status")) or "",
    }
    selected = decision.get("selected")
    if isinstance(selected, str) and selected:
        summary["selected"] = selected
    reason = decision.get("reason")
    if isinstance(reason, str) and reason:
        summary["reason"] = _safe_text(reason)
    failed = decision.get("failed")
    if isinstance(failed, list):
        summary["failed"] = [str(item) for item in failed]
    precedence = decision.get("precedence")
    if isinstance(precedence, list):
        summary["precedence"] = [str(item) for item in precedence]
    branches = decision.get("branches")
    if isinstance(branches, list):
        items = [
            {
                "name": _string(item.get("name")) or "",
                "status": _string(item.get("status")) or "",
                "summary": _string(item.get("summary")) or "",
                "error_type": _string(item.get("error_type")) or "",
                "error_message": _safe_text(item.get("error_message")) if isinstance(item.get("error_message"), str) else None,
            }
            for item in branches
            if isinstance(item, dict)
        ]
        limited, truncated = _apply_limit(items, MAX_MERGE_DETAILS)
        summary["branches"] = limited
        summary["branches_total"] = len(items)
        summary["branches_truncated"] = truncated
    return summary


def _orchestration_key_from_branch(branch_id: str) -> str:
    parts = branch_id.split(":") if branch_id else []
    if len(parts) >= 3 and parts[0] == "branch":
        return f"{parts[1]}:{parts[2]}"
    return "unknown"


def _orchestration_key_from_merge(merge_id: str) -> str:
    parts = merge_id.split(":") if merge_id else []
    if len(parts) >= 3 and parts[0] == "merge":
        return f"{parts[1]}:{parts[2]}"
    return "unknown"


def _get_orchestration_run(runs: dict[str, dict], order: list[str], key: str) -> dict:
    if key not in runs:
        runs[key] = {
            "orchestration_id": key,
            "branches": [],
            "merge": None,
        }
        order.append(key)
    return runs[key]
