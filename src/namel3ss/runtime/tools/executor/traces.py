from __future__ import annotations

from namel3ss.foreign.intent import foreign_language_label
from namel3ss.observe import summarize_value
from namel3ss.runtime.capabilities.gates import record_capability_check
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext, EffectiveGuarantees
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.tools.outcome import ToolDecision
from namel3ss.secrets import collect_secret_values, redact_text
from namel3ss.traces.schema import TraceEventType


def _record_tool_trace(
    ctx: ExecutionContext,
    tool_name: str,
    tool_kind: str | None,
    decision: ToolDecision,
    *,
    result: str,
) -> None:
    updates = {
        "decision": decision.status,
        "capability": decision.capability or "none",
        "reason": decision.reason,
        "result": result,
    }
    if _update_tool_trace(ctx, tool_name, updates):
        return
    event = {
        "type": "tool_call",
        "tool": tool_name,
        "tool_name": tool_name,
        "kind": tool_kind,
        "status": result,
    }
    event.update(updates)
    _trace_target(ctx).append(event)


def _record_policy_block(ctx: ExecutionContext, tool_name: str, decision: ToolDecision) -> None:
    if decision.reason != "policy_denied" or not decision.capability:
        return
    context = CapabilityContext(
        tool_name=tool_name,
        resolved_source="policy",
        runner="policy",
        protocol_version=1,
        guarantees=EffectiveGuarantees(),
    )
    record_capability_check(
        context,
        CapabilityCheck(
            capability=decision.capability,
            allowed=False,
            guarantee_source="policy",
            reason="policy_denied",
        ),
        _trace_target(ctx),
    )


def _update_tool_trace(ctx: ExecutionContext, tool_name: str, updates: dict) -> bool:
    for event in reversed(_trace_target(ctx)):
        if not isinstance(event, dict):
            continue
        if event.get("type") != "tool_call":
            continue
        if event.get("tool") != tool_name and event.get("tool_name") != tool_name:
            continue
        event.update(updates)
        return True
    return False


def _trace_target(ctx: ExecutionContext) -> list[dict]:
    return ctx.pending_tool_traces if ctx.tool_call_source == "ai" else ctx.traces


def _record_foreign_boundary_start(
    ctx: ExecutionContext,
    tool_decl,
    args: dict,
    *,
    policy_mode: str,
) -> None:
    if tool_decl is None or getattr(tool_decl, "declared_as", "tool") != "foreign":
        return
    secret_values = collect_secret_values(getattr(ctx, "config", None))
    event = {
        "type": TraceEventType.BOUNDARY_START,
        "boundary": "foreign",
        "language": foreign_language_label(getattr(tool_decl, "kind", None)),
        "function_name": tool_decl.name,
        "policy_mode": policy_mode,
        "input_summary": summarize_value(args, secret_values=secret_values),
    }
    _trace_target(ctx).append(event)


def _record_foreign_boundary_end(
    ctx: ExecutionContext,
    tool_decl,
    *,
    status: str,
    result: object | None = None,
    error: Exception | None = None,
    policy_mode: str,
) -> None:
    if tool_decl is None or getattr(tool_decl, "declared_as", "tool") != "foreign":
        return
    secret_values = collect_secret_values(getattr(ctx, "config", None))
    event = {
        "type": TraceEventType.BOUNDARY_END,
        "boundary": "foreign",
        "language": foreign_language_label(getattr(tool_decl, "kind", None)),
        "function_name": tool_decl.name,
        "policy_mode": policy_mode,
        "status": status,
    }
    if status == "ok":
        event["output_summary"] = summarize_value(result, secret_values=secret_values)
    elif error is not None:
        event["error_message"] = redact_text(str(error), secret_values)
    _trace_target(ctx).append(event)


__all__ = [
    "_record_foreign_boundary_end",
    "_record_foreign_boundary_start",
    "_record_policy_block",
    "_record_tool_trace",
]
