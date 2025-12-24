from __future__ import annotations

from statistics import mean as _mean, median as _median


def mean(payload: dict) -> dict:
    values = _read_values(payload)
    return {"value": _mean(values) if values else 0.0}


def median(payload: dict) -> dict:
    values = _read_values(payload)
    return {"value": _median(values) if values else 0.0}


def describe(payload: dict) -> dict:
    values = _read_values(payload)
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "mean": _mean(values),
        "median": _median(values),
        "min": min(values),
        "max": max(values),
    }


def _read_values(payload: dict) -> list[float]:
    values = payload.get("values", [])
    if not isinstance(values, list) or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        raise ValueError("payload.values must be a list of numbers")
    return [float(v) for v in values]


__all__ = ["describe", "mean", "median"]
