from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.ai_runner import execute_ask_ai
from namel3ss.runtime.executor.agents import execute_run_agent, execute_run_agents_parallel
from namel3ss.runtime.executor.assign import assign
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.parallel.scheduler import execute_parallel_block
from namel3ss.runtime.execution.normalize import format_assignable, format_expression, summarize_value
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.records_ops import handle_create, handle_delete, handle_find, handle_save, handle_update
from namel3ss.runtime.executor.signals import _ReturnSignal
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def execute_statement(ctx: ExecutionContext, stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.Let):
        value = evaluate_expression(ctx, stmt.expression)
        ctx.locals[stmt.name] = value
        if stmt.constant:
            ctx.constants.add(stmt.name)
        record_step(
            ctx,
            kind="statement_let",
            what=f"set local {stmt.name}",
            line=stmt.line,
            column=stmt.column,
        )
        ctx.last_value = value
        return
    if isinstance(stmt, ir.Set):
        if getattr(ctx, "parallel_mode", False) and isinstance(stmt.target, ir.StatePath):
            raise Namel3ssError("Parallel tasks cannot change state", line=stmt.line, column=stmt.column)
        if getattr(ctx, "call_stack", []) and isinstance(stmt.target, ir.StatePath):
            raise Namel3ssError("Functions cannot change state", line=stmt.line, column=stmt.column)
        value = evaluate_expression(ctx, stmt.expression)
        assign(ctx, stmt.target, value, stmt)
        record_step(
            ctx,
            kind="statement_set",
            what=f"set {format_assignable(stmt.target)}",
            line=stmt.line,
            column=stmt.column,
        )
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
        condition_text = format_expression(stmt.condition)
        record_step(
            ctx,
            kind="decision_if",
            what=f"if {condition_text} was {_bool_label(condition_value)}",
            data={"condition": condition_text, "value": condition_value},
            line=stmt.line,
            column=stmt.column,
        )
        if condition_value:
            record_step(
                ctx,
                kind="branch_taken",
                what="took then branch",
                because="condition was true",
                line=stmt.line,
                column=stmt.column,
            )
            if stmt.else_body:
                record_step(
                    ctx,
                    kind="branch_skipped",
                    what="skipped else branch",
                    because="condition was true",
                    line=stmt.line,
                    column=stmt.column,
                )
        else:
            record_step(
                ctx,
                kind="branch_taken",
                what="took else branch",
                because="condition was false",
                line=stmt.line,
                column=stmt.column,
            )
            if stmt.then_body:
                record_step(
                    ctx,
                    kind="branch_skipped",
                    what="skipped then branch",
                    because="condition was false",
                    line=stmt.line,
                    column=stmt.column,
                )
        branch = stmt.then_body if condition_value else stmt.else_body
        for child in branch:
            execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.Return):
        value = evaluate_expression(ctx, stmt.expression)
        record_step(
            ctx,
            kind="statement_return",
            what="returned a value",
            line=stmt.line,
            column=stmt.column,
        )
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
        count_int = int(count_decimal)
        record_step(
            ctx,
            kind="decision_repeat",
            what=f"repeat {count_int} times",
            data={"count": count_int},
            line=stmt.line,
            column=stmt.column,
        )
        if count_int == 0:
            record_step(
                ctx,
                kind="branch_skipped",
                what="skipped repeat body",
                because="count was 0",
                line=stmt.line,
                column=stmt.column,
            )
            return
        for _ in range(count_int):
            for child in stmt.body:
                execute_statement(ctx, child)
        record_step(
            ctx,
            kind="branch_taken",
            what=f"ran repeat body {count_int} times",
            because=f"count was {count_int}",
            line=stmt.line,
            column=stmt.column,
        )
        return
    if isinstance(stmt, ir.RepeatWhile):
        if stmt.limit <= 0:
            raise Namel3ssError("Loop limit must be greater than zero", line=stmt.line, column=stmt.column)
        record_step(
            ctx,
            kind="loop_start",
            what=f"loop start with limit {stmt.limit}",
            data={"limit": stmt.limit},
            line=stmt.line,
            column=stmt.column,
        )
        iterations = 0
        skipped = 0
        detail_limit = 5
        while iterations < stmt.limit:
            condition_value = evaluate_expression(ctx, stmt.condition)
            if not isinstance(condition_value, bool):
                raise Namel3ssError(
                    _condition_type_message(condition_value),
                    line=stmt.line,
                    column=stmt.column,
                )
            if not condition_value:
                break
            iterations += 1
            if iterations <= detail_limit:
                record_step(
                    ctx,
                    kind="loop_iteration",
                    what=f"loop iteration {iterations}",
                    data={"iteration": iterations},
                    line=stmt.line,
                    column=stmt.column,
                )
            else:
                skipped += 1
            for child in stmt.body:
                execute_statement(ctx, child)
        if iterations >= stmt.limit:
            record_step(
                ctx,
                kind="loop_limit_hit",
                what="loop limit hit",
                data={"limit": stmt.limit},
                line=stmt.limit_line or stmt.line,
                column=stmt.limit_column or stmt.column,
            )
            raise Namel3ssError("Loop limit hit", line=stmt.limit_line or stmt.line, column=stmt.limit_column or stmt.column)
        if skipped > 0:
            record_step(
                ctx,
                kind="loop_iteration",
                what=f"skipped {skipped} iterations",
                data={"skipped": skipped},
                line=stmt.line,
                column=stmt.column,
            )
        record_step(
            ctx,
            kind="loop_end",
            what=f"loop ended after {iterations} iterations",
            line=stmt.line,
            column=stmt.column,
        )
        return
    if isinstance(stmt, ir.ForEach):
        iterable_value = evaluate_expression(ctx, stmt.iterable)
        if not isinstance(iterable_value, list):
            raise Namel3ssError("For-each expects a list", line=stmt.line, column=stmt.column)
        count = len(iterable_value)
        record_step(
            ctx,
            kind="decision_for_each",
            what=f"for each {stmt.name} in list of {count} items",
            data={"count": count},
            line=stmt.line,
            column=stmt.column,
        )
        if count == 0:
            record_step(
                ctx,
                kind="branch_skipped",
                what="skipped for each body",
                because="list was empty",
                line=stmt.line,
                column=stmt.column,
            )
            return
        for item in iterable_value:
            ctx.locals[stmt.name] = item
            for child in stmt.body:
                execute_statement(ctx, child)
        record_step(
            ctx,
            kind="branch_taken",
            what=f"ran for each body {count} times",
            because=f"list length was {count}",
            line=stmt.line,
            column=stmt.column,
        )
        return
    if isinstance(stmt, ir.Match):
        subject = evaluate_expression(ctx, stmt.expression)
        subject_summary = summarize_value(subject)
        record_step(
            ctx,
            kind="decision_match",
            what=f"match {subject_summary}",
            data={"subject": subject_summary},
            line=stmt.line,
            column=stmt.column,
        )
        matched = False
        for idx, case in enumerate(stmt.cases):
            pattern_text = format_expression(case.pattern)
            pattern_value = evaluate_expression(ctx, case.pattern)
            if subject == pattern_value:
                matched = True
                record_step(
                    ctx,
                    kind="case_taken",
                    what=f"case {pattern_text} matched",
                    because="subject == pattern",
                    line=case.line,
                    column=case.column,
                )
                for child in case.body:
                    execute_statement(ctx, child)
                remaining = stmt.cases[idx + 1 :]
                for later in remaining:
                    later_text = format_expression(later.pattern)
                    record_step(
                        ctx,
                        kind="case_skipped",
                        what=f"case {later_text} skipped",
                        because="matched an earlier case",
                        line=later.line,
                        column=later.column,
                    )
                break
            record_step(
                ctx,
                kind="case_skipped",
                what=f"case {pattern_text} skipped",
                because="subject != pattern",
                line=case.line,
                column=case.column,
            )
        if matched:
            if stmt.otherwise is not None:
                record_step(
                    ctx,
                    kind="otherwise_skipped",
                    what="otherwise branch skipped",
                    because="matched an earlier case",
                    line=stmt.line,
                    column=stmt.column,
                )
            return
        if stmt.otherwise is not None:
            record_step(
                ctx,
                kind="otherwise_taken",
                what="otherwise branch taken",
                because="no cases matched",
                line=stmt.line,
                column=stmt.column,
            )
            for child in stmt.otherwise:
                execute_statement(ctx, child)
        return
    if isinstance(stmt, ir.TryCatch):
        record_step(
            ctx,
            kind="decision_try",
            what="try block",
            line=stmt.line,
            column=stmt.column,
        )
        try:
            for child in stmt.try_body:
                execute_statement(ctx, child)
        except Namel3ssError as err:
            record_step(
                ctx,
                kind="catch_taken",
                what="catch block taken",
                because="error raised",
                line=stmt.line,
                column=stmt.column,
            )
            ctx.locals[stmt.catch_var] = err
            for child in stmt.catch_body:
                execute_statement(ctx, child)
        else:
            record_step(
                ctx,
                kind="catch_skipped",
                what="catch block skipped",
                because="no error",
                line=stmt.line,
                column=stmt.column,
            )
        return
    if isinstance(stmt, ir.AskAIStmt):
        if getattr(ctx, "call_stack", []):
            raise Namel3ssError("Functions cannot call ai", line=stmt.line, column=stmt.column)
        execute_ask_ai(ctx, stmt)
        return
    if isinstance(stmt, ir.RunAgentStmt):
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
        return
    if isinstance(stmt, ir.RunAgentsParallelStmt):
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
        return
    if isinstance(stmt, ir.ParallelBlock):
        execute_parallel_block(ctx, stmt, execute_statement)
        return
    if isinstance(stmt, ir.Save):
        _run_record_write(ctx, stmt, handle_save, kind="statement_save", verb="saved")
        return
    if isinstance(stmt, ir.Create):
        _run_record_write(ctx, stmt, handle_create, kind="statement_create", verb="created")
        return
    if isinstance(stmt, ir.Find):
        if getattr(ctx, "call_stack", []):
            raise Namel3ssError("Functions cannot read records", line=stmt.line, column=stmt.column)
        handle_find(ctx, stmt)
        record_step(
            ctx,
            kind="statement_find",
            what=f"found {stmt.record_name}",
            line=stmt.line,
            column=stmt.column,
        )
        return
    if isinstance(stmt, ir.Update):
        _run_record_write(ctx, stmt, handle_update, kind="statement_update", verb="updated")
        return
    if isinstance(stmt, ir.Delete):
        _run_record_write(ctx, stmt, handle_delete, kind="statement_delete", verb="deleted")
        return
    if isinstance(stmt, ir.ThemeChange):
        if getattr(ctx, "parallel_mode", False):
            raise Namel3ssError("Parallel tasks cannot change theme", line=stmt.line, column=stmt.column)
        if getattr(ctx, "call_stack", []):
            raise Namel3ssError("Functions cannot change theme", line=stmt.line, column=stmt.column)
        if stmt.value not in {"light", "dark", "system"}:
            raise Namel3ssError("Theme must be one of: light, dark, system", line=stmt.line, column=stmt.column)
        ctx.runtime_theme = stmt.value
        ctx.traces.append({"type": "theme_change", "value": stmt.value})
        record_step(
            ctx,
            kind="statement_theme",
            what=f"set theme {stmt.value}",
            line=stmt.line,
            column=stmt.column,
        )
        ctx.last_value = stmt.value
        return
    raise Namel3ssError(f"Unsupported statement type: {type(stmt)}", line=stmt.line, column=stmt.column)


def _run_record_write(ctx: ExecutionContext, stmt: ir.Statement, handler, *, kind: str, verb: str) -> None:
    if getattr(ctx, "parallel_mode", False):
        raise Namel3ssError("Parallel tasks cannot write records", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot write records", line=stmt.line, column=stmt.column)
    handler(ctx, stmt)
    record_step(
        ctx,
        kind=kind,
        what=f"{verb} {stmt.record_name}",
        line=stmt.line,
        column=stmt.column,
    )


def _condition_type_message(value: object) -> str:
    kind = _value_kind(value)
    return build_guidance_message(
        what="If condition did not evaluate to true/false.",
        why=f"The condition evaluated to {kind}, but if/else requires a boolean.",
        fix="Use a comparison so the condition is boolean.",
        example="if total is greater than 10:\n  return true",
    )


def _bool_label(value: bool) -> str:
    return "true" if value else "false"


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
