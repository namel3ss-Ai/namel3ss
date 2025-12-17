from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIToolCallResponse
from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.runtime.ai.trace import AITrace
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.tools.registry import execute_tool


def execute_ask_ai(ctx: ExecutionContext, expr: ir.AskAIStmt) -> str:
    if expr.ai_name not in ctx.ai_profiles:
        raise Namel3ssError(
            f"Unknown AI '{expr.ai_name}'",
            line=expr.line,
            column=expr.column,
        )
    profile = ctx.ai_profiles[expr.ai_name]
    user_input = evaluate_expression(ctx, expr.input_expr)
    if not isinstance(user_input, str):
        raise Namel3ssError("AI input must be a string", line=expr.line, column=expr.column)
    memory_context = ctx.memory_manager.recall_context(profile, user_input, ctx.state)
    tool_events: list[dict] = []
    response_output = run_ai_with_tools(ctx, profile, user_input, memory_context, tool_events)
    trace = AITrace(
        ai_name=expr.ai_name,
        ai_profile_name=expr.ai_name,
        agent_name=None,
        model=profile.model,
        system_prompt=profile.system_prompt,
        input=user_input,
        output=response_output,
        memory=memory_context,
        tool_calls=[e for e in tool_events if e.get("type") == "call"],
        tool_results=[e for e in tool_events if e.get("type") == "result"],
    )
    ctx.traces.append(trace)
    if expr.target in ctx.constants:
        raise Namel3ssError(f"Cannot assign to constant '{expr.target}'", line=expr.line, column=expr.column)
    ctx.locals[expr.target] = response_output
    ctx.last_value = response_output
    ctx.memory_manager.record_interaction(profile, ctx.state, user_input, response_output, tool_events)
    return response_output


def run_ai_with_tools(
    ctx: ExecutionContext,
    profile: ir.AIDecl,
    user_input: str,
    memory_context: dict,
    tool_events: list[dict],
) -> str:
    max_calls = 3
    tool_results: list[dict] = []
    provider_name = getattr(profile, "provider", "mock") or "mock"
    for _ in range(max_calls + 1):
        provider = _resolve_provider(ctx, provider_name)
        response = provider.ask(
            model=profile.model,
            system_prompt=profile.system_prompt,
            user_input=user_input,
            tools=[{"name": name} for name in profile.exposed_tools],
            memory=memory_context,
            tool_results=tool_results,
        )
        if isinstance(response, AIToolCallResponse):
            if response.tool_name not in profile.exposed_tools:
                raise Namel3ssError(f"AI requested unexposed tool '{response.tool_name}'")
            if not isinstance(response.args, dict):
                raise Namel3ssError("Tool call args must be a dictionary")
            tool_events.append({"type": "call", "name": response.tool_name, "args": response.args})
            result = execute_tool(response.tool_name, response.args)
            tool_events.append({"type": "result", "name": response.tool_name, "result": result})
            tool_results.append({"name": response.tool_name, "result": result})
            continue
        if not isinstance(response.output, str):
            raise Namel3ssError("AI response must be a string")
        return response.output
    raise Namel3ssError("AI exceeded maximum tool calls")


def _resolve_provider(ctx: ExecutionContext, provider_name: str):
    key = provider_name.lower()
    if key in ctx.provider_cache:
        return ctx.provider_cache[key]
    provider = get_provider(key, ctx.config)
    ctx.provider_cache[key] = provider
    return provider
