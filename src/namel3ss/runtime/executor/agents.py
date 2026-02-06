from __future__ import annotations

from namel3ss.agents.ids import agent_id_from_name
from namel3ss.agents.orchestration import MergeCandidate, build_merge_trace_events, merge_agent_candidates
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.executor.ai_runner import run_ai_with_tools
from namel3ss.runtime.executor.ai_runner_support import flush_pending_tool_traces as _flush_pending_tool_traces
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.parallel.isolation import ensure_agent_call_allowed
from namel3ss.runtime.ai.input_format import prepare_ai_input
import namel3ss.runtime.memory.api as memory_api
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.memory_explain import append_explanation_events
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.memory_lanes.model import agent_lane_key
from namel3ss.traces.builders import (
    build_agent_step_end,
    build_agent_step_start,
    build_memory_recall,
    build_memory_write,
)
from namel3ss.traces.redact import redact_memory_context
from namel3ss.runtime.values.normalize import ensure_object


def execute_run_agent(ctx: ExecutionContext, stmt: ir.RunAgentStmt) -> None:
    agent = ctx.agents.get(stmt.agent_name)
    agent_name = agent.name if agent else stmt.agent_name
    agent_id = _resolve_agent_id(agent) if agent else None
    ai_name = agent.ai_name if agent else None
    role = agent.role if agent else None
    reason = _agent_step_reason(ctx)
    start_step = record_step(
        ctx,
        kind="agent_step_start",
        what=f"agent {agent_name} started",
        because=reason,
        data=_agent_step_data(agent_name, agent_id, role),
        line=stmt.line,
        column=stmt.column,
    )
    ctx.traces.append(
        build_agent_step_start(
            agent_name=agent_name,
            agent_id=agent_id,
            ai_name=ai_name,
            role=role,
            step_id=start_step.id,
            reason=reason,
        )
    )
    try:
        output, trace, written_count = run_agent_call(
            ctx,
            stmt.agent_name,
            stmt.input_expr,
            getattr(stmt, "input_mode", "text"),
            stmt.line,
            stmt.column,
            agent_id=agent_id,
            role=role,
        )
        ctx.traces.append(trace)
        end_step = record_step(
            ctx,
            kind="agent_step_end",
            what=f"agent {agent_name} completed",
            because=reason,
            data=_agent_step_data(agent_name, agent_id, role),
            line=stmt.line,
            column=stmt.column,
        )
        memory_facts = dict(_agent_memory_facts(ctx, agent_id))
        memory_facts["last_updated_step"] = end_step.id if written_count else None
        ctx.traces.append(
            build_agent_step_end(
                agent_name=agent_name,
                agent_id=agent_id,
                ai_name=ai_name,
                role=role,
                step_id=end_step.id,
                reason=reason,
                status="ok",
                memory_facts=memory_facts,
            )
        )
        _flush_pending_tool_traces(ctx)
        if stmt.target in ctx.constants:
            raise Namel3ssError(f"Cannot assign to constant '{stmt.target}'", line=stmt.line, column=stmt.column)
        ctx.locals[stmt.target] = output
        ctx.last_value = output
    except Exception as err:
        end_step = record_step(
            ctx,
            kind="agent_step_end",
            what=f"agent {agent_name} failed",
            because=reason,
            data=_agent_step_data(agent_name, agent_id, role),
            line=stmt.line,
            column=stmt.column,
        )
        ctx.traces.append(
            build_agent_step_end(
                agent_name=agent_name,
                agent_id=agent_id,
                ai_name=ai_name,
                role=role,
                step_id=end_step.id,
                reason=reason,
                status="error",
                error_message=str(err),
            )
        )
        _flush_pending_tool_traces(ctx)
        raise


