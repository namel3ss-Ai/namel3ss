from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.boundary import mark_boundary
from namel3ss.runtime.capabilities.gates import record_capability_check
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext, EffectiveGuarantees
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.parallel.isolation import ensure_tool_call_allowed
from namel3ss.runtime.tools.gate import gate_tool_call
from namel3ss.runtime.tools.outcome import ToolCallOutcome, ToolDecision
from namel3ss.runtime.tools.policy import load_tool_policy, normalize_capabilities
from namel3ss.runtime.tools.python_runtime import execute_python_tool_call
from namel3ss.runtime.tools.node_runtime import execute_node_tool_call
from namel3ss.runtime.tools.registry import execute_tool as execute_builtin_tool, is_builtin_tool
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.tools.runners.registry import get_runner
from namel3ss.runtime.values.normalize import ensure_object


@dataclass(frozen=True)
class _BindingCheck:
    ok: bool
    error: Namel3ssError | None
    reason: str | None
    status: str | None


def execute_tool_call(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None = None,
    column: int | None = None,
) -> ToolCallOutcome:
    outcome, err = _execute_tool_call_internal(
        ctx,
        tool_name,
        args,
        line=line,
        column=column,
    )
    if err is not None:
        raise err
    return outcome


def execute_tool_call_with_outcome(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None = None,
    column: int | None = None,
) -> tuple[ToolCallOutcome, Exception | None]:
    return _execute_tool_call_internal(
        ctx,
        tool_name,
        args,
        line=line,
        column=column,
    )


def _execute_tool_call_internal(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None,
    column: int | None,
) -> tuple[ToolCallOutcome, Exception | None]:
    ensure_tool_call_allowed(ctx, tool_name, line=line, column=column)
    tool_decl = ctx.tools.get(tool_name)
    builtin_fallback = ctx.tool_call_source == "ai" and is_builtin_tool(tool_name)
    tool_kind = tool_decl.kind if tool_decl else ("builtin" if builtin_fallback else None)
    required_caps = normalize_capabilities(getattr(tool_decl, "capabilities", None) if tool_decl else ())
    binding_check = _check_binding(ctx, tool_name, tool_kind, line=line, column=column)
    if not binding_check.ok:
        decision_reason = binding_check.reason or "missing_binding"
        decision_status = binding_check.status or "error"
        message = binding_check.error.message if binding_check.error else _binding_message(tool_name, decision_reason)
        decision = ToolDecision(
            status=decision_status,
            capability=None,
            reason=decision_reason,
            message=message,
        )
        outcome = ToolCallOutcome(
            tool_name=tool_name,
            decision=decision,
            result_kind="blocked" if decision_status == "blocked" else "error",
            result_summary=decision.message,
        )
        if decision_status == "blocked":
            _record_policy_block(ctx, tool_name, decision)
        _record_tool_trace(
            ctx,
            tool_name,
            tool_kind,
            decision,
            result="blocked" if decision_status == "blocked" else "error",
        )
        err = _blocked_error(ctx, tool_name, decision, binding_check.error, line=line, column=column)
        mark_boundary(err, "tools")
        return outcome, err
    policy = load_tool_policy(
        tool_name=tool_name,
        tool_known=tool_decl is not None or builtin_fallback,
        binding_ok=True,
        config=getattr(ctx, "config", None),
    )
    decision = gate_tool_call(tool_name=tool_name, required_capabilities=required_caps, policy=policy)
    if decision.status != "allowed":
        outcome = ToolCallOutcome(
            tool_name=tool_name,
            decision=decision,
            result_kind="blocked" if decision.status == "blocked" else "error",
            result_summary=decision.message,
        )
        if decision.status == "blocked":
            _record_policy_block(ctx, tool_name, decision)
        _record_tool_trace(
            ctx,
            tool_name,
            tool_kind,
            decision,
            result="blocked" if decision.status == "blocked" else "error",
        )
        err = _blocked_error(ctx, tool_name, decision, None, line=line, column=column)
        mark_boundary(err, "tools")
        return outcome, err
    if tool_kind is None:
        err = Namel3ssError(f'Unknown tool "{tool_name}".', line=line, column=column)
        _record_tool_trace(ctx, tool_name, tool_kind, decision, result="error")
        mark_boundary(err, "tools")
        outcome = ToolCallOutcome(
            tool_name=tool_name,
            decision=decision,
            result_kind="error",
            result_summary=str(err),
        )
        return outcome, err

    try:
        if tool_kind == "python":
            result = _run_python_tool(ctx, tool_name, args, line=line, column=column)
        elif tool_kind == "node":
            result = _run_node_tool(ctx, tool_name, args, line=line, column=column)
        elif tool_kind == "builtin" and ctx.tool_call_source == "ai":
            result = execute_builtin_tool(tool_name, args)
        else:
            err = _unsupported_kind_error(tool_name, tool_kind or "unknown", line=line, column=column)
            _record_tool_trace(ctx, tool_name, tool_kind, decision, result="error")
            mark_boundary(err, "tools")
            outcome = ToolCallOutcome(
                tool_name=tool_name,
                decision=decision,
                result_kind="error",
                result_summary=str(err),
            )
            return outcome, err
    except Exception as err:
        _record_tool_trace(ctx, tool_name, tool_kind, decision, result="error")
        mark_boundary(err, "tools")
        outcome = ToolCallOutcome(
            tool_name=tool_name,
            decision=decision,
            result_kind="error",
            result_summary=str(err),
        )
        return outcome, err

    result_object = ensure_object(result)
    _record_tool_trace(ctx, tool_name, tool_kind, decision, result="ok")
    outcome = ToolCallOutcome(
        tool_name=tool_name,
        decision=decision,
        result_kind="ok",
        result_summary="ok",
        result_value=result_object,
    )
    return outcome, None


