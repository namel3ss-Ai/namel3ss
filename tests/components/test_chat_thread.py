from __future__ import annotations

import pytest

from namel3ss.runtime.components.chat_thread import (
    ChatThreadError,
    apply_chat_event,
    apply_chat_events,
    build_chat_thread_payload,
    normalize_chat_state,
)


def test_normalize_chat_state_defaults() -> None:
    state = normalize_chat_state(None)
    assert state == {"messages": [], "streaming": {}, "selected_citation": None}


def test_apply_chat_events_streaming_is_deterministic() -> None:
    result = apply_chat_events(
        None,
        [
            {"id": "e4", "type": "chat.stream.complete", "message_id": "m1", "order": 4},
            {"id": "e2", "type": "chat.stream.chunk", "message_id": "m1", "chunk": "Hello", "order": 2},
            {"id": "e1", "type": "chat.stream.start", "message_id": "m1", "role": "assistant", "order": 1},
            {"id": "e3", "type": "chat.stream.chunk", "message_id": "m1", "chunk": " world", "order": 3},
        ],
    )
    assert result["streaming"] == {}
    assert result["messages"] == [
        {
            "id": "m1",
            "role": "assistant",
            "content": "Hello world",
            "citations": [],
            "status": "complete",
            "error": None,
        }
    ]


def test_apply_chat_events_serializes_simultaneous_streams_by_order() -> None:
    result = apply_chat_events(
        None,
        [
            {"id": "b1", "type": "chat.stream.start", "message_id": "m2", "order": 20},
            {"id": "a1", "type": "chat.stream.start", "message_id": "m1", "order": 10},
            {"id": "b2", "type": "chat.stream.chunk", "message_id": "m2", "chunk": "B", "order": 21},
            {"id": "a2", "type": "chat.stream.chunk", "message_id": "m1", "chunk": "A", "order": 11},
            {"id": "a3", "type": "chat.stream.complete", "message_id": "m1", "order": 12},
            {"id": "b3", "type": "chat.stream.complete", "message_id": "m2", "order": 22},
        ],
    )
    assert [message["id"] for message in result["messages"]] == ["m1", "m2"]
    assert [message["content"] for message in result["messages"]] == ["A", "B"]


def test_apply_chat_event_select_citation() -> None:
    state = apply_chat_event(None, {"type": "chat.citation.select", "citation_id": "c-1"})
    assert state["selected_citation"] == "c-1"


def test_apply_chat_event_raises_for_unknown_stream_target() -> None:
    with pytest.raises(ChatThreadError) as err:
        apply_chat_event(None, {"type": "chat.stream.chunk", "message_id": "missing", "chunk": "x"})
    assert "No active stream" in str(err.value)


def test_build_chat_thread_payload_reflects_state() -> None:
    state = {
        "messages": [{"id": "m1", "role": "assistant", "content": "Hi", "citations": ["c1"], "status": "complete"}],
        "streaming": {},
        "selected_citation": "c1",
    }
    payload = build_chat_thread_payload(state, component_id="component.chat_thread.1")
    assert payload["type"] == "component.chat_thread"
    assert payload["id"] == "component.chat_thread.1"
    assert payload["messages"][0]["content"] == "Hi"
    assert payload["selected_citation"] == "c1"