def execute_run_agents_parallel(ctx: ExecutionContext, stmt: ir.RunAgentsParallelStmt) -> None:
    if len(stmt.entries) > 3:
        raise Namel3ssError("Parallel agent limit exceeded")
    reason = _agent_step_reason(ctx)
    results: list[object] = []
    child_traces: list[dict] = []
    candidates: list[MergeCandidate] = []
    for entry in stmt.entries:
        agent = ctx.agents.get(entry.agent_name)
        agent_name = agent.name if agent else entry.agent_name
        agent_id = _resolve_agent_id(agent) if agent else None
        ai_name = agent.ai_name if agent else None
        role = agent.role if agent else None
        start_step = record_step(
            ctx,
            kind="agent_step_start",
            what=f"agent {agent_name} started",
            because=reason,
            data=_agent_step_data(agent_name, agent_id, role),
            line=entry.line,
            column=entry.column,
        )
        ctx.traces.append(
            build_agent_step_start(
                agent_name=agent_name,
                agent_id=agent_id,
                ai_name=ai_name,
                role=role,
                step_id=start_step.id,
                reason=reason,
            )
        )
        try:
            output, trace, written_count = run_agent_call(
                ctx,
                entry.agent_name,
                entry.input_expr,
                getattr(entry, "input_mode", "text"),
                entry.line,
                entry.column,
                agent_id=agent_id,
                role=role,
            )
        except Namel3ssError as err:
            end_step = record_step(
                ctx,
                kind="agent_step_end",
                what=f"agent {agent_name} failed",
                because=reason,
                data=_agent_step_data(agent_name, agent_id, role),
                line=entry.line,
                column=entry.column,
            )
            ctx.traces.append(
                build_agent_step_end(
                    agent_name=agent_name,
                    agent_id=agent_id,
                    ai_name=ai_name,
                    role=role,
                    step_id=end_step.id,
                    reason=reason,
                    status="error",
                    error_message=str(err),
                )
            )
            _flush_pending_tool_traces(ctx)
            raise Namel3ssError(f"Agent '{entry.agent_name}' failed: {err}", line=entry.line, column=entry.column) from err
        results.append(output)
        trace_dict = _trace_to_dict(trace)
        child_traces.append(trace_dict)
        candidates.append(MergeCandidate(agent_name=entry.agent_name, output=output))
        end_step = record_step(
            ctx,
            kind="agent_step_end",
            what=f"agent {agent_name} completed",
            because=reason,
            data=_agent_step_data(agent_name, agent_id, role),
            line=entry.line,
            column=entry.column,
        )
        memory_facts = dict(_agent_memory_facts(ctx, agent_id))
        memory_facts["last_updated_step"] = end_step.id if written_count else None
        ctx.traces.append(
            build_agent_step_end(
                agent_name=agent_name,
                agent_id=agent_id,
                ai_name=ai_name,
                role=role,
                step_id=end_step.id,
                reason=reason,
                status="ok",
                memory_facts=memory_facts,
            )
        )
    merge_policy = getattr(stmt, "merge", None)
    if merge_policy is not None:
        outcome = merge_agent_candidates(
            candidates,
            merge_policy,
            line=merge_policy.line or stmt.line,
            column=merge_policy.column or stmt.column,
        )
        ctx.locals[stmt.target] = outcome.output
        ctx.last_value = outcome.output
        ctx.traces.extend(build_merge_trace_events(outcome, merge_policy))
    else:
        ctx.locals[stmt.target] = results
        ctx.last_value = results
    wrapper = {"type": "parallel_agents", "target": stmt.target, "agents": child_traces}
    if merge_policy is not None:
        wrapper["merge_policy"] = merge_policy.policy
        wrapper["merge_selected"] = [candidates[idx].agent_name for idx in outcome.selected]
    ctx.traces.append(wrapper)
    _flush_pending_tool_traces(ctx)


def run_agent_call(
    ctx: ExecutionContext,
    agent_name: str,
    input_expr,
    input_mode: str,
    line: int | None,
    column: int | None,
    *,
    agent_id: str | None = None,
    role: str | None = None,
):
    ensure_agent_call_allowed(ctx, agent_name, line=line, column=column)
    ctx.agent_calls += 1
    if ctx.agent_calls > 5:
        raise Namel3ssError("Agent call limit exceeded in flow")
    if agent_name not in ctx.agents:
        raise Namel3ssError(f"Unknown agent '{agent_name}'", line=line, column=column)
    agent = ctx.agents[agent_name]
    resolved_agent_id = agent_id or _resolve_agent_id(agent)
    resolved_role = role if role is not None else agent.role
    ai_profile = ctx.ai_profiles.get(agent.ai_name)
    if ai_profile is None:
        raise Namel3ssError(f"Agent '{agent.name}' references unknown AI '{agent.ai_name}'", line=line, column=column)
    input_value = evaluate_expression(ctx, input_expr)
    input_text, input_structured, input_format = prepare_ai_input(
        input_value,
        mode=input_mode,
        line=line,
        column=column,
    )
    record_step(
        ctx,
        kind="ai_call",
        what=f"asked ai {ai_profile.name}",
        line=line,
        column=column,
    )
    profile_override = ir.AIDecl(
        name=ai_profile.name,
        model=ai_profile.model,
        provider=ai_profile.provider,
        system_prompt=agent.system_prompt or ai_profile.system_prompt,
        exposed_tools=list(ai_profile.exposed_tools),
        memory=ai_profile.memory,
        line=ai_profile.line,
        column=ai_profile.column,
    )
    recall_pack = memory_api.recall_with_events(
        ctx.memory_manager,
        profile_override,
        input_text,
        ctx.state,
        identity=ctx.identity,
        project_root=ctx.project_root,
        app_path=getattr(ctx, "app_path", None),
        agent_id=resolved_agent_id,
    )
    memory_context = recall_pack.payload
    recall_events = recall_pack.events
    recall_meta = recall_pack.meta
    recalled = _flatten_memory_context(memory_context)
    deterministic_hash = recall_pack.proof.get("recall_hash") or ctx.memory_manager.recall_hash(recalled)
    canonical_events: list[dict] = []
    canonical_events.append(
        build_memory_recall(
            ai_profile=profile_override.name,
            session=ctx.memory_manager.session_id(ctx.state),
            query=input_text,
            recalled=recalled,
            policy=_memory_policy(
                profile_override,
                ctx.memory_manager,
                agent_id=resolved_agent_id,
                project_root=ctx.project_root,
                app_path=getattr(ctx, "app_path", None),
            ),
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
        profile_override,
        input_text,
        memory_context,
        tool_events,
        canonical_events=canonical_events,
        agent_name=agent.name,
        input_format=input_format,
        input_structured=input_structured,
    )
    record_pack = memory_api.record_with_events(
        ctx.memory_manager,
        profile_override,
        ctx.state,
        input_text,
        response_output,
        tool_events,
        identity=ctx.identity,
        project_root=ctx.project_root,
        app_path=getattr(ctx, "app_path", None),
        agent_id=resolved_agent_id,
    )
    written = record_pack.payload
    governance_events = record_pack.events
    canonical_events.append(
        build_memory_write(
            ai_profile=profile_override.name,
            session=ctx.memory_manager.session_id(ctx.state),
            written=written,
            reason="interaction_recorded",
        )
    )
    if governance_events:
        canonical_events.extend(governance_events)
    canonical_events = append_explanation_events(canonical_events)
    trace_model = profile_override.model
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
        ai_name=profile_override.name,
        ai_profile_name=profile_override.name,
        agent_name=agent.name,
        model=trace_model,
        system_prompt=profile_override.system_prompt,
        input=input_text,
        input_structured=input_structured,
        input_format=input_format,
        output=response_output,
        memory=redact_memory_context(memory_context),
        tool_calls=[e for e in tool_events if e.get("type") == "call"],
        tool_results=[e for e in tool_events if e.get("type") == "result"],
        canonical_events=canonical_events,
        agent_id=resolved_agent_id,
        role=resolved_role,
    )
    output_value = ensure_object(response_output, key="text")
    return output_value, trace, len(written or [])