def _run_python_tool(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None,
    column: int | None,
) -> object:
    trace_target, original_traces = _swap_trace_target(ctx)
    try:
        return execute_python_tool_call(ctx, tool_name=tool_name, payload=args, line=line, column=column)
    finally:
        if original_traces is not None:
            ctx.traces = original_traces
            ctx.pending_tool_traces = trace_target


def _run_node_tool(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None,
    column: int | None,
) -> object:
    trace_target, original_traces = _swap_trace_target(ctx)
    try:
        return execute_node_tool_call(ctx, tool_name=tool_name, payload=args, line=line, column=column)
    finally:
        if original_traces is not None:
            ctx.traces = original_traces
            ctx.pending_tool_traces = trace_target


def _swap_trace_target(ctx: ExecutionContext) -> tuple[list[dict], list | None]:
    if ctx.tool_call_source != "ai":
        return ctx.traces, None
    original = ctx.traces
    ctx.traces = ctx.pending_tool_traces
    return ctx.pending_tool_traces, original


def _check_binding(
    ctx: ExecutionContext,
    tool_name: str,
    tool_kind: str | None,
    *,
    line: int | None,
    column: int | None,
) -> _BindingCheck:
    if tool_kind is None:
        return _BindingCheck(ok=False, error=None, reason="unknown_tool", status="error")
    if tool_kind not in {"python", "node"}:
        return _BindingCheck(ok=True, error=None, reason=None, status=None)
    if not ctx.project_root:
        return _BindingCheck(ok=True, error=None, reason=None, status=None)
    try:
        resolved = resolve_tool_binding(
            Path(ctx.project_root),
            tool_name,
            ctx.config,
            tool_kind=tool_kind,
            line=line,
            column=column,
        )
    except Namel3ssError as err:
        reason = _binding_reason(err)
        status = "blocked" if reason == "pack_unavailable_or_unverified" else "error"
        return _BindingCheck(ok=False, error=err, reason=reason, status=status)
    runner_name = resolved.binding.runner or ("node" if tool_kind == "node" else "local")
    try:
        get_runner(runner_name)
    except Namel3ssError as err:
        return _BindingCheck(ok=False, error=err, reason="unknown_runner", status="error")
    return _BindingCheck(ok=True, error=None, reason=None, status=None)


def _binding_reason(err: Namel3ssError) -> str:
    details = err.details if isinstance(err.details, dict) else {}
    reason = details.get("tool_reason")
    if isinstance(reason, str) and reason:
        return reason
    return "binding_error"


def _binding_message(tool_name: str, reason: str) -> str:
    if reason == "unknown_tool":
        return f'Unknown tool "{tool_name}".'
    if reason == "missing_binding":
        return f'Tool "{tool_name}" is not bound to a runner.'
    return f'Tool "{tool_name}" failed.'


def _blocked_error(
    ctx: ExecutionContext,
    tool_name: str,
    decision: ToolDecision,
    binding_error: Namel3ssError | None,
    *,
    line: int | None,
    column: int | None,
) -> Namel3ssError:
    if binding_error is not None and decision.reason in {
        "binding_error",
        "missing_binding",
        "pack_collision",
        "pack_pin_missing",
        "pack_unavailable_or_unverified",
        "unknown_runner",
    }:
        return binding_error
    if decision.reason == "unknown_tool" and ctx.tool_call_source != "ai":
        return Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not declared.',
                why="The flow called a tool name that is not in the program.",
                fix='Declare the tool in your .ai file before calling it.',
                example=_tool_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return Namel3ssError(decision.message, line=line, column=column)


def _unsupported_kind_error(tool_name: str, kind: str, *, line: int | None, column: int | None) -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what=f'Tool "{tool_name}" has unsupported kind "{kind}".',
            why="Only python and node tools can be called directly from flows.",
            fix='Declare the tool with `implemented using python` or `implemented using node` before calling it.',
            example=_tool_example(tool_name),
        ),
        line=line,
        column=column,
    )


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


def _tool_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


__all__ = ["execute_tool_call", "execute_tool_call_with_outcome"]
