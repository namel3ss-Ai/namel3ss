from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.boundary import mark_boundary
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.parallel.isolation import ensure_tool_call_allowed
from namel3ss.runtime.tools.gate import gate_tool_call
from namel3ss.runtime.tools.outcome import ToolCallOutcome, ToolDecision
from namel3ss.runtime.tools.policy import load_tool_policy, normalize_capabilities
from namel3ss.runtime.tools.python_runtime import execute_python_tool_call
from namel3ss.runtime.tools.node_runtime import execute_node_tool_call
from namel3ss.runtime.tools.registry import execute_tool as execute_builtin_tool, is_builtin_tool
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.values.normalize import ensure_object


def execute_tool_call(
    ctx: ExecutionContext,
    tool_name: str,
    args: dict,
    *,
    line: int | None = None,
    column: int | None = None,
) -> ToolCallOutcome:
    ensure_tool_call_allowed(ctx, tool_name, line=line, column=column)
    tool_decl = ctx.tools.get(tool_name)
    builtin_fallback = ctx.tool_call_source == "ai" and is_builtin_tool(tool_name)
    tool_kind = tool_decl.kind if tool_decl else ("builtin" if builtin_fallback else None)
    required_caps = normalize_capabilities(getattr(tool_decl, "capabilities", None) if tool_decl else ())
    binding_ok, binding_error = _check_binding(ctx, tool_name, tool_kind, line=line, column=column)
    policy = load_tool_policy(
        tool_name=tool_name,
        tool_known=tool_decl is not None or builtin_fallback,
        binding_ok=binding_ok,
        config=getattr(ctx, "config", None),
    )
    decision = gate_tool_call(tool_name=tool_name, required_capabilities=required_caps, policy=policy)
    if decision.status == "blocked":
        outcome = ToolCallOutcome(
            tool_name=tool_name,
            decision=decision,
            result_kind="blocked",
            result_summary=decision.message,
        )
        _record_tool_trace(ctx, tool_name, tool_kind, decision, result="blocked")
        err = _blocked_error(ctx, tool_name, decision, binding_error, line=line, column=column)
        mark_boundary(err, "tools")
        raise err
    if tool_kind is None:
        err = Namel3ssError(f'Unknown tool "{tool_name}".', line=line, column=column)
        _record_tool_trace(ctx, tool_name, tool_kind, decision, result="error")
        mark_boundary(err, "tools")
        raise err

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
            raise err
    except Exception as err:
        _record_tool_trace(ctx, tool_name, tool_kind, decision, result="error")
        mark_boundary(err, "tools")
        raise

    result_object = ensure_object(result)
    _record_tool_trace(ctx, tool_name, tool_kind, decision, result="ok")
    return ToolCallOutcome(
        tool_name=tool_name,
        decision=decision,
        result_kind="ok",
        result_summary="ok",
        result_value=result_object,
    )


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
) -> tuple[bool, Namel3ssError | None]:
    if tool_kind is None:
        return False, None
    if tool_kind not in {"python", "node"}:
        return True, None
    if not ctx.project_root:
        return True, None
    try:
        resolve_tool_binding(Path(ctx.project_root), tool_name, ctx.config, tool_kind=tool_kind, line=line, column=column)
    except Namel3ssError as err:
        return False, err
    return True, None


def _blocked_error(
    ctx: ExecutionContext,
    tool_name: str,
    decision: ToolDecision,
    binding_error: Namel3ssError | None,
    *,
    line: int | None,
    column: int | None,
) -> Namel3ssError:
    if decision.reason == "missing_binding" and binding_error is not None:
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


__all__ = ["execute_tool_call"]
