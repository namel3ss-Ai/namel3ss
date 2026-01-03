from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from namel3ss.utils.numbers import decimal_is_int, decimal_to_str


TRACE_VOLATILE_KEYS = {
    "call_id",
    "duration_ms",
    "project_id",
    "time",
    "time_end",
    "time_start",
    "timestamp",
    "tool_call_id",
    "tool_use_id",
    "trace_id",
}
_DROP_RUN_KEYS = {"ui"}


def normalize_traces(traces: Iterable[Any] | None) -> list[dict]:
    items = list(traces or [])
    return [_normalize_trace_item(item) for item in items]


def canonical_trace_json(traces: Iterable[Any] | None) -> str:
    canonical = _canonicalize_traces(traces)
    return _dump_json(canonical, pretty=True)


def trace_hash(traces: Iterable[Any] | None) -> str:
    canonical = _canonicalize_traces(traces)
    payload = _dump_json(canonical, pretty=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_trace_hash(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return payload
    traces = payload.get("traces")
    hash_value = trace_hash(traces if isinstance(traces, list) else [])
    contract = payload.get("contract")
    if isinstance(contract, dict):
        contract["trace_hash"] = hash_value
    return payload


def canonicalize_run_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    return _canonicalize_payload_value(payload, path=())


def canonical_run_json(payload: dict, *, pretty: bool = True) -> str:
    canonical = canonicalize_run_payload(payload)
    return _dump_json(canonical, pretty=pretty)


def run_payload_hash(payload: dict) -> str:
    canonical = canonicalize_run_payload(payload)
    payload_json = _dump_json(canonical, pretty=False)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _canonicalize_traces(traces: Iterable[Any] | None) -> list[dict]:
    normalized = normalize_traces(traces)
    scrubbed = _scrub_trace_value(normalized)
    return _canonicalize_value(scrubbed)


def _normalize_trace_item(item: Any) -> dict:
    trace = _coerce_trace(item)
    canonical_events = trace.get("canonical_events")
    if not isinstance(canonical_events, list):
        canonical_events = []
    trace["canonical_events"] = canonical_events

    memory_events = trace.get("memory_events")
    if not isinstance(memory_events, list):
        memory_events = _extract_memory_events(canonical_events)
    trace["memory_events"] = memory_events

    trace_type = trace.get("type")
    if not isinstance(trace_type, str) or not trace_type:
        trace_type = _infer_type(trace)
        trace["type"] = trace_type

    title = trace.get("title")
    if not isinstance(title, str) or not title:
        trace["title"] = _infer_title(trace_type, trace)

    return trace


def _coerce_trace(item: Any) -> dict:
    if isinstance(item, dict):
        return dict(item)
    data = getattr(item, "__dict__", None)
    if isinstance(data, dict):
        return dict(data)
    return {"raw": item}


def _extract_memory_events(events: list[dict]) -> list[dict]:
    memory_events: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if isinstance(event_type, str) and "memory" in event_type:
            memory_events.append(event)
    return memory_events


def _infer_type(trace: dict) -> str:
    if trace.get("ai_name") or trace.get("ai_profile_name") or trace.get("agent_name"):
        return "ai_call"
    if trace.get("record") and trace.get("fields") is not None:
        return "submit_form"
    if trace.get("tool_name") or trace.get("tool"):
        return "tool_call"
    if trace.get("error_id") or trace.get("boundary"):
        return "runtime_error"
    return "trace"


def _infer_title(trace_type: str, trace: dict) -> str:
    if trace_type == "ai_call":
        agent = trace.get("agent_name")
        if agent:
            return f"Agent {agent}"
        name = trace.get("ai_name") or trace.get("ai_profile_name")
        return f"AI {name}" if name else "AI call"
    if trace_type == "submit_form":
        record = trace.get("record")
        return f"Form submit: {record}" if record else "Form submit"
    if trace_type == "tool_call":
        tool = trace.get("tool_name") or trace.get("tool")
        return f"Tool call: {tool}" if tool else "Tool call"
    if trace_type.startswith("memory_") or trace_type == "memory":
        return "Memory"
    return trace_type.replace("_", " ").title()


def _scrub_trace_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _scrub_trace_value(val)
            for key, val in value.items()
            if key not in TRACE_VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_scrub_trace_value(item) for item in value]
    return value


def _canonicalize_payload_value(value: Any, *, path: tuple) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_str = str(key)
            if not path and key_str in _DROP_RUN_KEYS:
                continue
            child = value[key]
            if key_str == "traces" and isinstance(child, list):
                normalized[key_str] = _canonicalize_traces(child)
            elif key_str == "events" and path == ("contract", "memory") and isinstance(child, list):
                scrubbed = _scrub_trace_value(child)
                normalized[key_str] = _canonicalize_value(scrubbed)
            else:
                normalized[key_str] = _canonicalize_payload_value(child, path=path + (key_str,))
        return normalized
    if isinstance(value, list):
        return [_canonicalize_payload_value(item, path=path + (idx,)) for idx, item in enumerate(value)]
    if isinstance(value, tuple):
        return [_canonicalize_payload_value(item, path=path + (idx,)) for idx, item in enumerate(value)]
    if isinstance(value, set):
        return [_canonicalize_payload_value(item, path=path + ("set",)) for item in sorted(value, key=str)]
    return _canonicalize_scalar(value)


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            normalized[str(key)] = _canonicalize_value(value[key])
        return normalized
    if isinstance(value, list):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_value(item) for item in value]
    if isinstance(value, set):
        return [_canonicalize_value(item) for item in sorted(value, key=str)]
    return _canonicalize_scalar(value)


def _canonicalize_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        if decimal_is_int(value):
            return int(value)
        return decimal_to_str(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return _canonicalize_scalar(value.value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _dump_json(value: object, *, pretty: bool) -> str:
    if pretty:
        return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


__all__ = [
    "TRACE_VOLATILE_KEYS",
    "apply_trace_hash",
    "canonical_run_json",
    "canonical_trace_json",
    "canonicalize_run_payload",
    "normalize_traces",
    "run_payload_hash",
    "trace_hash",
]
