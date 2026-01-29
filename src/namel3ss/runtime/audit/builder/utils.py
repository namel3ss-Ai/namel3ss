from __future__ import annotations

from typing import Iterable


def trace_events(traces: list[dict], event_type: str) -> list[dict]:
    return [trace for trace in traces if isinstance(trace, dict) and trace.get("type") == event_type]


def safe_state(state: dict | None) -> dict:
    return state if isinstance(state, dict) else {}


def safe_traces(traces: Iterable[dict] | None) -> list[dict]:
    items = list(traces or [])
    return [item for item in items if isinstance(item, dict)]


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


__all__ = ["safe_state", "safe_traces", "string_list", "trace_events"]
