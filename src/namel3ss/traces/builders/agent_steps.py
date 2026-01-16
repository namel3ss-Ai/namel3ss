from __future__ import annotations

from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def build_agent_step_start(
    *,
    agent_name: str,
    agent_id: str | None,
    role: str | None,
    step_id: str,
    reason: str,
) -> dict:
    event = {
        "type": TraceEventType.AGENT_STEP_START,
        "trace_version": TRACE_VERSION,
        "agent_name": agent_name,
        "step_id": step_id,
        "title": "Agent step started",
        "lines": [reason],
    }
    if agent_id:
        event["agent_id"] = agent_id
    if role:
        event["role"] = role
    return event


def build_agent_step_end(
    *,
    agent_name: str,
    agent_id: str | None,
    role: str | None,
    step_id: str,
    reason: str,
    status: str,
    memory_facts: dict | None = None,
    error_message: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.AGENT_STEP_END,
        "trace_version": TRACE_VERSION,
        "agent_name": agent_name,
        "step_id": step_id,
        "status": status,
        "title": "Agent step completed" if status == "ok" else "Agent step failed",
        "lines": [reason],
    }
    if agent_id:
        event["agent_id"] = agent_id
    if role:
        event["role"] = role
    if memory_facts is not None:
        event["memory_facts"] = dict(memory_facts)
    if error_message:
        event["error_message"] = error_message
    return event


__all__ = ["build_agent_step_start", "build_agent_step_end"]
