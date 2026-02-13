from __future__ import annotations

import io
from types import SimpleNamespace

from namel3ss.runtime.router.dispatch import dispatch_route
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.runtime.store.memory_store import MemoryStore


def _program(tmp_path):
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n', encoding="utf-8")
    return SimpleNamespace(app_path=app_path, project_root=tmp_path, routes=[])


def _state() -> dict:
    return {
        "index": {
            "chunks": [
                {
                    "chunk_id": "doc-b:1",
                    "chunk_index": 1,
                    "document_id": "doc-b",
                    "ingestion_phase": "quick",
                    "page_number": 2,
                    "source_name": "b.txt",
                    "text": "Beta row.",
                },
                {
                    "chunk_id": "doc-a:0",
                    "chunk_index": 0,
                    "document_id": "doc-a",
                    "ingestion_phase": "deep",
                    "page_number": 1,
                    "source_name": "a.txt",
                    "text": "Alpha row.",
                },
            ]
        },
        "ingestion": {
            "doc-a": {"page_text": ["Alpha row."]},
            "doc-b": {"page_text": ["Beta page one.", "Beta row."]},
        },
    }


def test_chunk_inspection_route_returns_sorted_rows_and_preview_targets(tmp_path) -> None:
    store = MemoryStore()
    store.save_state(_state())
    registry = RouteRegistry()
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chunks/inspection",
        headers={},
        rfile=io.BytesIO(b""),
        program=_program(tmp_path),
        identity=None,
        auth_context=None,
        store=store,
    )
    assert result is not None
    assert result.status == 200
    assert result.payload is not None
    assert result.payload["ok"] is True
    rows = result.payload["chunk_inspection"]["rows"]
    assert [row["doc_id"] for row in rows] == ["doc-a", "doc-b"]
    assert rows[0]["preview_url"] == "/api/documents/doc-a/pages/1?chunk_id=doc-a%3A0"
    assert rows[1]["preview_url"] == "/api/documents/doc-b/pages/2?chunk_id=doc-b%3A1"


def test_chunk_click_to_page_routing_contract_filters_document_rows(tmp_path) -> None:
    store = MemoryStore()
    store.save_state(_state())
    registry = RouteRegistry()
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chunks/inspection?document_id=doc-b",
        headers={},
        rfile=io.BytesIO(b""),
        program=_program(tmp_path),
        identity=None,
        auth_context=None,
        store=store,
    )
    assert result is not None
    assert result.status == 200
    payload = result.payload["chunk_inspection"]
    rows = payload["rows"]
    assert len(rows) == 1
    assert rows[0]["doc_id"] == "doc-b"
    assert rows[0]["preview_url"] == "/api/documents/doc-b/pages/2?chunk_id=doc-b%3A1"
    assert payload["pages"] == [{"page_number": 1, "snippet": "Beta page one."}, {"page_number": 2, "snippet": "Beta row."}]


def test_chunk_inspection_route_supports_stream_response(tmp_path) -> None:
    store = MemoryStore()
    store.save_state(_state())
    registry = RouteRegistry()
    result = dispatch_route(
        registry=registry,
        method="GET",
        raw_path="/api/chunks/inspection?stream=true",
        headers={},
        rfile=io.BytesIO(b""),
        program=_program(tmp_path),
        identity=None,
        auth_context=None,
        store=store,
    )
    assert result is not None
    assert result.status == 200
    assert result.body is not None
    assert result.content_type == "text/event-stream; charset=utf-8"
    text = result.body.decode("utf-8")
    assert "event: yield" in text
    assert "event: return" in text
