from namel3ss.traces.builders import (
    build_ai_call_completed,
    build_ai_call_failed,
    build_ai_call_started,
    build_tool_call_completed,
    build_tool_call_failed,
    build_tool_call_requested,
)
from namel3ss.traces.redact import SUMMARY_MAX_LENGTH
from namel3ss.traces.schema import TRACE_VERSION, TraceEventType


def test_ai_call_event_keys_and_version():
    event = build_ai_call_started(
        call_id="call-123",
        provider="mock",
        model="gpt-4.1",
        input_text="hello world",
        tools_declared_count=1,
        memory_enabled=True,
    )
    assert event["type"] == TraceEventType.AI_CALL_STARTED
    assert event["trace_version"] == TRACE_VERSION
    assert "timestamp" in event
    assert event["call_id"] == "call-123"
    assert event["provider"] == "mock"
    assert event["model"] == "gpt-4.1"
    assert event["memory_enabled"] is True

    failed = build_ai_call_failed(
        call_id="call-123",
        provider="mock",
        model="gpt-4.1",
        error_type="TestError",
        error_message="something went wrong",
        duration_ms=42,
    )
    assert failed["type"] == TraceEventType.AI_CALL_FAILED
    assert failed["duration_ms"] == 42


def test_redaction_and_truncation():
    long_text = "x" * (SUMMARY_MAX_LENGTH + 50)
    completed = build_ai_call_completed(
        call_id="call-999",
        provider="mock",
        model="demo",
        output_text=long_text,
        duration_ms=10,
    )
    assert len(completed["output_summary"]) <= SUMMARY_MAX_LENGTH + len("... (truncated)")

    requested = build_tool_call_requested(
        call_id="call-999",
        tool_call_id="tool-1",
        provider="mock",
        model="demo",
        tool_name="echo",
        arguments={"api_key": "secret-value"},
    )
    assert requested["type"] == TraceEventType.TOOL_CALL_REQUESTED
    assert requested["arguments_summary"] == "(redacted)"

    failed = build_tool_call_failed(
        call_id="call-999",
        tool_call_id="tool-1",
        provider="mock",
        model="demo",
        tool_name="echo",
        error_type="Boom",
        error_message="super long " + ("z" * (SUMMARY_MAX_LENGTH + 10)),
        duration_ms=5,
    )
    assert len(failed["error_message"]) <= SUMMARY_MAX_LENGTH + len("... (truncated)")
