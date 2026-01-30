from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum
import os
from pathlib import Path
from typing import Any

_PROFILE_ENV = "N3_PROFILE"
_ENABLED_VALUES = {"1", "true", "yes", "on"}


@dataclass(slots=True)
class _Bucket:
    name: str
    units: int = 0
    items: int = 0


_STATE: dict[str, _Bucket] = {}


def enabled() -> bool:
    value = os.getenv(_PROFILE_ENV, "")
    return value.strip().lower() in _ENABLED_VALUES


def reset() -> None:
    _STATE.clear()


def record_scan(*, tokens: int, lines: int) -> None:
    if not enabled():
        return
    _record("scan", units=_safe_int(tokens), items=_safe_int(lines))


def record_parse(program: object) -> None:
    if not enabled():
        return
    _record("parse", units=_count_units(program))


def record_lower(program: object) -> None:
    if not enabled():
        return
    _record("lower", units=_count_units(program))


def record_explain(payload: object) -> None:
    if not enabled():
        return
    _record("explain", units=_count_units(payload))


def snapshot() -> dict:
    if not enabled():
        return {}
    buckets: list[dict] = []
    total = 0
    for name in sorted(_STATE.keys()):
        bucket = _STATE[name]
        entry = {"name": name, "units": bucket.units}
        if bucket.items:
            entry["items"] = bucket.items
        buckets.append(entry)
        total += bucket.units
    return {"units": total, "buckets": buckets}


def attach_profile(payload: dict) -> dict:
    if not enabled():
        return payload
    record_explain(payload)
    profile = snapshot()
    if not profile:
        return payload
    merged = dict(payload)
    merged["profiling"] = profile
    return merged


def _record(name: str, *, units: int, items: int = 0) -> None:
    bucket = _STATE.get(name)
    if bucket is None:
        bucket = _Bucket(name=name)
        _STATE[name] = bucket
    bucket.units += max(0, units)
    if items:
        bucket.items += max(0, items)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count_units(value: Any) -> int:
    seen: set[int] = set()
    return _count_value(value, seen)


def _count_value(value: Any, seen: set[int]) -> int:
    if value is None or isinstance(value, (str, int, float, bool, Decimal, Path, Enum, bytes)):
        return 1
    value_id = id(value)
    if value_id in seen:
        return 0
    if is_dataclass(value):
        seen.add(value_id)
        total = 1
        for field in fields(value):
            total += _count_value(getattr(value, field.name), seen)
        return total
    if isinstance(value, dict):
        seen.add(value_id)
        total = 1
        for key, val in value.items():
            total += _count_value(key, seen)
            total += _count_value(val, seen)
        return total
    if isinstance(value, (list, tuple, set)):
        seen.add(value_id)
        total = 1
        for item in value:
            total += _count_value(item, seen)
        return total
    return 1


__all__ = [
    "attach_profile",
    "enabled",
    "record_explain",
    "record_lower",
    "record_parse",
    "record_scan",
    "reset",
    "snapshot",
]
