from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.ai_runner import execute_ask_ai
from namel3ss.runtime.executor.agents import execute_run_agent, execute_run_agents_parallel
from namel3ss.runtime.executor.assign import assign
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.records_ops import handle_create, handle_find, handle_save
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


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
                _condition_type_message(condition_value),
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
        if not is_number(count_value):
            raise Namel3ssError("Repeat count must be an integer", line=stmt.line, column=stmt.column)
        count_decimal = to_decimal(count_value)
        if not decimal_is_int(count_decimal):
            raise Namel3ssError("Repeat count must be an integer", line=stmt.line, column=stmt.column)
        if count_decimal < 0:
            raise Namel3ssError("Repeat count cannot be negative", line=stmt.line, column=stmt.column)
        for _ in range(int(count_decimal)):
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
    if isinstance(stmt, ir.Create):
        handle_create(ctx, stmt)
        return
    if isinstance(stmt, ir.Find):
        handle_find(ctx, stmt)
        return
    if isinstance(stmt, ir.ThemeChange):
        if stmt.value not in {"light", "dark", "system"}:
            raise Namel3ssError("Theme must be one of: light, dark, system", line=stmt.line, column=stmt.column)
        ctx.runtime_theme = stmt.value
        ctx.traces.append({"type": "theme_change", "value": stmt.value})
        ctx.last_value = stmt.value
        return
    raise Namel3ssError(f"Unsupported statement type: {type(stmt)}", line=stmt.line, column=stmt.column)


def _condition_type_message(value: object) -> str:
    kind = _value_kind(value)
    return build_guidance_message(
        what="If condition did not evaluate to true/false.",
        why=f"The condition evaluated to {kind}, but if/else requires a boolean.",
        fix="Use a comparison so the condition is boolean.",
        example="if total is greater than 10:\n  return true",
    )


def _value_kind(value: object) -> str:
    from namel3ss.utils.numbers import is_number

    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "list"
    return type(value).__name__
