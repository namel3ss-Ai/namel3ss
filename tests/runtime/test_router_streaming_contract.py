from __future__ import annotations

from namel3ss.runtime.router.streaming import build_sse_body, should_stream_response, sorted_yield_messages


def test_sorted_yield_messages_orders_chat_and_ai_events_by_contract() -> None:
    rows = sorted_yield_messages(
        [
            {"event_type": "finish", "flow_name": "demo", "output": "done", "sequence": 2, "stream_channel": "ai"},
            {"event_type": "token", "flow_name": "demo", "output": "d", "sequence": 2, "stream_channel": "ai"},
            {"event_type": "progress", "flow_name": "demo", "output": None, "sequence": 2, "stream_channel": "ai"},
            {"event_type": "chat.thread.save", "flow_name": "chat.threads", "output": {"thread_id": "thread.main"}, "sequence": 1, "stream_channel": "chat"},
            {"event_type": "chat.thread.load", "flow_name": "chat.threads", "output": {"thread_id": "thread.main"}, "sequence": 1, "stream_channel": "chat"},
            {"event_type": "chat.thread.list", "flow_name": "chat.threads", "output": {"thread_count": 1}, "sequence": 1, "stream_channel": "chat"},
        ]
    )
    assert [row["event_type"] for row in rows] == [
        "chat.thread.list",
        "chat.thread.load",
        "chat.thread.save",
        "progress",
        "token",
        "finish",
    ]


def test_sorted_yield_messages_uses_deterministic_tie_breakers() -> None:
    rows = sorted_yield_messages(
        [
            {
                "event_type": "chat.thread.list",
                "flow_name": "chat.z",
                "output": {"thread_count": 2},
                "sequence": 1,
                "stream_channel": "chat",
                "stream_id": "chat.threads.b",
            },
            {
                "event_type": "chat.thread.list",
                "flow_name": "chat.a",
                "output": {"thread_count": 1},
                "sequence": 1,
                "stream_channel": "chat",
                "stream_id": "chat.threads.a",
            },
            {
                "event_type": "chat.thread.list",
                "flow_name": "chat.a",
                "output": {"thread_count": 0},
                "sequence": 1,
                "stream_channel": "chat",
                "stream_id": "chat.threads.a",
            },
        ]
    )
    assert [(row["flow_name"], row["stream_id"], row["output"]["thread_count"]) for row in rows] == [
        ("chat.a", "chat.threads.a", 0),
        ("chat.a", "chat.threads.a", 1),
        ("chat.z", "chat.threads.b", 2),
    ]


def test_sorted_yield_messages_normalizes_invalid_event_types_by_channel() -> None:
    rows = sorted_yield_messages(
        [
            {
                "event_type": "invalid.event",
                "flow_name": "chat.threads",
                "output": {"thread_id": "thread.main"},
                "sequence": 1,
                "stream_channel": "chat",
            },
            {
                "event_type": "invalid.event",
                "flow_name": "assistant.chat",
                "output": "a",
                "sequence": 2,
                "stream_channel": "ai",
            },
            {
                "event_type": "chat.thread.save",
                "flow_name": "chat.threads",
                "output": {"thread_id": "thread.docs"},
                "sequence": 3,
                "stream_channel": "unknown",
            },
        ]
    )
    assert [(row["stream_channel"], row["event_type"]) for row in rows[:2]] == [
        ("chat", "yield"),
        ("ai", "yield"),
    ]
    assert "stream_channel" not in rows[2]
    assert rows[2]["event_type"] == "chat.thread.save"


def test_should_stream_response_requires_explicit_signal_for_chat_events() -> None:
    chat_events = [
        {
            "event_type": "chat.thread.list",
            "flow_name": "chat.threads",
            "output": {"thread_count": 0},
            "sequence": 1,
            "stream_channel": "chat",
        }
    ]
    assert should_stream_response({}, {}, chat_events) is False
    assert should_stream_response({"stream": "true"}, {}, chat_events) is True


def test_build_sse_body_emits_chat_event_types_and_return_event() -> None:
    events = sorted_yield_messages(
        [
            {
                "event_type": "chat.thread.load",
                "flow_name": "chat.threads",
                "output": {"thread_id": "thread.docs"},
                "sequence": 1,
                "stream_channel": "chat",
            }
        ]
    )
    body = build_sse_body(events, {"ok": True})
    text = body.decode("utf-8")
    assert "event: chat.thread.load" in text
    assert "event: return" in text
