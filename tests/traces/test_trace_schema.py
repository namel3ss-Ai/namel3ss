from namel3ss.traces.builders import (
    build_ai_call_completed,
    build_ai_call_failed,
    build_ai_call_started,
    build_memory_border_check,
    build_memory_conflict,
    build_memory_denied,
    build_memory_forget,
    build_memory_recall,
    build_memory_deleted,
    build_memory_promoted,
    build_memory_phase_diff,
    build_memory_phase_started,
    build_memory_promotion_denied,
    build_memory_write,
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


def test_memory_trace_schema_and_redaction():
    recall = build_memory_recall(
        ai_profile="assistant",
        session="sess-1",
        query="my password is 123",
        recalled=[
            {
                "id": "sess-1:short_term:1",
                "kind": "short_term",
                "text": "secret token",
                "source": "user",
                "created_at": 1,
                "importance": 0,
                "scope": "session",
                "meta": {},
            }
        ],
        policy={"short_term": 1, "semantic": False, "profile": False},
        deterministic_hash="hash-1",
        spaces_consulted=["session"],
        recall_counts={"session": 1},
    )
    assert recall["type"] == TraceEventType.MEMORY_RECALL
    assert recall["trace_version"] == TRACE_VERSION
    assert recall["query"] == "(redacted)"
    assert recall["recalled"][0]["text"] == "(redacted)"
    assert recall["deterministic_hash"] == "hash-1"
    assert recall["spaces_consulted"] == ["session"]
    assert recall["recall_counts"] == {"session": 1}

    write = build_memory_write(
        ai_profile="assistant",
        session="sess-1",
        written=[
            {
                "id": "sess-1:short_term:2",
                "kind": "short_term",
                "text": "token",
                "source": "ai",
                "created_at": 2,
                "importance": 0,
                "scope": "session",
                "meta": {},
            }
        ],
        reason="interaction_recorded",
    )
    assert write["type"] == TraceEventType.MEMORY_WRITE
    assert write["trace_version"] == TRACE_VERSION
    assert write["written"][0]["text"] == "(redacted)"
    assert write["reason"] == "interaction_recorded"


def test_memory_governance_trace_events():
    denied = build_memory_denied(
        ai_profile="assistant",
        session="sess-1",
        attempted={
            "id": "sess-1:semantic:1",
            "kind": "semantic",
            "text": "password=123",
            "source": "user",
            "created_at": 1,
            "importance": 0,
            "scope": "session",
            "meta": {},
        },
        reason="privacy_deny_sensitive",
        policy_snapshot={"write_policy": "normal"},
        explanation={"reason": "privacy_deny_sensitive"},
    )
    assert denied["type"] == TraceEventType.MEMORY_DENIED
    assert denied["attempted"]["text"] == "(redacted)"

    conflict = build_memory_conflict(
        ai_profile="assistant",
        session="sess-1",
        winner_id="sess-1:profile:2",
        loser_id="sess-1:profile:1",
        rule="authority",
        dedup_key="fact:name",
        explanation={"rule": "authority"},
    )
    assert conflict["type"] == TraceEventType.MEMORY_CONFLICT
    assert conflict["winner_id"] == "sess-1:profile:2"

    forgot = build_memory_forget(
        ai_profile="assistant",
        session="sess-1",
        memory_id="sess-1:semantic:3",
        reason="decay",
        policy_snapshot={"retention": {}},
        explanation={"reason": "decay"},
    )
    assert forgot["type"] == TraceEventType.MEMORY_FORGET
    assert forgot["memory_id"] == "sess-1:semantic:3"


def test_memory_space_trace_events():
    border = build_memory_border_check(
        ai_profile="assistant",
        session="sess-1",
        action="read",
        from_space="session",
        to_space=None,
        allowed=True,
        reason="allowed",
        policy_snapshot={"spaces": {"read_order": ["session"]}},
    )
    assert border["type"] == TraceEventType.MEMORY_BORDER_CHECK
    assert border["from_space"] == "session"

    promoted = build_memory_promoted(
        ai_profile="assistant",
        session="sess-1",
        from_space="session",
        to_space="user",
        from_id="sess-1:semantic:1",
        to_id="user-1:semantic:1",
        authority_used="user_asserted",
        reason="hint:remember_for_me",
        policy_snapshot={"spaces": {"read_order": ["session", "user"]}},
    )
    assert promoted["type"] == TraceEventType.MEMORY_PROMOTED
    assert promoted["to_space"] == "user"

    denied = build_memory_promotion_denied(
        ai_profile="assistant",
        session="sess-1",
        from_space="session",
        to_space="system",
        memory_id="sess-1:semantic:2",
        allowed=False,
        reason="promotion_disallowed",
        policy_snapshot={"spaces": {"read_order": ["session"]}},
    )
    assert denied["type"] == TraceEventType.MEMORY_PROMOTION_DENIED
    assert denied["allowed"] is False


def test_memory_phase_trace_events():
    started = build_memory_phase_started(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        owner="sess-1",
        phase_id="phase-1",
        phase_name="Phase 1",
        reason="auto",
        policy_snapshot={"phase": {"enabled": True}},
    )
    assert started["type"] == TraceEventType.MEMORY_PHASE_STARTED
    assert started["phase_id"] == "phase-1"
    assert started["phase_name"] == "Phase 1"

    deleted = build_memory_deleted(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        owner="sess-1",
        phase_id="phase-1",
        memory_id="sess-1:semantic:2",
        reason="superseded",
        policy_snapshot={"phase": {"enabled": True}},
        replaced_by="sess-1:semantic:3",
    )
    assert deleted["type"] == TraceEventType.MEMORY_DELETED
    assert deleted["replaced_by"] == "sess-1:semantic:3"

    diff = build_memory_phase_diff(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        owner="sess-1",
        from_phase_id="phase-1",
        to_phase_id="phase-2",
        added_count=1,
        deleted_count=2,
        replaced_count=1,
        top_changes=[{"change": "added", "memory_id": "sess-1:semantic:4", "kind": "semantic"}],
        summary_lines=["Added 1 items", "Deleted 2 items", "Replaced 1 items"],
    )
    assert diff["type"] == TraceEventType.MEMORY_PHASE_DIFF
    assert diff["from_phase_id"] == "phase-1"
