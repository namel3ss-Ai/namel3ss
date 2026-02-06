from __future__ import annotations

import namel3ss.runtime.memory.api as memory_api
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.input_format import prepare_ai_input
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.boundary import mark_boundary
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.ai_runner_support import flush_pending_tool_traces
from namel3ss.runtime.executor.ai_tool_pipeline import run_ai_with_tools
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.parallel.isolation import ensure_ai_call_allowed
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.secrets import collect_secret_values
from namel3ss.traces.builders import build_memory_recall, build_memory_write
from namel3ss.traces.redact import redact_memory_context


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
        input_value = evaluate_expression(ctx, expr.input_expr)
        input_text, input_structured, input_format = prepare_ai_input(
            input_value,
            mode=getattr(expr, "input_mode", "text"),
            line=expr.line,
            column=expr.column,
            project_root=ctx.project_root,
        )
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
                input_text,
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
        recalled: list[dict] = []
        for key in ("short_term", "semantic", "profile"):
            recalled.extend(memory_context.get(key, []))
        deterministic_hash = recall_pack.proof.get("recall_hash") or ctx.memory_manager.recall_hash(recalled)
        canonical_events: list[dict] = []
        canonical_events.append(
            build_memory_recall(
                ai_profile=profile.name,
                session=ctx.memory_manager.session_id(ctx.state),
                query=input_text,
                recalled=recalled,
                policy=ctx.memory_manager.policy_snapshot(profile),
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
            input_text,
            memory_context,
            tool_events,
            canonical_events=canonical_events,
            agent_name=None,
            input_format=input_format,
            input_structured=input_structured,
        )
        try:
            record_pack = memory_api.record_with_events(
                ctx.memory_manager,
                profile,
                ctx.state,
                input_text,
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
        trace_model = profile.model
        for event in canonical_events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "ai_call_started":
                continue
            candidate = event.get("model")
            if isinstance(candidate, str) and candidate.strip():
                trace_model = candidate
                break
        trace = AITrace(
            ai_name=expr.ai_name,
            ai_profile_name=expr.ai_name,
            agent_name=None,
            model=trace_model,
            system_prompt=profile.system_prompt,
            input=input_text,
            input_structured=input_structured,
            input_format=input_format,
            output=response_output,
            memory=redact_memory_context(memory_context),
            tool_calls=[e for e in tool_events if e.get("type") == "call"],
            tool_results=[e for e in tool_events if e.get("type") == "result"],
            canonical_events=canonical_events,
        )
        ctx.traces.append(trace)
        flush_pending_tool_traces(ctx)
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
        flush_pending_tool_traces(ctx)
        mark_boundary(err, "ai")
        raise


__all__ = ["execute_ask_ai"]
