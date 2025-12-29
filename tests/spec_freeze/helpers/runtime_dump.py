from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from namel3ss.spec_freeze.v1.rules import NONDETERMINISTIC_KEYS, NORMALIZED_VALUE, PATH_KEYS


def dump_runtime(result: Any) -> dict:
    return {
        "state": _to_data(getattr(result, "state", None)),
        "last_value": _to_data(getattr(result, "last_value", None)),
        "execution_steps": _to_data(getattr(result, "execution_steps", None)),
        "traces": _to_data(getattr(result, "traces", None)),
        "runtime_theme": _to_data(getattr(result, "runtime_theme", None)),
        "theme_source": _to_data(getattr(result, "theme_source", None)),
    }


def _to_data(value: Any, *, key_name: str | None = None) -> Any:
    if key_name in NONDETERMINISTIC_KEYS:
        return NORMALIZED_VALUE
    if key_name in PATH_KEYS:
        return _normalize_path(value)
    if is_dataclass(value):
        data = {"type": value.__class__.__name__}
        for field in fields(value):
            data[field.name] = _to_data(getattr(value, field.name), key_name=field.name)
        return data
    if isinstance(value, dict):
        return {key: _to_data(value[key], key_name=key) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_to_data(item) for item in value]
    if isinstance(value, tuple):
        return [_to_data(item) for item in value]
    if isinstance(value, set):
        return sorted([_to_data(item) for item in value], key=str)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return _normalize_path(value)
    return value


def _normalize_path(value: Any) -> Any:
    if isinstance(value, Path):
        return NORMALIZED_VALUE if value.is_absolute() else str(value)
    if isinstance(value, str):
        return NORMALIZED_VALUE if Path(value).is_absolute() else value
    return value


__all__ = ["dump_runtime"]
