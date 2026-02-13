from __future__ import annotations

import io
import json
from types import SimpleNamespace

from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.store.memory_store import MemoryStore


def _program(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    return SimpleNamespace(app_path=app_path, project_root=tmp_path, routes=[])


def test_chat_thread_list_route_returns_deterministic_rows(tmp_path) -> None:
    program = _program(tmp_path)
    store = MemoryStore()
    store.save_state(
        {
            "chat": {
                "active_thread_id": "thread.main",
                "models": [{"id": "model.alpha", "name": "Alpha"}],
                "selected_model_ids": ["model.alpha"],
                "threads": [
                    {"id": "thread.main", "name": "Main"},
                    {"id": "thread.docs", "name": "Docs"},
                ],
                "thread_snapshots": {
                    "thread.docs": {
                        "messages_graph": {
                            "active_message_id": "message.1",
                            "edges": [],
                            "nodes": [{"content": "Doc question", "id": "message.1", "role": "user"}],
                        }
                    }
                },
            }
        }
    )
    registry = RouteRegistry()
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chat/threads",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert result is not None
    assert result.status == 200
    assert result.body is None
    assert result.payload["ok"] is True
    rows = result.payload["chat"]["threads"]
    assert [row["id"] for row in rows] == ["thread.main", "thread.docs"]
    assert [row["message_count"] for row in rows] == [0, 1]
    assert rows[1]["last_message_id"] == "message.1"


def test_chat_thread_save_then_load_persists_graph_snapshot(tmp_path) -> None:
    program = _program(tmp_path)
    store = MemoryStore()
    store.save_state(
        {
            "chat": {
                "active_thread_id": "thread.main",
                "messages": [{"content": "Hello", "id": "message.1", "role": "user"}],
                "messages_graph": {
                    "active_message_id": "message.1",
                    "edges": [],
                    "nodes": [{"content": "Hello", "id": "message.1", "role": "user"}],
                },
                "models": [{"id": "model.alpha", "name": "Alpha"}],
                "selected_model_ids": ["model.alpha"],
                "threads": [{"id": "thread.main", "name": "Main"}],
            }
        }
    )
    registry = RouteRegistry()

    save_payload = {
        "composer_state": {"attachments": [], "draft": "", "tools": [], "web_search": False},
        "messages_graph": {
            "active_message_id": "message.2",
            "edges": [{"from": "message.1", "to": "message.2"}],
            "nodes": [
                {"content": "Doc question", "id": "message.1", "role": "user"},
                {"content": "Doc answer", "id": "message.2", "role": "assistant"},
            ],
        },
        "name": "Docs",
    }
    save_bytes = json.dumps(save_payload).encode("utf-8")
    save_result = dispatch_route(
        registry=registry,
        method="PUT",
        raw_path="/api/chat/threads/thread.docs/save",
        headers={"Content-Length": str(len(save_bytes))},
        rfile=io.BytesIO(save_bytes),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert save_result is not None
    assert save_result.status == 200
    assert save_result.payload["thread"] == {"id": "thread.docs", "name": "Docs"}

    state_after_save = store.load_state()
    docs_snapshot = state_after_save["chat"]["thread_snapshots"]["thread.docs"]
    assert docs_snapshot["messages_graph"]["nodes"][1]["content"] == "Doc answer"
    assert state_after_save["chat"]["active_thread_id"] == "thread.main"

    load_result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chat/threads/thread.docs?activate=true",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert load_result is not None
    assert load_result.status == 200
    assert load_result.payload["chat"]["active_thread_id"] == "thread.docs"
    assert load_result.payload["chat"]["messages_graph"]["active_message_id"] == "message.2"

    state_after_load = store.load_state()
    assert state_after_load["chat"]["active_thread_id"] == "thread.docs"
    assert "thread.main" in state_after_load["chat"]["thread_snapshots"]


def test_chat_thread_routes_stream_only_when_explicit_requested(tmp_path) -> None:
    program = _program(tmp_path)
    store = MemoryStore()
    registry = RouteRegistry()

    plain_result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chat/threads",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert plain_result is not None
    assert plain_result.payload is not None
    assert plain_result.body is None

    stream_result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chat/threads?stream=true",
        headers={},
        rfile=io.BytesIO(b""),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert stream_result is not None
    assert stream_result.body is not None
    assert stream_result.content_type == "text/event-stream; charset=utf-8"
    text = stream_result.body.decode("utf-8")
    assert "event: chat.thread.list" in text
    assert "event: return" in text
