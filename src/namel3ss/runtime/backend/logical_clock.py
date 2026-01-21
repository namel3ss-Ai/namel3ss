from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def current_logical_time(ctx) -> int:
    value = getattr(ctx, "logical_time", 0)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return 0


def advance_logical_time(ctx, amount: object, *, line: int | None, column: int | None) -> tuple[int, int]:
    delta = require_non_negative_int(amount, line=line, column=column)
    now = current_logical_time(ctx)
    new_time = now + delta
    ctx.logical_time = new_time
    return now, new_time


def require_non_negative_int(value: object, *, line: int | None, column: int | None) -> int:
    if not is_number(value):
        raise Namel3ssError(
            build_guidance_message(
                what="Logical time must be a number.",
                why="Scheduling uses a deterministic logical clock.",
                fix="Use a whole number duration.",
                example="tick 5",
            ),
            line=line,
            column=column,
        )
    decimal = to_decimal(value)
    if not decimal_is_int(decimal):
        raise Namel3ssError(
            build_guidance_message(
                what="Logical time must be a whole number.",
                why="Fractional time is not supported.",
                fix="Round to a whole number.",
                example="tick 1",
            ),
            line=line,
            column=column,
        )
    delta = int(decimal)
    if delta < 0:
        raise Namel3ssError(
            build_guidance_message(
                what="Logical time cannot move backward.",
                why="Scheduling requires non-negative time advances.",
                fix="Use zero or a positive value.",
                example="tick 3",
            ),
            line=line,
            column=column,
        )
    return delta


__all__ = ["advance_logical_time", "current_logical_time", "require_non_negative_int"]
