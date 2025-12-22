from __future__ import annotations

TRACE_VERSION = "2024-10-01"


class TraceEventType:
    AI_CALL_STARTED = "ai_call_started"
    AI_CALL_COMPLETED = "ai_call_completed"
    AI_CALL_FAILED = "ai_call_failed"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"


__all__ = ["TRACE_VERSION", "TraceEventType"]
