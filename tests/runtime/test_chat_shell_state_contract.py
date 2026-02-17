from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.state.chat_shell import (
    append_chat_user_message,
    begin_chat_message_regeneration,
    create_chat_thread,
    ensure_chat_shell_state,
    request_chat_stream_cancel,
    select_chat_branch,
    select_chat_models,
    select_chat_thread,
)


def test_chat_shell_contract_initializes_defaults() -> None:
    state: dict = {}
    chat = ensure_chat_shell_state(state)
    assert state["chat"] is chat
    assert chat["threads"] == []
    assert chat["active_thread_id"] == ""
    assert chat["models"] == []
    assert chat["selected_model_ids"] == []
    assert chat["messages_graph"] == {"active_message_id": None, "edges": [], "nodes": []}
    assert chat["composer_state"] == {"attachments": [], "draft": "", "tools": [], "web_search": False}
    assert chat["stream_state"] == {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []}
    assert chat["active_thread"] == ""
    assert chat["active_models"] == []


def test_chat_shell_contract_migrates_legacy_fields_and_builds_graph() -> None:
    state = {
        "chat": {
            "messages": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
            "threads": [
                {"id": "thread.main", "name": "Main"},
                {"id": "thread.docs", "name": "Docs"},
            ],
            "active_thread": ["thread.docs"],
            "models": [
                {"id": "model.beta", "name": "Beta"},
                {"id": "model.alpha", "name": "Alpha"},
            ],
            "active_models": ["model.beta", "model.alpha", "model.beta"],
        }
    }
    chat = ensure_chat_shell_state(state)
    assert chat["active_thread_id"] == "thread.docs"
    assert chat["active_thread"] == "thread.docs"
    assert chat["selected_model_ids"] == ["model.alpha", "model.beta"]
    assert chat["active_models"] == ["model.alpha", "model.beta"]
    assert chat["messages_graph"] == {
        "active_message_id": "message.2",
        "edges": [{"from": "message.1", "to": "message.2"}],
        "nodes": [
            {"content": "Hi", "id": "message.1", "role": "user"},
            {"content": "Hello", "id": "message.2", "role": "assistant"},
        ],
    }


def test_chat_shell_contract_rebuilds_graph_when_messages_outdate_graph_nodes() -> None:
    state = {
        "chat": {
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Answer"},
            ],
            "messages_graph": {
                "active_message_id": "message.1",
                "edges": [],
                "nodes": [{"id": "message.1", "role": "assistant", "content": "Old answer only"}],
            },
        }
    }
    chat = ensure_chat_shell_state(state)
    assert chat["messages_graph"] == {
        "active_message_id": "message.2",
        "edges": [{"from": "message.1", "to": "message.2"}],
        "nodes": [
            {"content": "Question", "id": "message.1", "role": "user"},
            {"content": "Answer", "id": "message.2", "role": "assistant"},
        ],
    }
    assert chat["messages"] == [
        {"content": "Question", "role": "user"},
        {"content": "Answer", "role": "assistant"},
    ]


def test_select_chat_thread_updates_canonical_and_legacy_keys() -> None:
    state = {"chat": {"threads": [{"id": "thread.main", "name": "Main"}, {"id": "thread.docs", "name": "Docs"}]}}
    select_chat_thread(state, "thread.docs")
    assert state["chat"]["active_thread_id"] == "thread.docs"
    assert state["chat"]["active_thread"] == "thread.docs"


def test_select_chat_models_rejects_unknown_ids() -> None:
    state = {"chat": {"models": [{"id": "model.alpha", "name": "Alpha"}]}}
    with pytest.raises(Namel3ssError) as err:
        select_chat_models(state, ["model.missing"])
    assert 'Unknown model id "model.missing"' in str(err.value)


