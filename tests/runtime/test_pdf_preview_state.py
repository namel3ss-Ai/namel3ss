from __future__ import annotations

import io
import json
from types import SimpleNamespace

from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.state.pdf_preview_state import (
    apply_pdf_preview_citation_state,
    ensure_pdf_preview_state,
    normalize_pdf_preview_state,
)


def _program(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    return SimpleNamespace(app_path=app_path, project_root=tmp_path, routes=[])


def test_pdf_preview_state_defaults_are_stable() -> None:
    chat: dict = {}
    first = ensure_pdf_preview_state(chat)
    second = ensure_pdf_preview_state(chat)
    assert first == second
    assert first == {
        "active": False,
        "chunk_id": "",
        "citation_id": "",
        "color_index": 0,
        "deep_link_query": "",
        "doc_id": "",
        "highlight_mode": "unavailable",
        "page_number": 1,
        "preview_url": "",
        "schema_version": "ui.pdf_preview_state@1",
    }


def test_pdf_preview_selection_state_builds_stable_payload() -> None:
    chat: dict = {}
    citation = {
        "citation_id": "cit.7",
        "chunk_id": "doc-a:2",
        "doc_id": "doc-a",
        "page_number": 4,
        "preview_target": {"page": 4, "token_positions": [{"index": 0, "token": "Alpha", "start_char": 1, "end_char": 6}]},
        "extensions": {"deep_link_query": "doc=doc-a&page=4&cit=cit.7"},
    }
    first = apply_pdf_preview_citation_state(chat, citation)
    second = normalize_pdf_preview_state(first)
    assert first == second
    assert first["active"] is True
    assert first["doc_id"] == "doc-a"
    assert first["chunk_id"] == "doc-a:2"
    assert first["highlight_mode"] == "token_positions"
    assert first["deep_link_query"] == "doc=doc-a&page=4&cit=cit.7"
    assert first["preview_url"] == "/api/documents/doc-a/pages/4?chunk_id=doc-a%3A2&citation_id=cit.7"


def test_chat_thread_routes_roundtrip_pdf_preview_state(tmp_path) -> None:
    program = _program(tmp_path)
    store = MemoryStore()
    store.save_state(
        {
            "chat": {
                "active_thread_id": "thread.main",
                "messages_graph": {"active_message_id": None, "edges": [], "nodes": []},
                "models": [{"id": "model.alpha", "name": "Alpha"}],
                "selected_model_ids": ["model.alpha"],
                "threads": [{"id": "thread.main", "name": "Main"}],
            }
        }
    )
    registry = RouteRegistry()

    save_payload = {
        "messages_graph": {"active_message_id": None, "edges": [], "nodes": []},
        "pdf_preview_state": {
            "active": True,
            "chunk_id": "doc-a:0",
            "citation_id": "cit.a",
            "deep_link_query": "doc=doc-a&page=1&cit=cit.a",
            "doc_id": "doc-a",
            "highlight_mode": "span",
            "page_number": 1,
            "preview_url": "/api/documents/doc-a/pages/1?chunk_id=doc-a%3A0&citation_id=cit.a",
        },
    }
    body = json.dumps(save_payload).encode("utf-8")
    save_result = dispatch_route(
        registry=registry,
        method="PUT",
        raw_path="/api/chat/threads/thread.docs/save",
        headers={"Content-Length": str(len(body))},
        rfile=io.BytesIO(body),
        program=program,
        identity=None,
        auth_context=None,
        store=store,
    )
    assert save_result is not None
    assert save_result.status == 200
    assert save_result.payload["chat"]["pdf_preview_state"]["citation_id"] == "cit.a"

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
    assert load_result.payload["chat"]["pdf_preview_state"]["deep_link_query"] == "doc=doc-a&page=1&cit=cit.a"
