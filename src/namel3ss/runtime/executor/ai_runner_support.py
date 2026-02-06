from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.canary_results import record_canary_result
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.traces.redact import redact_memory_context


def run_shadow_compare(
    ctx: ExecutionContext,
    *,
    provider,
    profile: ir.AIDecl,
    provider_name: str,
    selected_model: str,
    shadow_model: str | None,
    canary_hit: bool,
    user_input: str,
    memory_context: dict,
    output_text: str,
    secret_values: set[str] | list[str],
) -> None:
    if not shadow_model:
        return
    try:
        shadow_response = provider.ask(
            model=shadow_model,
            system_prompt=profile.system_prompt,
            user_input=user_input,
            tools=[{"name": name} for name in profile.exposed_tools],
            memory=memory_context,
            tool_results=[],
        )
    except Exception:
        return
    shadow_output = shadow_response.output if hasattr(shadow_response, "output") else shadow_response
    shadow_output_text = normalize_ai_text(
        shadow_output,
        provider_name=provider_name,
        secret_values=secret_values,
    )
    if canary_hit:
        primary_model = shadow_model
        candidate_model = selected_model
        primary_output = shadow_output_text
        candidate_output = output_text
        mode = "canary"
    else:
        primary_model = selected_model
        candidate_model = shadow_model
        primary_output = output_text
        candidate_output = shadow_output_text
        mode = "shadow"
    record_canary_result(
        project_root=ctx.project_root,
        app_path=ctx.app_path,
        flow_name=getattr(ctx.flow, "name", ""),
        input_text=user_input,
        primary_model=primary_model,
        candidate_model=candidate_model,
        mode=mode,
        primary_output=primary_output,
        candidate_output=candidate_output,
        step_count=int(getattr(ctx, "execution_step_counter", 0)),
    )


def resolve_provider(ctx: ExecutionContext, provider_name: str):
    key = provider_name.lower()
    _ = get_provider_capabilities(key)  # read-only lookup for capability metadata
    if key in ctx.provider_cache:
        return ctx.provider_cache[key]
    provider = get_provider(key, ctx.config)
    ctx.provider_cache[key] = provider
    return provider


def flush_pending_tool_traces(ctx: ExecutionContext) -> None:
    if not ctx.pending_tool_traces:
        return
    ctx.traces.extend(ctx.pending_tool_traces)
    ctx.pending_tool_traces.clear()


def extract_provider_diagnostic(err: Exception) -> dict[str, object] | None:
    if not isinstance(err, Namel3ssError):
        return None
    details = err.details
    if not isinstance(details, dict):
        return None
    diagnostic = details.get("diagnostic")
    if not isinstance(diagnostic, dict):
        return None
    keys = (
        "provider",
        "url",
        "status",
        "code",
        "type",
        "message",
        "category",
        "hint",
        "severity",
        "network_error",
    )
    return {key: diagnostic.get(key) for key in keys}


def append_ai_error_trace(
    ctx: ExecutionContext,
    profile: ir.AIDecl,
    agent_name: str | None,
    user_input: str,
    memory_context: dict,
    tool_events: list[dict],
    canonical_events: list[dict],
    *,
    model_name: str,
    input_format: str | None = None,
    input_structured: object | None = None,
) -> None:
    trace = AITrace(
        ai_name=profile.name,
        ai_profile_name=profile.name,
        agent_name=agent_name,
        model=model_name,
        system_prompt=profile.system_prompt,
        input=user_input,
        input_structured=input_structured,
        input_format=input_format,
        output="",
        memory=redact_memory_context(memory_context),
        tool_calls=[e for e in tool_events if e.get("type") == "call"],
        tool_results=[e for e in tool_events if e.get("type") == "result"],
        canonical_events=canonical_events,
    )
    ctx.traces.append(trace)


__all__ = [
    "append_ai_error_trace",
    "extract_provider_diagnostic",
    "flush_pending_tool_traces",
    "resolve_provider",
    "run_shadow_compare",
]
