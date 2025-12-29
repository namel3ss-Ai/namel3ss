from __future__ import annotations

from namel3ss.utils.numbers import is_number


def type_name_for_value(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "map"
    return type(value).__name__


def is_json_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, bool)):
        return True
    if is_number(value):
        return True
    if isinstance(value, list):
        return all(is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_json_value(val) for key, val in value.items())
    return False


__all__ = ["is_json_value", "type_name_for_value"]
