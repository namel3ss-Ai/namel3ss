from __future__ import annotations

from namel3ss.runtime.execution.normalize import summarize_value
from namel3ss.runtime.executor.orchestration.merge import OrchestrationBranchResult, OrchestrationMergeOutcome
from namel3ss.traces.builders import (
    build_orchestration_branch_finished,
    build_orchestration_branch_started,
    build_orchestration_merge_finished,
    build_orchestration_merge_started,
)


_BRACKET_CHARS = str.maketrans({")": " ", "(": " ", "]": " ", "[": " ", "}": " ", "{": " "})


def build_orchestration_branch_started_event(
    *,
    branch_name: str,
    branch_id: str,
    call_kind: str,
    call_target: str,
) -> dict:
    lines = [
        f"Branch {branch_name} started.",
        f"Call {call_kind} {call_target}.",
    ]
    return build_orchestration_branch_started(
        branch_name=_sanitize(branch_name),
        branch_id=branch_id,
        call_kind=_sanitize(call_kind),
        call_target=_sanitize(call_target),
        title="Orchestration branch started",
        lines=[_sanitize(line) for line in lines],
    )


def build_orchestration_branch_finished_event(
    *,
    branch_id: str,
    result: OrchestrationBranchResult,
    summary: str,
) -> dict:
    if result.status == "ok":
        lines = [
            f"Branch {result.name} finished.",
            f"Result summary: {summary}.",
        ]
        return build_orchestration_branch_finished(
            branch_name=_sanitize(result.name),
            branch_id=branch_id,
            status="ok",
            title="Orchestration branch finished",
            lines=[_sanitize(line) for line in lines],
        )
    lines = [
        f"Branch {result.name} failed.",
        f"Error: {result.error_message or 'Unknown error.'}.",
    ]
    return build_orchestration_branch_finished(
        branch_name=_sanitize(result.name),
        branch_id=branch_id,
        status="error",
        title="Orchestration branch finished",
        lines=[_sanitize(line) for line in lines],
        error_message=_sanitize(result.error_message or "Unknown error."),
    )


def build_orchestration_merge_started_event(
    *,
    merge_id: str,
    policy: str,
    branches: list[OrchestrationBranchResult],
) -> dict:
    branch_names = ", ".join(branch.name for branch in branches)
    lines = [
        f"Policy is {policy}.",
        f"Branches: {branch_names}." if branch_names else "Branches: none.",
    ]
    return build_orchestration_merge_started(
        merge_id=merge_id,
        policy=_sanitize(policy),
        title="Orchestration merge started",
        lines=[_sanitize(line) for line in lines],
    )


def build_orchestration_merge_finished_event(
    *,
    merge_id: str,
    outcome: OrchestrationMergeOutcome,
) -> dict:
    lines = [f"Policy is {outcome.policy}."]
    if outcome.selected:
        lines.append(f"Selected {outcome.selected}.")
    lines.append(outcome.reason)
    for branch in outcome.branches:
        if branch.status == "ok":
            summary = _safe_summary(branch.value)
            lines.append(f"Branch {branch.name} ok: {summary}.")
        else:
            lines.append(f"Branch {branch.name} error: {branch.error_type or 'Error'}.")
    decision = _decision_payload(outcome)
    return build_orchestration_merge_finished(
        merge_id=merge_id,
        policy=_sanitize(outcome.policy),
        status=outcome.status,
        title="Orchestration merge finished",
        lines=[_sanitize(line) for line in lines],
        selected=_sanitize(outcome.selected) if outcome.selected else None,
        decision=decision,
        error_message=_sanitize(outcome.reason) if outcome.status != "ok" else None,
    )


def _decision_payload(outcome: OrchestrationMergeOutcome) -> dict:
    return {
        "policy": _sanitize(outcome.policy),
        "status": outcome.status,
        "selected": _sanitize(outcome.selected) if outcome.selected else None,
        "failed": [_sanitize(name) for name in outcome.failed],
        "precedence": [_sanitize(name) for name in outcome.precedence] if outcome.precedence else None,
        "reason": _sanitize(outcome.reason),
        "branches": [
            {
                "name": _sanitize(branch.name),
                "status": branch.status,
                "summary": _sanitize(_safe_summary(branch.value)) if branch.status == "ok" else None,
                "error_type": _sanitize(branch.error_type) if branch.error_type else None,
                "error_message": _sanitize(branch.error_message) if branch.error_message else None,
            }
            for branch in outcome.branches
        ],
    }


def _safe_summary(value: object) -> str:
    if isinstance(value, str):
        return f"text length {len(value)}"
    return summarize_value(value)


def _sanitize(value: object) -> str:
    text = "" if value is None else str(value)
    sanitized = text.translate(_BRACKET_CHARS)
    return " ".join(sanitized.split()).strip()


__all__ = [
    "build_orchestration_branch_started_event",
    "build_orchestration_branch_finished_event",
    "build_orchestration_merge_started_event",
    "build_orchestration_merge_finished_event",
]
