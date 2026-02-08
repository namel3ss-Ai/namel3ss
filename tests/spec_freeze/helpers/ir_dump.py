from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from typing import Any


SORTED_LIST_FIELDS = {"capabilities", "exposed_tools"}


def dump_ir(node: Any) -> Any:
    return _to_data(node)


def _to_data(value: Any, *, field_name: str | None = None) -> Any:
    if is_dataclass(value):
        data = {"type": value.__class__.__name__}
        for field in fields(value):
            field_value = getattr(value, field.name)
            if field.name == "purity" and field_value == "effectful":
                continue
            if field.name == "flow_contracts" and not field_value:
                continue
            if field.name == "functions" and not field_value:
                continue
            if field.name == "merge" and field_value is None:
                continue
            if field.name == "stream" and field_value is False:
                continue
            if field.name == "state_defaults" and field_value is None:
                continue
            if field.name == "status" and field_value is None:
                continue
            if field.name == "layout" and field_value is None:
                continue
            if field.name == "ui_active_page_rules" and field_value is None:
                continue
            if field.name == "policy" and field_value is None:
                continue
            if field.name == "steps" and not field_value:
                continue
            if field.name == "declarative" and not field_value:
                continue
            if field.name == "ai_metadata" and field_value is None:
                continue
            if field.name == "ai_flows" and not field_value:
                continue
            if field.name == "prompts" and not field_value:
                continue
            if field.name == "crud" and not field_value:
                continue
            if field.name == "routes" and not field_value:
                continue
            if field.name == "ui_plugins" and not field_value:
                continue
            if field.name == "generated" and not field_value:
                continue
            if field.name == "visibility_rule" and field_value is None:
                continue
            if field.name == "visibility" and field_value is None and value.__class__.__name__ == "Page":
                continue
            if field.name == "availability_rule" and field_value is None:
                continue
            if field.name == "empty_state_hidden" and field_value is False:
                continue
            if field.name == "debug_only" and field_value is None:
                continue
            if field.name in {"prompt_expr", "source_language", "target_language", "tests"} and field_value is None:
                continue
            if field.name in {"output_fields", "chain_steps"} and not field_value:
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


__all__ = ["dump_ir"]
