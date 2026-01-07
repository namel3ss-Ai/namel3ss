from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.utils.numbers import decimal_is_int, is_number, to_decimal


def list_length(value: object, *, line: int | None = None, column: int | None = None) -> int:
    if not isinstance(value, list):
        raise Namel3ssError(
            f"List length needs a list but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    return len(value)


def list_append(value: object, item: object, *, line: int | None = None, column: int | None = None) -> list:
    if not isinstance(value, list):
        raise Namel3ssError(
            f"List append needs a list but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    return list(value) + [item]


def list_get(value: object, index: object, *, line: int | None = None, column: int | None = None) -> object:
    if not isinstance(value, list):
        raise Namel3ssError(
            f"List get needs a list but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    if not is_number(index):
        raise Namel3ssError(
            f"List index must be a number but got {type_name_for_value(index)}",
            line=line,
            column=column,
        )
    index_decimal = to_decimal(index)
    if not decimal_is_int(index_decimal):
        raise Namel3ssError(
            "List index must be an integer",
            line=line,
            column=column,
        )
    idx = int(index_decimal)
    if idx < 0 or idx >= len(value):
        raise Namel3ssError(
            "List index is out of range",
            line=line,
            column=column,
        )
    return value[idx]

def list_sum(value: object, *, line: int | None = None, column: int | None = None) -> Decimal:
    numbers = _require_numeric_list(value, op_name="sum", line=line, column=column)
    return sum(numbers, Decimal("0"))


def list_min(value: object, *, line: int | None = None, column: int | None = None) -> Decimal:
    numbers = _require_numeric_list(value, op_name="min", line=line, column=column)
    return min(numbers)


def list_max(value: object, *, line: int | None = None, column: int | None = None) -> Decimal:
    numbers = _require_numeric_list(value, op_name="max", line=line, column=column)
    return max(numbers)


def list_mean(value: object, *, line: int | None = None, column: int | None = None) -> Decimal:
    numbers = _require_numeric_list(value, op_name="mean", line=line, column=column)
    total = sum(numbers, Decimal("0"))
    return total / Decimal(len(numbers))


def list_median(value: object, *, line: int | None = None, column: int | None = None) -> Decimal:
    numbers = _require_numeric_list(value, op_name="median", line=line, column=column)
    ordered = sorted(numbers)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


def _require_numeric_list(
    value: object,
    *,
    op_name: str,
    line: int | None,
    column: int | None,
) -> list[Decimal]:
    if not isinstance(value, list):
        raise Namel3ssError(
            f"{op_name} requires a list but got {type_name_for_value(value)}",
            line=line,
            column=column,
            details={"error_id": "math.not_list", "operation": op_name},
        )
    if not value:
        raise Namel3ssError(
            f"{op_name} cannot operate on an empty list",
            line=line,
            column=column,
            details={"error_id": "math.empty_list", "operation": op_name},
        )
    numbers: list[Decimal] = []
    for idx, item in enumerate(value):
        if not is_number(item):
            raise Namel3ssError(
                f"{op_name} list item at index {idx} must be a number but got {type_name_for_value(item)}",
                line=line,
                column=column,
                details={"error_id": "math.non_numeric_element", "operation": op_name, "index": idx},
            )
        numbers.append(to_decimal(item))
    return numbers


__all__ = [
    "list_append",
    "list_get",
    "list_length",
    "list_max",
    "list_mean",
    "list_median",
    "list_min",
    "list_sum",
]
