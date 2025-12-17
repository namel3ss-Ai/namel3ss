from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.executor.ai_runner import run_ai_with_tools
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression


def execute_run_agent(ctx: ExecutionContext, stmt: ir.RunAgentStmt) -> None:
    output, trace = run_agent_call(ctx, stmt.agent_name, stmt.input_expr, stmt.line, stmt.column)
    ctx.traces.append(trace)
    if stmt.target in ctx.constants:
        raise Namel3ssError(f"Cannot assign to constant '{stmt.target}'", line=stmt.line, column=stmt.column)
    ctx.locals[stmt.target] = output
    ctx.last_value = output


def execute_run_agents_parallel(ctx: ExecutionContext, stmt: ir.RunAgentsParallelStmt) -> None:
    if len(stmt.entries) > 3:
        raise Namel3ssError("Parallel agent limit exceeded")
    results: list[str] = []
    child_traces: list[dict] = []
    for entry in stmt.entries:
        try:
            output, trace = run_agent_call(ctx, entry.agent_name, entry.input_expr, entry.line, entry.column)
        except Namel3ssError as err:
            raise Namel3ssError(f"Agent '{entry.agent_name}' failed: {err}", line=entry.line, column=entry.column) from err
        results.append(output)
        child_traces.append(_trace_to_dict(trace))
    ctx.locals[stmt.target] = results
    ctx.last_value = results
    ctx.traces.append({"type": "parallel_agents", "target": stmt.target, "agents": child_traces})


def run_agent_call(ctx: ExecutionContext, agent_name: str, input_expr, line: int | None, column: int | None):
    ctx.agent_calls += 1
    if ctx.agent_calls > 5:
        raise Namel3ssError("Agent call limit exceeded in flow")
    if agent_name not in ctx.agents:
        raise Namel3ssError(f"Unknown agent '{agent_name}'", line=line, column=column)
    agent = ctx.agents[agent_name]
    ai_profile = ctx.ai_profiles.get(agent.ai_name)
    if ai_profile is None:
        raise Namel3ssError(f"Agent '{agent.name}' references unknown AI '{agent.ai_name}'", line=line, column=column)
    user_input = evaluate_expression(ctx, input_expr)
    if not isinstance(user_input, str):
        raise Namel3ssError("Agent input must be a string", line=line, column=column)
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
    memory_context = ctx.memory_manager.recall_context(profile_override, user_input, ctx.state)
    tool_events: list[dict] = []
    response_output = run_ai_with_tools(ctx, profile_override, user_input, memory_context, tool_events)
    trace = AITrace(
        ai_name=profile_override.name,
        ai_profile_name=profile_override.name,
        agent_name=agent.name,
        model=profile_override.model,
        system_prompt=profile_override.system_prompt,
        input=user_input,
        output=response_output,
        memory=memory_context,
        tool_calls=[e for e in tool_events if e.get("type") == "call"],
        tool_results=[e for e in tool_events if e.get("type") == "result"],
    )
    ctx.memory_manager.record_interaction(profile_override, ctx.state, user_input, response_output, tool_events)
    return response_output, trace


def _trace_to_dict(trace: AITrace) -> dict:
    return {
        "ai_name": trace.ai_name,
        "ai_profile_name": trace.ai_profile_name,
        "agent_name": trace.agent_name,
        "model": trace.model,
        "system_prompt": trace.system_prompt,
        "input": trace.input,
        "output": trace.output,
        "memory": trace.memory,
        "tool_calls": trace.tool_calls,
        "tool_results": trace.tool_results,
    }
