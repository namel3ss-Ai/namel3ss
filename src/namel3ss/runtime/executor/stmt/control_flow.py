from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.normalize import format_expression, summarize_value
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.executor.parallel.scheduler import execute_parallel_block
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def execute_if(ctx, stmt: ir.If, execute_statement) -> None:
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


def execute_repeat(ctx, stmt: ir.Repeat, execute_statement) -> None:
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


def execute_repeat_while(ctx, stmt: ir.RepeatWhile, execute_statement) -> None:
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


def execute_for_each(ctx, stmt: ir.ForEach, execute_statement) -> None:
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


def execute_match(ctx, stmt: ir.Match, execute_statement) -> None:
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


def execute_parallel(ctx, stmt: ir.ParallelBlock, execute_statement) -> None:
    execute_parallel_block(ctx, stmt, execute_statement)


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


__all__ = [
    "execute_for_each",
    "execute_if",
    "execute_match",
    "execute_parallel",
    "execute_repeat",
    "execute_repeat_while",
]
