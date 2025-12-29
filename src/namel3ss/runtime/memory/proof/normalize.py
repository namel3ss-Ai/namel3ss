from __future__ import annotations

from typing import Any


_ND_KEYS = {
    "timestamp": "<time>",
    "time": "<time>",
    "uuid": "<id>",
}


def normalize_recall_steps(steps: list[dict]) -> list[dict]:
    return [normalize_value(step, path=("recall_steps", idx)) for idx, step in enumerate(steps)]


def normalize_write_steps(steps: list[dict]) -> list[dict]:
    return [normalize_value(step, path=("write_steps", idx)) for idx, step in enumerate(steps)]


def normalize_meta(meta: dict) -> dict:
    return normalize_value(meta, path=("meta",))


def normalize_value(value: Any, *, path: tuple = ()) -> Any:
    if isinstance(value, dict):
        normalized: dict = {}
        for key in sorted(value.keys(), key=str):
            child = value[key]
            if key in _ND_KEYS:
                normalized[key] = _ND_KEYS[key]
            else:
                normalized[key] = normalize_value(child, path=path + (key,))
        return normalized
    if isinstance(value, list):
        return [normalize_value(entry, path=path + (idx,)) for idx, entry in enumerate(value)]
    return value


__all__ = ["normalize_meta", "normalize_recall_steps", "normalize_value", "normalize_write_steps"]
