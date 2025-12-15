from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.ai_runner import execute_ask_ai
from namel3ss.runtime.executor.agents import execute_run_agent, execute_run_agents_parallel
from namel3ss.runtime.executor.assign import assign
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.records_ops import handle_find, handle_save
from namel3ss.runtime.executor.signals import _ReturnSignal


def execute_statement(ctx: ExecutionContext, stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.Let):
        value = evaluate_expression(ctx, stmt.expression)
        ctx.locals[stmt.name] = value
        if stmt.constant:
            ctx.constants.add(stmt.name)
        ctx.last_value = value
        return
    if isinstance(stmt, ir.Set):
        value = evaluate_expression(ctx, stmt.expression)
        assign(ctx, stmt.target, value, stmt)
        ctx.last_value = value
        return
    if isinstance(stmt, ir.If):
        condition_value = evaluate_expression(ctx, stmt.condition)
        if not isinstance(condition_value, bool):
            raise Namel3ssError(
                "Condition must evaluate to a boolean",
                line=stmt.line,
                column=stmt.column,
            )
        branch = stmt.then_body if condition_value else stmt.else_body
        for child in branch:
            execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.Return):
        value = evaluate_expression(ctx, stmt.expression)
        raise _ReturnSignal(value)
    if isinstance(stmt, ir.Repeat):
        count_value = evaluate_expression(ctx, stmt.count)
        if not isinstance(count_value, int):
            raise Namel3ssError("Repeat count must be an integer", line=stmt.line, column=stmt.column)
        if count_value < 0:
            raise Namel3ssError("Repeat count cannot be negative", line=stmt.line, column=stmt.column)
        for _ in range(count_value):
            for child in stmt.body:
                execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.ForEach):
        iterable_value = evaluate_expression(ctx, stmt.iterable)
        if not isinstance(iterable_value, list):
            raise Namel3ssError("For-each expects a list", line=stmt.line, column=stmt.column)
        for item in iterable_value:
            ctx.locals[stmt.name] = item
            for child in stmt.body:
                execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.Match):
        subject = evaluate_expression(ctx, stmt.expression)
        matched = False
        for case in stmt.cases:
            pattern_value = evaluate_expression(ctx, case.pattern)
            if subject == pattern_value:
                matched = True
                for child in case.body:
                    execute_statement(ctx, child)
                break
        if not matched and stmt.otherwise is not None:
            for child in stmt.otherwise:
                execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.TryCatch):
        try:
            for child in stmt.try_body:
                execute_statement(ctx, child)
        except Namel3ssError as err:
            ctx.locals[stmt.catch_var] = err
            for child in stmt.catch_body:
                execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.AskAIStmt):
        execute_ask_ai(ctx, stmt)
        return
    if isinstance(stmt, ir.RunAgentStmt):
        execute_run_agent(ctx, stmt)
        return
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        execute_run_agents_parallel(ctx, stmt)
        return
    if isinstance(stmt, ir.Save):
        handle_save(ctx, stmt)
        return
    if isinstance(stmt, ir.Find):
        handle_find(ctx, stmt)
        return
    raise Namel3ssError(f"Unsupported statement type: {type(stmt)}", line=stmt.line, column=stmt.column)
