from __future__ import annotations

import time
import uuid
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.observe import summarize_value
from namel3ss.runtime.capabilities import build_effective_guarantees, resolve_tool_capabilities
from namel3ss.runtime.capabilities.coverage import container_runner_coverage, local_runner_coverage
from namel3ss.runtime.capabilities.gates import (
    check_network,
    check_secret_allowed,
    record_capability_check,
    record_capability_checks,
)
from namel3ss.runtime.capabilities.gates.base import CapabilityViolation, REASON_COVERAGE_MISSING
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.runtime.capabilities.overrides import unsafe_override_enabled
from namel3ss.runtime.capabilities.secrets import secret_names_in_payload
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from namel3ss.runtime.tools.entry_validation import validate_python_tool_entry, validate_python_tool_entry_exists
from namel3ss.runtime.tools.python_runtime_helpers import _binding_example, _tool_example, _tool_pack_example
from namel3ss.runtime.tools.schema_validate import validate_tool_fields
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest
from namel3ss.runtime.tools.runners.registry import get_runner
from namel3ss.runtime.tools.sandbox import sandbox_enabled
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION
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
        module_path = entry.split(":", 1)[0].strip()
        runner_name = binding.runner or "local"
        allow_external = resolved_source in {"installed_pack"} or module_path.startswith("tests.fixtures.")
        if (
            runner_name == "local"
            and resolved_source == "binding"
            and (module_path == "tools" or module_path.startswith("tools."))
        ):
            validate_python_tool_entry_exists(entry, tool.name, app_root=app_root, line=line, column=column)
        else:
            validate_python_tool_entry(entry, tool.name, line=line, column=column, allow_external=allow_external)
        if binding.kind != "python":
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Tool "{tool.name}" binding kind is "{binding.kind}".',
                    why="Python tools require python bindings in tools.yaml.",
                    fix='Set kind to "python" in the binding.',
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
        if runner_name == "node":
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Tool "{tool.name}" has unsupported runner "{runner_name}".',
                    why="Python tools cannot run on the node runner.",
                    fix='Set runner to "local", "service", or "container".',
                    example='runner: "local"',
                ),
                line=line,
                column=column,
            )
        trace_event["runner"] = runner_name
        if runner_name == "service" and binding.url:
            trace_event["service_url"] = binding.url
        if runner_name == "container":
            if binding.image:
                trace_event["image"] = binding.image
            if binding.command:
                trace_event["command"] = " ".join(binding.command)
            if getattr(binding, "enforcement", None):
                trace_event["container_enforcement"] = binding.enforcement
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
        capability_ctx = CapabilityContext(
            tool_name=tool.name,
            resolved_source=resolved_source,
            runner=runner_name,
            protocol_version=PROTOCOL_VERSION,
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
        if isinstance(err, CapabilityViolation):
            raise Namel3ssError(str(err), line=line, column=column) from err
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
                    what=f'Python tool "{tool.name}" failed with {err.error_type}.',
                    why=redacted_message,
                    fix=fix,
                    example=example,
                ),
                line=line,
                column=column,
            ) from err
        raise Namel3ssError(
            build_guidance_message(
                what=f'Python tool "{tool.name}" failed with {err.__class__.__name__}.',
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
                why="tools.yaml and tools/ are relative to the project root.",
                fix="Run Studio from the folder that contains app.ai or pass app_path explicitly.",
                example="cd <project-root> && n3 studio app.ai",
            ),
            line=line,
            column=column,
        )
    return Path(project_root).resolve()


def _trace_error_details(err: Exception, secret_values: list[str]) -> tuple[str, str]:
    if isinstance(err, ToolExecutionError):
        return err.error_type, redact_text(_strip_traceback(err.error_message), secret_values)
    error_type = err.__class__.__name__
    error_message = _strip_traceback(str(err))
    cause = getattr(err, "__cause__", None)
    if cause is not None:
        error_type = cause.__class__.__name__
        error_message = _strip_traceback(str(cause))
    return error_type, redact_text(error_message, secret_values)
def _strip_traceback(message: str | None) -> str:
    text = str(message or "")
    if "Traceback" not in text:
        return text
    return text.split("Traceback", 1)[0].strip()
