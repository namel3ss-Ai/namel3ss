from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.execution.normalize import format_assignable
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.executor.assign import assign
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.purity import require_effect_allowed
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def execute_order_list(ctx: ExecutionContext, stmt: ir.OrderList) -> None:
    _require_mutation_allowed(ctx, stmt.target, stmt)
    items = evaluate_expression(ctx, stmt.target)
    ordered = _order_by_field(items, stmt.field, stmt.direction, line=stmt.line, column=stmt.column)
    assign(ctx, stmt.target, ordered, stmt)
    ctx.last_value = ordered
    ctx.last_order_target = stmt.target
    record_step(
        ctx,
        kind="statement_order",
        what=f"order {format_assignable(stmt.target)} by {stmt.field}",
        line=stmt.line,
        column=stmt.column,
    )


def execute_keep_first(ctx: ExecutionContext, stmt: ir.KeepFirst) -> None:
    target = ctx.last_order_target
    if target is None:
        raise Namel3ssError(
            build_guidance_message(
                what="keep first needs an order statement first.",
                why="There is no ordered list to trim yet.",
                fix="Order a list before keep first.",
                example="order state.items by score from highest to lowest\nkeep first 5 items",
            ),
            line=stmt.line,
            column=stmt.column,
        )
    _require_mutation_allowed(ctx, target, stmt)
    count_value = evaluate_expression(ctx, stmt.count)
    count = _require_count(count_value, line=stmt.line, column=stmt.column)
    items = evaluate_expression(ctx, target)
    if not isinstance(items, list):
        raise Namel3ssError(
            f"keep first needs a list but got {type_name_for_value(items)}",
            line=stmt.line,
            column=stmt.column,
        )
    trimmed = list(items[:count])
    assign(ctx, target, trimmed, stmt)
    ctx.last_value = trimmed
    record_step(
        ctx,
        kind="statement_keep_first",
        what=f"keep first {count} items",
        line=stmt.line,
        column=stmt.column,
    )


def _require_mutation_allowed(ctx: ExecutionContext, target: ir.Assignable, stmt: ir.Statement) -> None:
    if getattr(ctx, "parallel_mode", False) and isinstance(target, ir.StatePath):
        raise Namel3ssError("Parallel tasks cannot change state", line=stmt.line, column=stmt.column)
    if getattr(ctx, "call_stack", []) and isinstance(target, ir.StatePath):
        raise Namel3ssError("Functions cannot change state", line=stmt.line, column=stmt.column)
    if isinstance(target, ir.StatePath):
        require_effect_allowed(ctx, effect="write state", line=stmt.line, column=stmt.column)


def _order_by_field(items: object, field: str, direction: str, *, line: int | None, column: int | None) -> list:
    if not isinstance(items, list):
        raise Namel3ssError(
            f"Order needs a list but got {type_name_for_value(items)}",
            line=line,
            column=column,
        )
    if not items:
        return []
    indexed: list[tuple[Decimal, int, object]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise Namel3ssError(
                f"Order list items must be objects but got {type_name_for_value(item)}",
                line=line,
                column=column,
            )
        if field not in item:
            raise Namel3ssError(
                f"Order field '{field}' is missing",
                line=line,
                column=column,
            )
        value = item[field]
        if not is_number(value):
            raise Namel3ssError(
                f"Order field '{field}' must be a number but got {type_name_for_value(value)}",
                line=line,
                column=column,
            )
        score = to_decimal(value)
        if isinstance(score, Decimal) and score.is_nan():
            raise Namel3ssError(
                f"Order field '{field}' must be a real number",
                line=line,
                column=column,
            )
        if direction == "desc":
            score = -score
        indexed.append((score, idx, item))
    indexed.sort(key=lambda entry: (entry[0], entry[1]))
    return [item for _, _, item in indexed]


def _require_count(value: object, *, line: int | None, column: int | None) -> int:
    if not is_number(value):
        raise Namel3ssError(
            f"keep first needs a number but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    count = to_decimal(value)
    if isinstance(count, Decimal) and count.is_nan():
        raise Namel3ssError("keep first needs a real number", line=line, column=column)
    if not decimal_is_int(count):
        raise Namel3ssError("keep first needs a whole number", line=line, column=column)
    count_int = int(count)
    if count_int < 0:
        raise Namel3ssError("keep first needs zero or more", line=line, column=column)
    return count_int


__all__ = ["execute_keep_first", "execute_order_list"]
