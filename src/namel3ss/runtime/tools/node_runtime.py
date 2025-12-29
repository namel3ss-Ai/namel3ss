from __future__ import annotations

import time
import uuid
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.observe import summarize_value
from namel3ss.runtime.capabilities import build_effective_guarantees, resolve_tool_capabilities
from namel3ss.runtime.capabilities.gates import record_capability_checks
from namel3ss.runtime.capabilities.overrides import unsafe_override_enabled
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.tools.entry_validation import validate_node_tool_entry
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest
from namel3ss.runtime.tools.runners.registry import get_runner
from namel3ss.runtime.tools.schema_validate import validate_tool_fields
from namel3ss.runtime.tools.python_runtime import (
    ToolExecutionError,
    _pack_root_from_paths,
    _preflight_capabilities,
    _resolve_project_root,
    _resolve_timeout_seconds,
    _trace_error_details,
)
from namel3ss.secrets import collect_secret_values, redact_text


def execute_node_tool_call(
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
    if tool.kind != "node":
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" has unsupported kind "{tool.kind}".',
                why="Only node tools can be called by this executor.",
                fix='Declare the tool with `implemented using node` before calling it.',
                example=_tool_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return _execute_node_tool(ctx, tool, payload, line=line, column=column)


def _execute_node_tool(
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
        "tool_name": tool.name,
        "kind": tool.kind,
        "input_summary": summarize_value(payload, secret_values=secret_values),
    }
    if tool.purity != "pure":
        trace_event["purity"] = tool.purity
    start_time = time.monotonic()
    timeout_seconds = _resolve_timeout_seconds(ctx, tool, line=line, column=column)
    resolved_source = "binding"
    trace_event["resolved_source"] = resolved_source
    pack_id = None
    pack_name = None
    pack_version = None
    trace_id = str(uuid.uuid4())
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
        resolved = resolve_tool_binding(app_root, tool.name, ctx.config, tool_kind=tool.kind, line=line, column=column)
        binding = resolved.binding
        resolved_source = resolved.source
        pack_id = resolved.pack_id
        pack_name = resolved.pack_name
        pack_version = resolved.pack_version
        entry = binding.entry
        validate_node_tool_entry(
            entry,
            tool.name,
            line=line,
            column=column,
            allow_external=resolved_source in {"builtin_pack", "installed_pack"},
        )
        if binding.kind != "node":
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Tool "{tool.name}" binding kind is "{binding.kind}".',
                    why="Node tools require node bindings in tools.yaml.",
                    fix='Set kind to "node" in the binding.',
                    example=_binding_example(tool.name),
                ),
                line=line,
                column=column,
            )
        timeout_ms = binding.timeout_ms if binding.timeout_ms is not None else timeout_seconds * 1000
        trace_event["timeout_ms"] = timeout_ms
        trace_event["resolved_source"] = resolved_source
        if resolved_source == "binding":
            trace_event["entry"] = entry
        runner_name = binding.runner or "node"
        if runner_name not in {"node", "service"}:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Tool "{tool.name}" has unsupported runner "{runner_name}".',
                    why="Node tools must use the node or service runner.",
                    fix='Set runner to "node" or "service".',
                    example='runner: "node"',
                ),
                line=line,
                column=column,
            )
        trace_event["runner"] = runner_name
        if runner_name == "service" and binding.url:
            trace_event["service_url"] = binding.url
        if resolved_source in {"builtin_pack", "installed_pack"} and pack_id:
            trace_event["pack_id"] = pack_id
            if pack_name:
                trace_event["pack_name"] = pack_name
            trace_event["pack_version"] = pack_version
        pack_root = _pack_root_from_paths(resolved.pack_paths)
        policy = load_pack_policy(app_root) if resolved_source in {"builtin_pack", "installed_pack"} else None
        tool_caps = resolve_tool_capabilities(tool.name, resolved_source, pack_root)
        overrides = getattr(ctx.config, "capability_overrides", {}).get(tool.name) if ctx.config else None
        unsafe_override = unsafe_override_enabled(overrides)
        guarantees = build_effective_guarantees(
            tool_name=tool.name,
            tool_purity=tool.purity,
            binding_purity=binding.purity,
            capabilities=tool_caps,
            overrides=overrides,
            policy=policy,
        )
        capability_ctx = _capability_context(
            tool,
            runner_name=runner_name,
            resolved_source=resolved_source,
            guarantees=guarantees,
        )
        unsafe_used = _preflight_capabilities(
            ctx,
            capability_ctx,
            runner_name=runner_name,
            payload=payload,
            binding=binding,
            resolved_source=resolved_source,
            unsafe_override=unsafe_override,
            line=line,
            column=column,
        )
        if unsafe_used:
            trace_event["unsafe_override"] = True
        runner = get_runner(runner_name)
        result = runner.execute(
            ToolRunnerRequest(
                tool_name=tool.name,
                kind=tool.kind,
                entry=entry,
                payload=payload,
                timeout_ms=timeout_ms,
                trace_id=trace_id,
                app_root=app_root,
                flow_name=getattr(ctx.flow, "name", None),
                binding=binding,
                config=ctx.config,
                pack_paths=resolved.pack_paths,
                capability_context=capability_ctx.to_dict(),
                allow_unsafe=unsafe_override,
            )
        )
        if result.capability_checks:
            record_capability_checks(capability_ctx, result.capability_checks, ctx.traces)
        if result.metadata:
            trace_event.update(result.metadata)
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
            if err.error_type == "CapabilityViolation":
                raise Namel3ssError(err.error_message, line=line, column=column) from err
            redacted_message = redact_text(err.error_message or "The tool returned an error.", secret_values)
            if resolved_source in {"builtin_pack", "installed_pack"} and pack_id:
                fix = "Review the tool inputs or upgrade namel3ss if the issue persists."
                example = _tool_pack_example(tool.name)
            else:
                fix = "Fix the tool implementation in tools/ and try again."
                example = _tool_example(tool.name)
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Node tool "{tool.name}" failed with {err.error_type}.',
                    why=redacted_message,
                    fix=fix,
                    example=example,
                ),
                line=line,
                column=column,
            ) from err
        raise Namel3ssError(
            build_guidance_message(
                what=f'Node tool "{tool.name}" failed with {err.__class__.__name__}.',
                why="The tool function raised an exception during execution.",
                fix="Fix the tool implementation in tools/ and try again."
                if resolved_source not in {"builtin_pack", "installed_pack"}
                else "Review the tool inputs or upgrade namel3ss if the issue persists.",
                example=_tool_example(tool.name)
                if resolved_source not in {"builtin_pack", "installed_pack"}
                else _tool_pack_example(tool.name),
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


def _capability_context(
    tool: ir.ToolDecl,
    *,
    runner_name: str,
    resolved_source: str,
    guarantees,
):
    from namel3ss.runtime.capabilities.model import CapabilityContext
    from namel3ss.runtime.tools.runners.node.protocol import PROTOCOL_VERSION

    return CapabilityContext(
        tool_name=tool.name,
        resolved_source=resolved_source,
        runner=runner_name,
        protocol_version=PROTOCOL_VERSION,
        guarantees=guarantees,
    )


def _tool_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using node\n\n"
        "  input:\n"
        "    web address is text\n\n"
        "  output:\n"
        "    data is json"
    )


def _tool_pack_example(tool_name: str) -> str:
    return (
        f'tool "{tool_name}":\n'
        "  implemented using node\n\n"
        "  input:\n"
        "    text is text\n\n"
        "  output:\n"
        "    text is text"
    )


def _binding_example(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "node"\n'
        '    entry: "tools.my_tool:run"'
    )


__all__ = ["execute_node_tool_call"]
