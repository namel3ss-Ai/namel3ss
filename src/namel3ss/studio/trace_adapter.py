from __future__ import annotations

from typing import Any


def normalize_action_response(payload: dict) -> dict:
    traces = payload.get("traces")
    if not isinstance(traces, list):
        return payload
    payload["traces"] = [_normalize_trace_item(item) for item in traces]
    return payload


def _normalize_trace_item(item: Any) -> dict:
    if isinstance(item, dict):
        trace = dict(item)
    else:
        trace = {"raw": item}

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


__all__ = ["normalize_action_response"]
