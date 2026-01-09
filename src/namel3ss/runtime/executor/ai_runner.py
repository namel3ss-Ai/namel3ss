from __future__ import annotations

import time
import uuid
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.parallel.isolation import ensure_ai_call_allowed
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.runtime.tools.field_schema import build_json_schema
from namel3ss.runtime.tools.executor import execute_tool_call_with_outcome
from namel3ss.runtime.boundary import mark_boundary
from namel3ss.runtime.values.normalize import unwrap_text
import namel3ss.runtime.memory.api as memory_api
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.traces.builders import (
    build_ai_call_completed,
    build_ai_call_failed,
    build_ai_provider_error,
    build_ai_call_started,
    build_memory_recall,
    build_memory_write,
)
from namel3ss.traces.redact import redact_memory_context
from namel3ss.observe import record_event, summarize_value
from namel3ss.secrets import collect_secret_values


def execute_ask_ai(ctx: ExecutionContext, expr: ir.AskAIStmt) -> str:
    try:
        ensure_ai_call_allowed(ctx, expr.ai_name, line=expr.line, column=expr.column)
        if expr.ai_name not in ctx.ai_profiles:
            raise Namel3ssError(
                f"Unknown AI '{expr.ai_name}'",
                line=expr.line,
                column=expr.column,
            )
        profile = ctx.ai_profiles[expr.ai_name]
        user_input = evaluate_expression(ctx, expr.input_expr)
        user_input = unwrap_text(user_input)
        if not isinstance(user_input, str):
            raise Namel3ssError("AI input must be a string", line=expr.line, column=expr.column)
        record_step(
            ctx,
            kind="ai_call",
            what=f"asked ai {expr.ai_name}",
            line=expr.line,
            column=expr.column,
        )
        try:
            recall_pack = memory_api.recall_with_events(
                ctx.memory_manager,
                profile,
                user_input,
                ctx.state,
                identity=ctx.identity,
                project_root=ctx.project_root,
                app_path=getattr(ctx, "app_path", None),
            )
        except Exception as err:
            mark_boundary(err, "memory")
            raise
        memory_context = recall_pack.payload
        recall_events = recall_pack.events
        recall_meta = recall_pack.meta
        recalled = _flatten_memory_context(memory_context)
        deterministic_hash = recall_pack.proof.get("recall_hash") or ctx.memory_manager.recall_hash(recalled)
        canonical_events: list[dict] = []
        canonical_events.append(
            build_memory_recall(
                ai_profile=profile.name,
                session=ctx.memory_manager.session_id(ctx.state),
                query=user_input,
                recalled=recalled,
                policy=_memory_policy(profile, ctx.memory_manager),
                deterministic_hash=deterministic_hash,
                spaces_consulted=recall_meta.get("spaces_consulted"),
                recall_counts=recall_meta.get("recall_counts"),
                phase_counts=recall_meta.get("phase_counts"),
                current_phase=recall_meta.get("current_phase"),
            )
        )
        if recall_events:
            canonical_events.extend(recall_events)
        tool_events: list[dict] = []
        response_output, canonical_events = run_ai_with_tools(
            ctx,
            profile,
            user_input,
            memory_context,
            tool_events,
            canonical_events=canonical_events,
            agent_name=None,
        )
        try:
            record_pack = memory_api.record_with_events(
                ctx.memory_manager,
                profile,
                ctx.state,
                user_input,
                response_output,
                tool_events,
                identity=ctx.identity,
                project_root=ctx.project_root,
                app_path=getattr(ctx, "app_path", None),
            )
        except Exception as err:
            mark_boundary(err, "memory")
            raise
        written = record_pack.payload
        governance_events = record_pack.events
        canonical_events.append(
            build_memory_write(
                ai_profile=profile.name,
                session=ctx.memory_manager.session_id(ctx.state),
                written=written,
                reason="interaction_recorded",
            )
        )
        if governance_events:
            canonical_events.extend(governance_events)
        canonical_events = append_explanation_events(canonical_events)
        trace = AITrace(
            ai_name=expr.ai_name,
            ai_profile_name=expr.ai_name,
            agent_name=None,
            model=profile.model,
            system_prompt=profile.system_prompt,
            input=user_input,
            output=response_output,
            memory=redact_memory_context(memory_context),
            tool_calls=[e for e in tool_events if e.get("type") == "call"],
            tool_results=[e for e in tool_events if e.get("type") == "result"],
            canonical_events=canonical_events,
        )
        ctx.traces.append(trace)
        _flush_pending_tool_traces(ctx)
        if expr.target in ctx.constants:
            raise Namel3ssError(f"Cannot assign to constant '{expr.target}'", line=expr.line, column=expr.column)
        provider_name = (getattr(profile, "provider", "mock") or "mock").lower()
        secret_values = collect_secret_values(ctx.config)
        output_text = normalize_ai_text(
            response_output,
            provider_name=provider_name,
            secret_values=secret_values,
        )
        ctx.locals[expr.target] = output_text
        ctx.last_value = output_text
        return output_text
    except Exception as err:
        _flush_pending_tool_traces(ctx)
        mark_boundary(err, "ai")
        raise


