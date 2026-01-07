from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.ai_runner import execute_ask_ai
from namel3ss.runtime.executor.agents import execute_run_agent, execute_run_agents_parallel


def execute_ask_ai_stmt(ctx, stmt: ir.AskAIStmt) -> None:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot call ai", line=stmt.line, column=stmt.column)
    execute_ask_ai(ctx, stmt)


def execute_run_agent_stmt(ctx, stmt: ir.RunAgentStmt) -> None:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot call agents", line=stmt.line, column=stmt.column)
    record_step(
        ctx,
        kind="statement_run_agent",
        what=f"ran agent {stmt.agent_name}",
        line=stmt.line,
        column=stmt.column,
    )
    execute_run_agent(ctx, stmt)


def execute_run_agents_parallel_stmt(ctx, stmt: ir.RunAgentsParallelStmt) -> None:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot call agents", line=stmt.line, column=stmt.column)
    record_step(
        ctx,
        kind="statement_run_agents_parallel",
        what=f"ran {len(stmt.entries)} agents in parallel",
        line=stmt.line,
        column=stmt.column,
    )
    execute_run_agents_parallel(ctx, stmt)


__all__ = ["execute_ask_ai_stmt", "execute_run_agent_stmt", "execute_run_agents_parallel_stmt"]
