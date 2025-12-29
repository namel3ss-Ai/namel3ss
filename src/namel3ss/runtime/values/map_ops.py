from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.values.types import type_name_for_value


def map_get(value: object, key: object, *, line: int | None = None, column: int | None = None) -> object:
    if not isinstance(value, dict):
        raise Namel3ssError(
            f"Map get needs a map but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    if not isinstance(key, str):
        raise Namel3ssError(
            f"Map key must be text but got {type_name_for_value(key)}",
            line=line,
            column=column,
        )
    if key not in value:
        raise Namel3ssError(
            f"Map key '{key}' was not found",
            line=line,
            column=column,
        )
    return value[key]


def map_set(value: object, key: object, item: object, *, line: int | None = None, column: int | None = None) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError(
            f"Map set needs a map but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    if not isinstance(key, str):
        raise Namel3ssError(
            f"Map key must be text but got {type_name_for_value(key)}",
            line=line,
            column=column,
        )
    updated = dict(value)
    updated[key] = item
    return updated


def map_keys(value: object, *, line: int | None = None, column: int | None = None) -> list:
    if not isinstance(value, dict):
        raise Namel3ssError(
            f"Map keys needs a map but got {type_name_for_value(value)}",
            line=line,
            column=column,
        )
    keys = list(value.keys())
    for key in keys:
        if not isinstance(key, str):
            raise Namel3ssError(
                f"Map key must be text but got {type_name_for_value(key)}",
                line=line,
                column=column,
            )
    return sorted(keys)


__all__ = ["map_get", "map_keys", "map_set"]