def test_select_chat_models_canonicalizes_to_sorted_unique_ids() -> None:
    state = {"chat": {"models": [{"id": "model.alpha", "name": "Alpha"}, {"id": "model.beta", "name": "Beta"}]}}
    selected = select_chat_models(state, ["model.beta", "model.alpha", "model.beta"])
    assert selected == ["model.alpha", "model.beta"]
    assert state["chat"]["selected_model_ids"] == ["model.alpha", "model.beta"]
    assert state["chat"]["active_models"] == ["model.alpha", "model.beta"]


def test_create_chat_thread_uses_deterministic_identity_and_reset_state() -> None:
    state = {
        "chat": {
            "threads": [{"id": "thread.main", "name": "Main"}],
            "messages": [{"role": "user", "content": "hi"}],
        }
    }
    created = create_chat_thread(state, "Main")
    assert created == {"id": "thread.main.2", "name": "Main 2"}
    assert state["chat"]["active_thread_id"] == "thread.main.2"
    assert state["chat"]["active_thread"] == "thread.main.2"
    assert state["chat"]["messages"] == []
    assert state["chat"]["messages_graph"] == {"active_message_id": None, "edges": [], "nodes": []}
    assert state["chat"]["stream_state"] == {
        "active_message_id": None,
        "cancel_requested": False,
        "phase": "idle",
        "tokens": [],
    }


def test_append_chat_user_message_updates_graph_and_stream_state() -> None:
    state = {"chat": {"messages": [{"role": "assistant", "content": "Hello"}]}}
    created = append_chat_user_message(state, "How are you?")
    assert created == {"content": "How are you?", "id": "message.2", "role": "user"}
    assert state["chat"]["messages_graph"] == {
        "active_message_id": "message.2",
        "edges": [{"from": "message.1", "to": "message.2"}],
        "nodes": [
            {"content": "Hello", "id": "message.1", "role": "assistant"},
            {"content": "How are you?", "id": "message.2", "role": "user"},
        ],
    }
    assert state["chat"]["messages"] == [
        {"content": "Hello", "id": "message.1", "role": "assistant"},
        {"content": "How are you?", "id": "message.2", "role": "user"},
    ]
    assert state["chat"]["stream_state"] == {
        "active_message_id": "message.2",
        "cancel_requested": False,
        "phase": "thinking",
        "tokens": [],
    }


def test_select_chat_branch_updates_active_message() -> None:
    state = {
        "chat": {
            "messages_graph": {
                "nodes": [
                    {"id": "message.1", "role": "user", "content": "A"},
                    {"id": "message.2", "role": "assistant", "content": "B"},
                ]
            }
        }
    }
    selected = select_chat_branch(state, "message.2")
    assert selected == "message.2"
    assert state["chat"]["messages_graph"]["active_message_id"] == "message.2"
    assert state["chat"]["stream_state"]["active_message_id"] == "message.2"


def test_begin_chat_message_regeneration_prefers_explicit_target() -> None:
    state = {
        "chat": {
            "messages_graph": {
                "active_message_id": "message.3",
                "nodes": [
                    {"id": "message.1", "role": "user", "content": "A"},
                    {"id": "message.2", "role": "assistant", "content": "B"},
                    {"id": "message.3", "role": "assistant", "content": "C"},
                ],
            },
            "stream_state": {"phase": "streaming", "tokens": ["a"], "cancel_requested": True},
        }
    }
    message_id = begin_chat_message_regeneration(state, message_id="message.2")
    assert message_id == "message.2"
    assert state["chat"]["messages_graph"]["active_message_id"] == "message.2"
    assert state["chat"]["stream_state"] == {
        "active_message_id": "message.2",
        "cancel_requested": False,
        "phase": "thinking",
        "tokens": [],
    }


def test_request_chat_stream_cancel_sets_cancel_and_clears_tokens() -> None:
    state = {"chat": {"stream_state": {"phase": "streaming", "tokens": ["a", "b"]}}}
    stream_state = request_chat_stream_cancel(state)
    assert stream_state == {
        "active_message_id": None,
        "cancel_requested": True,
        "phase": "idle",
        "tokens": [],
    }
    assert state["chat"]["stream_state"] == stream_state
