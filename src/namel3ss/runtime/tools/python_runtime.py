from __future__ import annotations

import time
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.observe import summarize_value
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.tools.bindings import resolve_tool_binding
from namel3ss.runtime.tools.entry_validation import validate_python_tool_entry
from namel3ss.runtime.tools.python_env import detect_dependency_info, resolve_python_env
from namel3ss.runtime.tools.schema_validate import validate_tool_fields
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION, run_tool_subprocess
from namel3ss.secrets import collect_secret_values, redact_text

DEFAULT_TOOL_TIMEOUT_SECONDS = 10


class ToolExecutionError(Exception):
    def __init__(self, error_type: str, error_message: str) -> None:
        super().__init__(error_message)
        self.error_type = error_type
        self.error_message = error_message


def execute_python_tool_call(
    ctx: ExecutionContext,
    *,
    tool_name: str,
    payload: object,
    line: int | None,
    column: int | None,
) -> object:
    tool = ctx.tools.get(tool_name)
    if tool is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not declared.',
                why="The flow called a tool name that is not in the program.",
                fix='Declare the tool in your .ai file before calling it.',
                example=_tool_example(tool_name),
            ),
            line=line,
            column=column,
        )
    if tool.kind != "python":
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" has unsupported kind "{tool.kind}".',
                why="Only python tools can be called directly from flows.",
                fix='Declare the tool with `implemented using python` before calling it.',
                example=_tool_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return _execute_python_tool(ctx, tool, payload, line=line, column=column)


def _execute_python_tool(
    ctx: ExecutionContext,
    tool: ir.ToolDecl,
    payload: object,
    *,
    line: int | None,
    column: int | None,
) -> object:
    secret_values = collect_secret_values(ctx.config)
    trace_event = {
        "type": "tool_call",
        "tool": tool.name,
        "kind": tool.kind,
        "input_summary": summarize_value(payload, secret_values=secret_values),
    }
    if tool.purity != "pure":
        trace_event["purity"] = tool.purity
    start_time = time.monotonic()
    timeout_seconds = _resolve_timeout_seconds(ctx, tool, line=line, column=column)
    trace_event["timeout_seconds"] = timeout_seconds
    try:
        validate_tool_fields(
            fields=tool.input_fields,
            payload=payload,
            tool_name=tool.name,
            phase="input",
            line=line,
            column=column,
        )
        app_root = _resolve_project_root(ctx.project_root, tool.name, line=line, column=column)
        binding = resolve_tool_binding(app_root, tool.name, line=line, column=column)
        entry = binding.entry
        validate_python_tool_entry(entry, tool.name, line=line, column=column)
        dep_info = detect_dependency_info(app_root)
        env_info = resolve_python_env(app_root)
        trace_event["python_env"] = env_info.env_kind
        trace_event["python_path"] = str(env_info.python_path)
        trace_event["deps_source"] = dep_info.kind
        trace_event["protocol_version"] = PROTOCOL_VERSION
        result = run_tool_subprocess(
            python_path=env_info.python_path,
            tool_name=tool.name,
            entry=entry,
            payload=payload,
            app_root=app_root,
            timeout_seconds=timeout_seconds,
        )
        if not result.ok:
            raise ToolExecutionError(result.error_type or "ToolError", result.error_message or "Tool error")
        validate_tool_fields(
            fields=tool.output_fields,
            payload=result.output,
            tool_name=tool.name,
            phase="output",
            line=line,
            column=column,
        )
    except Exception as err:
        error_type, error_message = _trace_error_details(err, secret_values)
        duration_ms = int((time.monotonic() - start_time) * 1000)
        trace_event.update(
            {
                "status": "error",
                "error_type": error_type,
                "error_message": error_message,
                "duration_ms": duration_ms,
            }
        )
        ctx.traces.append(trace_event)
        if isinstance(err, Namel3ssError):
            raise
        if isinstance(err, ToolExecutionError):
            redacted_message = redact_text(err.error_message or "The tool returned an error.", secret_values)
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Python tool "{tool.name}" failed with {err.error_type}.',
                    why=redacted_message,
                    fix="Fix the tool implementation in tools/ and try again.",
                    example=_tool_example(tool.name),
                ),
                line=line,
                column=column,
            ) from err
        raise Namel3ssError(
            build_guidance_message(
                what=f'Python tool "{tool.name}" failed with {err.__class__.__name__}.',
                why="The tool function raised an exception during execution.",
                fix="Fix the tool implementation in tools/ and try again.",
                example=_tool_example(tool.name),
            ),
            line=line,
            column=column,
        ) from err
    duration_ms = int((time.monotonic() - start_time) * 1000)
    trace_event.update(
        {
            "status": "ok",
            "output_summary": summarize_value(result.output, secret_values=secret_values),
            "duration_ms": duration_ms,
        }
    )
    ctx.traces.append(trace_event)
    return result.output


def _resolve_project_root(
    project_root: str | None,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
) -> Path:
    if not project_root:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" cannot resolve tools/ without a project root.',
                why="The engine was started without a project root path.",
                fix="Run the app from its project root or pass project_root to the executor.",
                example=_tool_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return Path(project_root).resolve()


def _trace_error_details(err: Exception, secret_values: list[str]) -> tuple[str, str]:
    if isinstance(err, ToolExecutionError):
        return err.error_type, redact_text(err.error_message, secret_values)
    error_type = err.__class__.__name__
    error_message = str(err)
    cause = getattr(err, "__cause__", None)
    if cause is not None:
        error_type = cause.__class__.__name__
        error_message = str(cause)
    return error_type, redact_text(error_message, secret_values)


def _resolve_timeout_seconds(ctx: ExecutionContext, tool: ir.ToolDecl, *, line: int | None, column: int | None) -> int:
    if tool.timeout_seconds is not None:
        return tool.timeout_seconds
    config_timeout = getattr(getattr(ctx, "config", None), "python_tools", None)
    if config_timeout and getattr(config_timeout, "timeout_seconds", None):
        return int(config_timeout.timeout_seconds)
    return DEFAULT_TOOL_TIMEOUT_SECONDS


def _tool_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using python\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


__all__ = ["execute_python_tool_call"]