def run_ai_with_tools(
    ctx: ExecutionContext,
    profile: ir.AIDecl,
    user_input: str,
    memory_context: dict,
    tool_events: list[dict],
    *,
    canonical_events: list[dict] | None = None,
    agent_name: str | None = None,
) -> tuple[str, list[dict]]:
    provider_name = (getattr(profile, "provider", "mock") or "mock").lower()
    secret_values = collect_secret_values(ctx.config)
    call_id = uuid.uuid4().hex
    canonical_events = canonical_events or []
    ai_start = time.monotonic()
    wall_start = time.time()
    ai_failed_emitted = False
    memory_enabled = bool(
        getattr(profile, "memory", None)
        and (profile.memory.short_term or profile.memory.semantic or profile.memory.profile)
    )
    canonical_events.append(
        build_ai_call_started(
            call_id=call_id,
            provider=provider_name,
            model=profile.model,
            input_text=user_input,
            tools_declared_count=len(profile.exposed_tools),
            memory_enabled=memory_enabled,
        )
    )
    provider = _resolve_provider(ctx, provider_name)
    capabilities = get_provider_capabilities(provider_name)

    def _text_only_call():
        response = provider.ask(
            model=profile.model,
            system_prompt=profile.system_prompt,
            user_input=user_input,
            tools=[{"name": name} for name in profile.exposed_tools],
            memory=memory_context,
            tool_results=[],
        )
        output = response.output if hasattr(response, "output") else response
        return normalize_ai_text(output, provider_name=provider_name, secret_values=secret_values)

    try:
        if not profile.exposed_tools or not capabilities.supports_tools:
            output_text = _text_only_call()
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_completed(
                    call_id=call_id,
                    provider=provider_name,
                    model=profile.model,
                    output_text=output_text,
                    duration_ms=duration_ms,
                    tokens_in=None,
                    tokens_out=None,
                )
            )
            _record_ai_event(
                ctx,
                profile.name,
                provider_name,
                profile.model,
                status="ok",
                input_text=user_input,
                output_text=output_text,
                started_at=wall_start,
                duration_ms=duration_ms,
            )
            ctx.last_ai_provider = provider_name
            return output_text, canonical_events

        from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
        from namel3ss.runtime.tool_calls.pipeline import run_ai_tool_pipeline
        from namel3ss.runtime.tool_calls.provider_iface import get_provider_adapter

        adapter = get_provider_adapter(provider_name, provider, model=profile.model, system_prompt=profile.system_prompt)
        if adapter is None:
            output_text = _text_only_call()
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_completed(
                    call_id=call_id,
                    provider=provider_name,
                    model=profile.model,
                    output_text=output_text,
                    duration_ms=duration_ms,
                    tokens_in=None,
                    tokens_out=None,
                )
            )
            _record_ai_event(
                ctx,
                profile.name,
                provider_name,
                profile.model,
                status="ok",
                input_text=user_input,
                output_text=output_text,
                started_at=wall_start,
                duration_ms=duration_ms,
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
                model=profile.model,
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
                model=profile.model,
                output_text=output_text,
                duration_ms=duration_ms,
                tokens_in=None,
                tokens_out=None,
            )
        )
        _record_ai_event(
            ctx,
            profile.name,
            provider_name,
            profile.model,
            status="ok",
            input_text=user_input,
            output_text=output_text,
            started_at=wall_start,
            duration_ms=duration_ms,
        )
        ctx.last_ai_provider = provider_name
        return output_text, canonical_events
    except Exception as err:
        mark_boundary(err, "ai")
        diagnostic = _extract_provider_diagnostic(err)
        if diagnostic:
            canonical_events.append(
                build_ai_provider_error(
                    call_id=call_id,
                    provider=provider_name,
                    model=profile.model,
                    diagnostic=diagnostic,
                )
            )
        if not ai_failed_emitted:
            duration_ms = int((time.monotonic() - ai_start) * 1000)
            canonical_events.append(
                build_ai_call_failed(
                    call_id=call_id,
                    provider=provider_name,
                    model=profile.model,
                    error_type=err.__class__.__name__,
                    error_message=str(err),
                    duration_ms=duration_ms,
                )
            )
            ai_failed_emitted = True
        _record_ai_event(
            ctx,
            profile.name,
            provider_name,
            profile.model,
            status="error",
            input_text=user_input,
            output_text=None,
            started_at=wall_start,
            duration_ms=int((time.monotonic() - ai_start) * 1000),
            error=err,
        )
        _append_ai_error_trace(
            ctx,
            profile,
            agent_name,
            user_input,
            memory_context,
            tool_events,
            canonical_events,
        )
        raise


