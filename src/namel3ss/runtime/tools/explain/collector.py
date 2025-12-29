from __future__ import annotations

from collections import defaultdict, deque

from .decision import ToolDecision, ToolEffect, ToolIntent, ToolPermission


def collect_tool_decisions(*, execution_last: dict | None, run_payload: dict | None) -> list[ToolDecision]:
    if not run_payload:
        return []
    steps = _steps(execution_last)
    steps_by_tool = _steps_by_tool(steps)
    flow_name = _flow_name(execution_last, run_payload)
    pending_checks: dict[str, list[dict]] = defaultdict(list)
    decisions: list[ToolDecision] = []
    counter = 0

    for trace in run_payload.get("traces") or []:
        if not isinstance(trace, dict):
            continue
        trace_type = trace.get("type")
        if trace_type == "capability_check":
            tool_name = trace.get("tool_name")
            if tool_name:
                pending_checks[str(tool_name)].append(trace)
            continue
        if trace_type != "tool_call":
            continue
        tool_name = _tool_name(trace)
        checks = pending_checks.pop(tool_name, [])
        step = _pop_step(steps_by_tool, tool_name)
        counter += 1
        decisions.append(
            _decision_from_trace(
                trace=trace,
                checks=checks,
                step=step,
                flow_name=flow_name,
                decision_id=_decision_id(counter),
            )
        )
    return decisions


def _steps(execution_last: dict | None) -> list[dict]:
    if not execution_last:
        return []
    steps = execution_last.get("execution_steps") or []
    return [step for step in steps if isinstance(step, dict)]


def _flow_name(execution_last: dict | None, run_payload: dict | None) -> str | None:
    flow = None
    if execution_last:
        flow = execution_last.get("flow_name")
    if not flow and run_payload:
        flow = run_payload.get("flow_name")
    return str(flow) if flow else None


def _steps_by_tool(steps: list[dict]) -> dict[str, deque]:
    by_tool: dict[str, deque] = defaultdict(deque)
    for step in steps:
        if step.get("kind") != "tool_call":
            continue
        tool_name = _step_tool_name(step)
        if tool_name:
            by_tool[tool_name].append(step)
    return by_tool


def _step_tool_name(step: dict) -> str | None:
    data = step.get("data")
    if isinstance(data, dict) and data.get("tool_name"):
        return str(data.get("tool_name"))
    what = step.get("what")
    if isinstance(what, str) and what.startswith("called tool "):
        return what.replace("called tool ", "", 1).strip()
    return None


def _pop_step(steps_by_tool: dict[str, deque], tool_name: str) -> dict | None:
    queue = steps_by_tool.get(tool_name)
    if not queue:
        return None
    if queue:
        return queue.popleft()
    return None


def _decision_from_trace(
    *,
    trace: dict,
    checks: list[dict],
    step: dict | None,
    flow_name: str | None,
    decision_id: str,
) -> ToolDecision:
    tool_name = _tool_name(trace)
    intent = ToolIntent(
        what=_intent_what(step, tool_name),
        because=step.get("because") if step else None,
        flow_name=flow_name,
        step_id=step.get("id") if step else None,
    )
    permission = _permission_from_checks(checks, trace)
    effect = ToolEffect(
        duration_ms=_int_or_none(trace.get("duration_ms")),
        input_summary=_coerce_str(trace.get("input_summary")),
        output_summary=_coerce_str(trace.get("output_summary")),
        error_type=_coerce_str(trace.get("error_type")),
        error_message=_coerce_str(trace.get("error_message")),
    )
    details = _details_from_trace(trace)
    status = _status_from_trace(trace, checks)
    return ToolDecision(
        id=decision_id,
        tool_name=tool_name,
        status=status,
        intent=intent,
        permission=permission,
        effect=effect,
        details=details,
    )


def _tool_name(trace: dict) -> str:
    tool_name = trace.get("tool_name") or trace.get("tool") or "unknown"
    return str(tool_name)


def _intent_what(step: dict | None, tool_name: str) -> str:
    if step and step.get("what"):
        return str(step.get("what"))
    return f"called tool {tool_name}"


def _permission_from_checks(checks: list[dict], trace: dict) -> ToolPermission:
    allowed_flags = [check.get("allowed") for check in checks if isinstance(check.get("allowed"), bool)]
    allowed = None
    if allowed_flags:
        allowed = all(allowed_flags)
    reasons = _reason_list(checks, allowed)
    capabilities_used = _capabilities_used(checks)
    unsafe_override = bool(trace.get("unsafe_override", False))
    return ToolPermission(
        allowed=allowed,
        reasons=reasons,
        capabilities_used=capabilities_used,
        unsafe_override=unsafe_override,
    )


def _status_from_trace(trace: dict, checks: list[dict]) -> str:
    status = trace.get("status") or "ok"
    if status == "error":
        if _has_denied(checks) or trace.get("error_type") == "CapabilityViolation":
            return "blocked"
        return "error"
    return str(status)


def _has_denied(checks: list[dict]) -> bool:
    return any(check.get("allowed") is False for check in checks if isinstance(check, dict))


def _reason_list(checks: list[dict], allowed: bool | None) -> list[str]:
    reasons: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        reason = check.get("reason")
        capability = check.get("capability")
        if reason:
            label = str(reason)
            if capability:
                label = f"{capability}: {label}"
            if label not in reasons:
                reasons.append(label)
    if not reasons and allowed is True:
        reasons.append("allowed by capability policy")
    return reasons


def _capabilities_used(checks: list[dict]) -> list[str]:
    names: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        capability = check.get("capability")
        if capability and capability not in names:
            names.append(str(capability))
    return names


def _details_from_trace(trace: dict) -> dict:
    keys = [
        "runner",
        "resolved_source",
        "entry",
        "service_url",
        "image",
        "command",
        "container_enforcement",
        "pack_id",
        "pack_name",
        "pack_version",
        "timeout_ms",
    ]
    details = {key: trace[key] for key in keys if key in trace}
    return details


def _decision_id(counter: int) -> str:
    return f"tool:{counter:04d}"


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


__all__ = ["collect_tool_decisions"]
