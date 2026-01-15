from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from typing import Any


SORTED_LIST_FIELDS = {"capabilities", "exposed_tools"}


def dump_ast(node: Any) -> Any:
    return _to_data(node)


def _to_data(value: Any, *, field_name: str | None = None) -> Any:
    if is_dataclass(value):
        data = {"type": value.__class__.__name__}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name == "functions" and not field_value:
                continue
            if field.name == "merge" and field_value is None:
                continue
            if field.name == "state_defaults" and field_value is None:
                continue
            if field.name == "steps" and not field_value:
                continue
            if field.name == "declarative" and not field_value:
                continue
            data[field.name] = _to_data(field_value, field_name=field.name)
        return data
    if isinstance(value, dict):
        return {key: _to_data(value[key], field_name=key) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        items = [_to_data(item) for item in value]
        return _sort_list(items, field_name)
    if isinstance(value, tuple):
        items = [_to_data(item) for item in value]
        return _sort_list(items, field_name)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _sort_list(items: list, field_name: str | None) -> list:
    if field_name in SORTED_LIST_FIELDS:
        return sorted(items, key=_list_sort_key)
    return items


def _list_sort_key(item: Any) -> str:
    if isinstance(item, dict):
        if "name" in item:
            return str(item.get("name"))
        if "type" in item:
            return str(item.get("type"))
        return json.dumps(item, sort_keys=True)
    return str(item)


__all__ = ["dump_ast"]
