from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from namel3ss.traces.redact import summarize_payload, summarize_text
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def _base_event(event_type: str, *, call_id: str, provider: str, model: str) -> dict:
    return {
        "type": event_type,
        "trace_version": TRACE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "call_id": call_id,
    }


def build_ai_call_started(
    *,
    call_id: str,
    provider: str,
    model: str,
    input_text: str | None,
    tools_declared_count: int,
    memory_enabled: bool,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_STARTED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "input_summary": summarize_text(input_text),
            "tools_declared_count": tools_declared_count,
            "memory_enabled": bool(memory_enabled),
        }
    )
    return event


def build_ai_call_completed(
    *,
    call_id: str,
    provider: str,
    model: str,
    output_text: str | None,
    duration_ms: int,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_COMPLETED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "output_summary": summarize_text(output_text),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
        }
    )
    return event


def build_ai_call_failed(
    *,
    call_id: str,
    provider: str,
    model: str,
    error_type: str,
    error_message: str,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.AI_CALL_FAILED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "error_type": error_type,
            "error_message": summarize_text(error_message),
            "duration_ms": duration_ms,
        }
    )
    return event


def build_ai_provider_error(
    *,
    call_id: str,
    provider: str,
    model: str,
    diagnostic: dict[str, object],
) -> dict:
    event = _base_event(TraceEventType.AI_PROVIDER_ERROR, call_id=call_id, provider=provider, model=model)
    event["diagnostic"] = diagnostic
    return event


def build_tool_call_requested(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    arguments: Any,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_REQUESTED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments_summary": summarize_payload(arguments),
        }
    )
    return event


def build_tool_call_proposed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    arguments: Any,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_PROPOSED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments_summary": summarize_payload(arguments),
        }
    )
    return event


def build_tool_call_allowed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    reason: str,
    capability: str | None,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_ALLOWED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "decision": "allowed",
            "reason": reason,
        }
    )
    if capability:
        event["capability"] = capability
    return event


def build_tool_call_blocked(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    reason: str,
    message: str,
    capability: str | None,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_BLOCKED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "decision": "blocked",
            "reason": reason,
            "message": summarize_text(message),
        }
    )
    if capability:
        event["capability"] = capability
    return event


def build_tool_call_started(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_STARTED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
        }
    )
    return event


def build_tool_call_finished(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    status: str,
    result: Any | None,
    error_message: str | None,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_FINISHED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "status": status,
            "duration_ms": duration_ms,
        }
    )
    if result is not None:
        event["result_summary"] = summarize_payload(result)
    if error_message:
        event["error_message"] = summarize_text(error_message)
    return event


def build_tool_loop_finished(
    *,
    call_id: str,
    provider: str,
    model: str,
    tool_call_count: int,
    stop_reason: str,
) -> dict:
    event = _base_event(TraceEventType.TOOL_LOOP_FINISHED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_count": int(tool_call_count),
            "stop_reason": stop_reason,
        }
    )
    return event


def build_tool_call_completed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    result: Any,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_COMPLETED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result_summary": summarize_payload(result),
            "duration_ms": duration_ms,
        }
    )
    return event


def build_tool_call_failed(
    *,
    call_id: str,
    tool_call_id: str,
    provider: str,
    model: str,
    tool_name: str,
    error_type: str,
    error_message: str,
    duration_ms: int,
) -> dict:
    event = _base_event(TraceEventType.TOOL_CALL_FAILED, call_id=call_id, provider=provider, model=model)
    event.update(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "error_type": error_type,
            "error_message": summarize_text(error_message),
            "duration_ms": duration_ms,
        }
    )
    return event
