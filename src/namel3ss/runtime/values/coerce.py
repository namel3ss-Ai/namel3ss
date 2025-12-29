from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.values.types import is_json_value, type_name_for_value
from namel3ss.utils.numbers import is_number


def require_type(value: object, type_name: str, *, line: int | None = None, column: int | None = None) -> None:
    if _matches_type(value, type_name):
        return
    actual = type_name_for_value(value)
    raise Namel3ssError(
        f"Expected {type_name} but got {actual}",
        line=line,
        column=column,
    )


def _matches_type(value: object, type_name: str) -> bool:
    if type_name == "text":
        return isinstance(value, str)
    if type_name == "number":
        return is_number(value)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "map":
        return isinstance(value, dict)
    if type_name == "json":
        return is_json_value(value)
    return False


__all__ = ["require_type"]