def _resolve_timeout_seconds(ctx: ExecutionContext, tool: ir.ToolDecl, *, line: int | None, column: int | None) -> int:
    if tool.timeout_seconds is not None:
        return tool.timeout_seconds
    config_timeout = getattr(getattr(ctx, "config", None), "python_tools", None)
    if config_timeout and getattr(config_timeout, "timeout_seconds", None):
        return int(config_timeout.timeout_seconds)
    return DEFAULT_TOOL_TIMEOUT_SECONDS


def _preflight_capabilities(
    ctx: ExecutionContext,
    capability_ctx: CapabilityContext,
    *,
    runner_name: str,
    payload: object,
    binding,
    resolved_source: str,
    unsafe_override: bool,
    line: int | None,
    column: int | None,
) -> bool:
    unsafe_used = False
    if runner_name in {"local", "node"}:
        sandbox_on = sandbox_enabled(
            resolved_source=resolved_source,
            runner=runner_name,
            binding=binding,
        )
        coverage = local_runner_coverage(capability_ctx.guarantees, sandbox_enabled=sandbox_on)
        if coverage.status != "enforced":
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, coverage.missing)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" requires sandbox enforcement.',
                        why=f"Sandbox is disabled but guarantees require: {', '.join(coverage.missing)}.",
                        fix="Enable sandbox in tools.yaml or relax the capability overrides.",
                        example='sandbox: true',
                    ),
                    line=line,
                    column=column,
                )
    if runner_name == "container":
        if capability_ctx.guarantees.no_subprocess:
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, ["subprocess"])
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" cannot run in a container runner.',
                        why="Container execution requires subprocess access.",
                        fix="Switch to the local runner or relax the no_subprocess guarantee.",
                        example=f'n3 tools set-runner "{capability_ctx.tool_name}" --runner local',
                    ),
                    line=line,
                    column=column,
                )
        coverage = container_runner_coverage(capability_ctx.guarantees, enforcement=getattr(binding, "enforcement", None))
        if coverage.status == "not_enforceable":
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, coverage.missing)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" requires container enforcement.',
                        why="Container bindings must declare enforcement coverage.",
                        fix="Set enforcement to declared/verified or choose a local runner.",
                        example='enforcement: "declared"',
                    ),
                    line=line,
                    column=column,
                )
    if runner_name == "service":
        url = binding.url or ctx.config.python_tools.service_url
        if url:
            _gate_capability(
                ctx,
                capability_ctx,
                lambda: check_network(capability_ctx, _record_for(ctx, capability_ctx), url=url, method="POST"),
                line=line,
                column=column,
            )
        _check_payload_secrets(ctx, capability_ctx, payload, line=line, column=column)
    return unsafe_used


def _gate_capability(ctx: ExecutionContext, capability_ctx: CapabilityContext, fn, *, line: int | None, column: int | None) -> None:
    try:
        fn()
    except CapabilityViolation as err:
        raise Namel3ssError(str(err), line=line, column=column) from err


def _check_payload_secrets(
    ctx: ExecutionContext,
    capability_ctx: CapabilityContext,
    payload: object,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if capability_ctx.guarantees.secrets_allowed is None:
        return
    names = secret_names_in_payload(payload, ctx.config)
    if not names:
        return
    record = _record_for(ctx, capability_ctx)
    for name in sorted(names):
        _gate_capability(
            ctx,
            capability_ctx,
            lambda n=name: check_secret_allowed(capability_ctx, record, secret_name=n),
            line=line,
            column=column,
        )


def _record_for(ctx: ExecutionContext, capability_ctx: CapabilityContext):
    return lambda check: record_capability_check(capability_ctx, check, ctx.traces)


def _record_coverage_block(ctx: ExecutionContext, capability_ctx: CapabilityContext, missing: list[str]) -> None:
    for capability in missing:
        source = capability_ctx.guarantees.source_for_capability(capability) or "pack"
        record_capability_check(
            capability_ctx,
            CapabilityCheck(
                capability=capability,
                allowed=False,
                guarantee_source=source,
                reason=REASON_COVERAGE_MISSING,
            ),
            ctx.traces,
        )
def _pack_root_from_paths(paths: list[Path] | None) -> Path | None:
    if not paths:
        return None
    return paths[0]


__all__ = ["execute_python_tool_call"]