def _trace_to_dict(trace: AITrace) -> dict:
    return {
        "ai_name": trace.ai_name,
        "ai_profile_name": trace.ai_profile_name,
        "agent_name": trace.agent_name,
        "agent_id": getattr(trace, "agent_id", None),
        "role": getattr(trace, "role", None),
        "model": trace.model,
        "system_prompt": trace.system_prompt,
        "input": trace.input,
        "input_structured": getattr(trace, "input_structured", None),
        "input_format": getattr(trace, "input_format", None),
        "output": trace.output,
        "memory": trace.memory,
        "tool_calls": trace.tool_calls,
        "tool_results": trace.tool_results,
        "canonical_events": getattr(trace, "canonical_events", []),
    }


def _flatten_memory_context(context: dict) -> list[dict]:
    ordered: list[dict] = []
    for key in ("short_term", "semantic", "profile"):
        ordered.extend(context.get(key, []))
    return ordered


def _memory_policy(
    profile: ir.AIDecl,
    memory_manager: MemoryManager,
    *,
    agent_id: str | None,
    project_root: str | None,
    app_path: str | None,
) -> dict:
    return memory_manager.policy_snapshot(
        profile,
        agent_id=agent_id,
        project_root=project_root,
        app_path=app_path,
    )


def _resolve_agent_id(agent: ir.AgentDecl | None) -> str | None:
    if agent is None:
        return None
    if agent.agent_id:
        return agent.agent_id
    return agent_id_from_name(agent.name)


def _agent_step_reason(ctx: ExecutionContext) -> str:
    action_id = getattr(ctx, "flow_action_id", None)
    if action_id:
        return f"invoked by user action {action_id}"
    flow_name = getattr(getattr(ctx, "flow", None), "name", None)
    if flow_name:
        return f"invoked by flow {flow_name}"
    return "invoked by user action"


def _agent_step_data(agent_name: str, agent_id: str | None, role: str | None) -> dict:
    payload = {"agent_name": agent_name}
    if agent_id:
        payload["agent_id"] = agent_id
    if role:
        payload["role"] = role
    return payload


def _agent_memory_facts(ctx: ExecutionContext, agent_id: str | None) -> dict:
    if not agent_id:
        return {"keys": [], "counts": {"total": 0}}
    memory_manager = ctx.memory_manager
    memory_manager.ensure_restored(project_root=ctx.project_root, app_path=ctx.app_path)
    space_ctx = memory_manager.space_context(
        ctx.state,
        identity=ctx.identity,
        project_root=ctx.project_root,
        app_path=ctx.app_path,
    )
    store_key = agent_lane_key(space_ctx, space="project", agent_id=agent_id)
    profile = getattr(memory_manager, "profile", None)
    if profile is None:
        return {"keys": [], "counts": {"total": 0}}
    facts = getattr(profile, "_facts", {}).get(store_key, {})
    keys = sorted(str(key) for key in facts.keys())
    return {"keys": keys, "counts": {"total": len(keys)}}
