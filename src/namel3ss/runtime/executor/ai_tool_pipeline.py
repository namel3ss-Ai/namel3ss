from __future__ import annotations

import time
import uuid

from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.boundary import mark_boundary
from namel3ss.runtime.executor.ai_observability import record_ai_event, record_ai_metrics
from namel3ss.runtime.executor.ai_response_output import extract_response_text
from namel3ss.runtime.executor.ai_runner_support import (
    append_ai_error_trace,
    extract_provider_diagnostic,
    run_shadow_compare,
)
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.provider_utils import _resolve_provider, _seed_from_structured_input
from namel3ss.runtime.explainability.logger import append_explain_entry
from namel3ss.runtime.explainability.seed_manager import resolve_ai_call_seed
from namel3ss.runtime.performance.state import run_cached_ai_text_call
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.runtime.tools.executor import execute_tool_call_with_outcome
from namel3ss.runtime.tools.field_schema import build_json_schema
from namel3ss.secrets import collect_secret_values
from namel3ss.traces.builders import (
    build_ai_call_completed,
    build_ai_call_failed,
    build_ai_call_started,
    build_ai_provider_error,
)


def run_ai_with_tools(
    ctx: ExecutionContext,
    profile: ir.AIDecl,
    user_input: str,
    memory_context: dict,
    tool_events: list[dict],
    *,
    canonical_events: list[dict] | None = None,
    agent_name: str | None = None,
    input_format: str | None = None,
    input_structured: object | None = None,
) -> tuple[str, list[dict]]:
    provider_name = (getattr(profile, "provider", "mock") or "mock").lower()
    model_name = profile.model
    shadow_model: str | None = None
    canary_hit = False
    manager = getattr(ctx, "model_manager", None)
    if manager is not None and hasattr(manager, "route_model"):
        route = manager.route_model(
            profile.model,
            key=user_input,
            flow_name=getattr(ctx.flow, "name", None),
        )
        model_name = route.selected_model
        shadow_model = route.shadow_model
        canary_hit = bool(route.canary_hit)
        manager.ensure_model(model_name, project_root=ctx.project_root, app_path=ctx.app_path)
        if shadow_model:
            manager.ensure_model(shadow_model, project_root=ctx.project_root, app_path=ctx.app_path)
    secret_values = collect_secret_values(ctx.config)
    start_step = getattr(ctx, "execution_step_counter", 0)
    call_id = uuid.uuid4().hex
    canonical_events = canonical_events or []
    ai_start = time.monotonic()
    wall_start = time.time()
    ai_failed_emitted = False
    global_seed = getattr(getattr(ctx.config, "determinism", None), "seed", None)
    call_seed = resolve_ai_call_seed(
        explicit_seed=_seed_from_structured_input(input_structured),
        global_seed=global_seed,
        model=model_name,
        user_input=user_input,
        context={
            "ai_profile": profile.name,
            "flow": getattr(getattr(ctx, "flow", None), "name", ""),
            "input_format": input_format or "text",
            "provider": provider_name,
        },
    )
    memory_enabled = bool(
        getattr(profile, "memory", None)
        and (profile.memory.short_term or profile.memory.semantic or profile.memory.profile)
    )
    canonical_events.append(
        build_ai_call_started(
            call_id=call_id,
            provider=provider_name,
            model=model_name,
            input_text=user_input,
            tools_declared_count=len(profile.exposed_tools),
            memory_enabled=memory_enabled,
        )
    )
    append_explain_entry(
        ctx,
        stage="generation",
        event_type="start",
        inputs={
            "input_format": input_format or "text",
            "user_input": user_input,
        },
        seed=call_seed,
        provider=provider_name,
        model=model_name,
        parameters={
            "tools_declared_count": len(profile.exposed_tools),
            "memory_enabled": memory_enabled,
        },
        metadata={
            "agent_name": agent_name,
        },
    )
    provider = _resolve_provider(ctx, provider_name)
    capabilities = get_provider_capabilities(provider_name)

    def _text_only_call():
        response = provider.ask(
            model=model_name,
            system_prompt=profile.system_prompt,
            user_input=user_input,
            tools=[{"name": name} for name in profile.exposed_tools],
            memory=memory_context,
            tool_results=[],
        )
        output = extract_response_text(response)
        return normalize_ai_text(output, provider_name=provider_name, secret_values=secret_values)

    try:
        if not profile.exposed_tools or not capabilities.supports_tools:
            output_text, _cache_hit = run_cached_ai_text_call(
                ctx,
                provider=provider_name,
                model=model_name,
                system_prompt=profile.system_prompt,
                user_input=user_input,
                tools=list(profile.exposed_tools),
                memory=memory_context,
                compute=_text_only_call,
            )
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_completed(
                    call_id=call_id,
                    provider=provider_name,
                    model=model_name,
                    output_text=output_text,
                    duration_ms=duration_ms,
                    tokens_in=None,
                    tokens_out=None,
                )
            )
            record_ai_event(
                ctx,
                profile.name,
                provider_name,
                model_name,
                status="ok",
                input_text=user_input,
                output_text=output_text,
                started_at=wall_start,
                duration_ms=duration_ms,
            )
            record_ai_metrics(
                ctx,
                input_text=user_input,
                output_text=output_text,
                start_step=start_step,
            )
            run_shadow_compare(
                ctx,
                provider=provider,
                profile=profile,
                provider_name=provider_name,
                selected_model=model_name,
                shadow_model=shadow_model,
                canary_hit=canary_hit,
                user_input=user_input,
                memory_context=memory_context,
                output_text=output_text,
                secret_values=secret_values,
            )
            append_explain_entry(
                ctx,
                stage="generation",
                event_type="finish",
                outputs={"output": output_text},
                seed=call_seed,
                provider=provider_name,
                model=model_name,
                metadata={
                    "cache_hit": _cache_hit,
                    "tools_used": 0,
                },
            )
            ctx.last_ai_provider = provider_name
            return output_text, canonical_events

        from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
        from namel3ss.runtime.tool_calls.pipeline import run_ai_tool_pipeline
        from namel3ss.runtime.tool_calls.provider_iface import get_provider_adapter

        adapter = get_provider_adapter(provider_name, provider, model=model_name, system_prompt=profile.system_prompt)
        if adapter is None:
            output_text, _cache_hit = run_cached_ai_text_call(
                ctx,
                provider=provider_name,
                model=model_name,
                system_prompt=profile.system_prompt,
                user_input=user_input,
                tools=list(profile.exposed_tools),
                memory=memory_context,
                compute=_text_only_call,
            )
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_completed(
                    call_id=call_id,
                    provider=provider_name,
                    model=model_name,
                    output_text=output_text,
                    duration_ms=duration_ms,
                    tokens_in=None,
                    tokens_out=None,
                )
            )
            record_ai_event(
                ctx,
                profile.name,
                provider_name,
                model_name,
                status="ok",
                input_text=user_input,
                output_text=output_text,
                started_at=wall_start,
                duration_ms=duration_ms,
            )
            record_ai_metrics(
                ctx,
                input_text=user_input,
                output_text=output_text,
                start_step=start_step,
            )
            run_shadow_compare(
                ctx,
                provider=provider,
                profile=profile,
                provider_name=provider_name,
                selected_model=model_name,
                shadow_model=shadow_model,
                canary_hit=canary_hit,
                user_input=user_input,
                memory_context=memory_context,
                output_text=output_text,
                secret_values=secret_values,
            )
            append_explain_entry(
                ctx,
                stage="generation",
                event_type="finish",
                outputs={"output": output_text},
                seed=call_seed,
                provider=provider_name,
                model=model_name,
                metadata={
                    "cache_hit": _cache_hit,
                    "tools_used": 0,
                },
            )
            ctx.last_ai_provider = provider_name
            return output_text, canonical_events

        messages: list[dict] = []
        if profile.system_prompt:
            messages.append({"role": "system", "content": profile.system_prompt})
        messages.append({"role": "user", "content": user_input})
        tool_decls = []
        for name in profile.exposed_tools:
            tool_decl = ctx.tools.get(name)
            input_schema = build_json_schema(tool_decl.input_fields) if tool_decl else {"type": "object", "properties": {}}
            output_schema = build_json_schema(tool_decl.output_fields) if tool_decl else None
            tool_decls.append(
                ToolDeclaration(
                    name=name,
                    description=None,
                    input_schema=input_schema,
                    output_schema=output_schema,
                    strict=False,
                )
            )
        policy = ToolCallPolicy(allow_tools=True, max_calls=3, strict_json=True, retry_on_parse_error=False, max_total_turns=6)

        def _tool_executor(tool_name: str, args: dict[str, object]):
            return execute_tool_call_with_outcome(ctx, tool_name, dict(args))

        previous_source = ctx.tool_call_source
        ctx.tool_call_source = "ai"
        try:
            output_text = run_ai_tool_pipeline(
                adapter=adapter,
                call_id=call_id,
                provider_name=provider_name,
                model=model_name,
                messages=messages,
                tools=tool_decls,
                policy=policy,
                tool_executor=_tool_executor,
                canonical_events=canonical_events,
                tool_events=tool_events,
            )
            output_text = normalize_ai_text(output_text, provider_name=provider_name, secret_values=secret_values)
        finally:
            ctx.tool_call_source = previous_source
        duration_ms = int((time.monotonic() - ai_start) * 1000)
        canonical_events.append(
            build_ai_call_completed(
                call_id=call_id,
                provider=provider_name,
                model=model_name,
                output_text=output_text,
                duration_ms=duration_ms,
                tokens_in=None,
                tokens_out=None,
            )
        )
        record_ai_event(
            ctx,
            profile.name,
            provider_name,
            model_name,
            status="ok",
            input_text=user_input,
            output_text=output_text,
            started_at=wall_start,
            duration_ms=duration_ms,
        )
        record_ai_metrics(
            ctx,
            input_text=user_input,
            output_text=output_text,
            start_step=start_step,
        )
        run_shadow_compare(
            ctx,
            provider=provider,
            profile=profile,
            provider_name=provider_name,
            selected_model=model_name,
            shadow_model=shadow_model,
            canary_hit=canary_hit,
            user_input=user_input,
            memory_context=memory_context,
            output_text=output_text,
            secret_values=secret_values,
        )
        append_explain_entry(
            ctx,
            stage="generation",
            event_type="finish",
            outputs={"output": output_text},
            seed=call_seed,
            provider=provider_name,
            model=model_name,
            metadata={
                "cache_hit": None,
                "tools_used": len([event for event in tool_events if event.get("type") == "call"]),
            },
        )
        ctx.last_ai_provider = provider_name
        return output_text, canonical_events
    except Exception as err:
        mark_boundary(err, "ai")
        append_explain_entry(
            ctx,
            stage="generation",
            event_type="error",
            outputs={"error": str(err)},
            seed=call_seed,
            provider=provider_name,
            model=model_name,
            metadata=None,
        )
        diagnostic = extract_provider_diagnostic(err)
        if diagnostic:
            canonical_events.append(
                build_ai_provider_error(
                    call_id=call_id,
                    provider=provider_name,
                    model=model_name,
                    diagnostic=diagnostic,
                )
            )
        if not ai_failed_emitted:
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_failed(
                    call_id=call_id,
                    provider=provider_name,
                    model=model_name,
                    error_type=err.__class__.__name__,
                    error_message=str(err),
                    duration_ms=duration_ms,
                )
            )
            ai_failed_emitted = True
        record_ai_event(
            ctx,
            profile.name,
            provider_name,
            model_name,
            status="error",
            input_text=user_input,
            output_text=None,
            started_at=wall_start,
            duration_ms=int((time.monotonic() - ai_start) * 1000),
            error=err,
        )
        append_ai_error_trace(
            ctx,
            profile,
            agent_name,
            user_input,
            memory_context,
            tool_events,
            canonical_events,
            model_name=model_name,
            input_format=input_format,
            input_structured=input_structured,
        )
        raise


__all__ = ["run_ai_with_tools"]