def _flatten_memory_context(context: dict) -> list[dict]:
    ordered: list[dict] = []
    for key in ("short_term", "semantic", "profile"):
        ordered.extend(context.get(key, []))
    return ordered


def _memory_policy(profile: ir.AIDecl, memory_manager: MemoryManager) -> dict:
    return memory_manager.policy_snapshot(profile)


def _resolve_provider(ctx: ExecutionContext, provider_name: str):
    key = provider_name.lower()
    _ = get_provider_capabilities(key)  # read-only lookup for capability metadata
    if key in ctx.provider_cache:
        return ctx.provider_cache[key]
    provider = get_provider(key, ctx.config)
    ctx.provider_cache[key] = provider
    return provider


def _record_ai_event(
    ctx: ExecutionContext,
    ai_name: str,
    provider: str,
    model: str,
    *,
    status: str,
    input_text: str,
    output_text: str | None,
    started_at: float,
    duration_ms: int,
    error: Exception | None = None,
) -> None:
    if not ctx.project_root:
        return
    secret_values = collect_secret_values(ctx.config)
    event = {
        "type": "ai_call",
        "flow_name": getattr(ctx.flow, "name", None),
        "ai_name": ai_name,
        "provider": provider,
        "model": model,
        "status": status,
        "time_start": started_at,
        "time_end": started_at + (duration_ms / 1000.0),
        "duration_ms": duration_ms,
        "redacted_input_summary": summarize_value(input_text, secret_values=secret_values),
        "redacted_output_summary": summarize_value(output_text or "", secret_values=secret_values),
    }
    if error:
        event["error_type"] = error.__class__.__name__
        event["error_message"] = str(error)
    record_event(Path(ctx.project_root), event, secret_values=secret_values)


def _flush_pending_tool_traces(ctx: ExecutionContext) -> None:
    if not ctx.pending_tool_traces:
        return
    ctx.traces.extend(ctx.pending_tool_traces)
    ctx.pending_tool_traces.clear()


def _extract_provider_diagnostic(err: Exception) -> dict[str, object] | None:
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


def _append_ai_error_trace(
    ctx: ExecutionContext,
    profile: ir.AIDecl,
    agent_name: str | None,
    user_input: str,
    memory_context: dict,
    tool_events: list[dict],
    canonical_events: list[dict],
) -> None:
    trace = AITrace(
        ai_name=profile.name,
        ai_profile_name=profile.name,
        agent_name=agent_name,
        model=profile.model,
        system_prompt=profile.system_prompt,
        input=user_input,
        output="",
        memory=redact_memory_context(memory_context),
        tool_calls=[e for e in tool_events if e.get("type") == "call"],
        tool_results=[e for e in tool_events if e.get("type") == "result"],
        canonical_events=canonical_events,
    )
    ctx.traces.append(trace)
