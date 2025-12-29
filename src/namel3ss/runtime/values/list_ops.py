from __future__ import annotations

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


__all__ = ["list_append", "list_get", "list_length"]
