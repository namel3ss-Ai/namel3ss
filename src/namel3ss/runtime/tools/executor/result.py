from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.tools.outcome import ToolDecision


def _ensure_tool_trace(
    ctx: ExecutionContext,
    tool_name: str,
    tool_kind: str | None,
    *,
    status: str,
    reason: str,
) -> None:
    for target in (ctx.traces, ctx.pending_tool_traces):
        for event in reversed(target):
            if not isinstance(event, dict):
                continue
            if event.get("type") != "tool_call":
                continue
            if event.get("tool") == tool_name or event.get("tool_name") == tool_name:
                return
    ctx.traces.append(
        {
            "type": "tool_call",
            "tool": tool_name,
            "tool_name": tool_name,
            "kind": tool_kind,
            "status": status,
            "decision": status,
            "capability": "none",
            "reason": reason,
            "result": status,
        }
    )


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
        "pack_not_declared",
        "pack_permission_denied",
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
            why="Only python, node, http, and file tools can be called directly from flows.",
            fix='Declare the tool with `implemented using python`, `implemented using node`, `implemented using http`, or `implemented using file` before calling it.',
            example=_tool_example(tool_name),
        ),
        line=line,
        column=column,
    )


def _tool_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


__all__ = ["_binding_message", "_blocked_error", "_ensure_tool_trace", "_tool_example", "_unsupported_kind_error"]
