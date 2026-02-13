from __future__ import annotations

from namel3ss.rag.determinism.text_normalizer import build_boundary_signature
from namel3ss.rag.indexing.chunk_inspector_service import build_chunk_inspection_payload
from namel3ss.rag.ingestion import run_ingestion_pipeline


def test_chunk_inspector_snapshot_contract_and_ordering() -> None:
    state = {
        "index": {
            "chunks": [
                {
                    "chunk_id": "doc-b:1",
                    "chunk_index": 1,
                    "document_id": "doc-b",
                    "ingestion_phase": "quick",
                    "page_number": 3,
                    "source_name": "b.txt",
                    "text": "Beta page content.",
                },
                {
                    "chunk_id": "doc-a:0",
                    "chunk_index": 0,
                    "document_id": "doc-a",
                    "ingestion_phase": "deep",
                    "page_number": 1,
                    "source_name": "a.txt",
                    "text": "Alpha page content.",
                },
            ]
        },
        "ingestion": {
            "doc-a": {
                "page_text": ["Alpha page content.", "Alpha page two content."],
                "provenance": {"source_name": "a.txt"},
            },
            "doc-b": {
                "page_text": ["Beta page one.", "Beta page two.", "Beta page content."],
                "provenance": {"source_name": "b.txt"},
            },
        },
    }
    payload = build_chunk_inspection_payload(state=state)
    rows = payload["rows"]
    assert [row["doc_id"] for row in rows] == ["doc-a", "doc-b"]
    assert [row["chunk_index"] for row in rows] == [0, 1]
    assert rows[0]["boundary_signature"] == build_boundary_signature(
        doc_id="doc-a",
        page_number=1,
        chunk_index=0,
        text="Alpha page content.",
    )
    assert rows[1]["boundary_signature"] == build_boundary_signature(
        doc_id="doc-b",
        page_number=3,
        chunk_index=1,
        text="Beta page content.",
    )
    assert rows[0]["deep_link_query"] == "doc=doc-a&page=1&chunk=doc-a%3A0"
    assert rows[0]["preview_url"] == "/api/documents/doc-a/pages/1?chunk_id=doc-a%3A0"
    assert payload["documents"] == [
        {"chunk_count": 1, "doc_id": "doc-a", "page_count": 2, "source_name": "a.txt"},
        {"chunk_count": 1, "doc_id": "doc-b", "page_count": 3, "source_name": "b.txt"},
    ]


def test_chunk_inspector_filtered_pages_payload() -> None:
    state = {
        "index": {
            "chunks": [
                {
                    "chunk_id": "doc-a:0",
                    "chunk_index": 0,
                    "document_id": "doc-a",
                    "ingestion_phase": "deep",
                    "page_number": 1,
                    "source_name": "a.txt",
                    "text": "Alpha page content.",
                },
                {
                    "chunk_id": "doc-b:0",
                    "chunk_index": 0,
                    "document_id": "doc-b",
                    "ingestion_phase": "deep",
                    "page_number": 1,
                    "source_name": "b.txt",
                    "text": "Beta page content.",
                },
            ]
        },
        "ingestion": {
            "doc-a": {
                "page_text": ["Alpha page content.", "Alpha page two content."],
                "provenance": {"source_name": "a.txt"},
            }
        },
    }
    payload = build_chunk_inspection_payload(state=state, document_id="doc-a")
    rows = payload["rows"]
    assert len(rows) == 1
    assert rows[0]["doc_id"] == "doc-a"
    assert payload["pages"] == [
        {"page_number": 1, "snippet": "Alpha page content."},
        {"page_number": 2, "snippet": "Alpha page two content."},
    ]


def test_chunk_index_and_boundary_signature_are_stable_across_whitespace_variants() -> None:
    first_state: dict = {}
    second_state: dict = {}
    first = run_ingestion_pipeline(
        state=first_state,
        content=b"Alpha  policy line\n\nBeta line",
        source_name="policy.txt",
        source_identity="fixtures/policy-stable.txt",
        source_type="upload",
        source_uri="upload://fixtures/policy-stable.txt",
        mime_type="text/plain",
    )
    second = run_ingestion_pipeline(
        state=second_state,
        content=b"Alpha policy line\n\nBeta line",
        source_name="policy.txt",
        source_identity="fixtures/policy-stable.txt",
        source_type="upload",
        source_uri="upload://fixtures/policy-stable.txt",
        mime_type="text/plain",
    )
    first_doc_id = first["document"]["doc_id"]
    second_doc_id = second["document"]["doc_id"]
    assert first_doc_id == second_doc_id

    first_payload = build_chunk_inspection_payload(state=first_state, document_id=first_doc_id)
    second_payload = build_chunk_inspection_payload(state=second_state, document_id=second_doc_id)
    first_rows = first_payload["rows"]
    second_rows = second_payload["rows"]
    assert [row["chunk_index"] for row in first_rows] == [row["chunk_index"] for row in second_rows]
    assert [row["boundary_signature"] for row in first_rows] == [row["boundary_signature"] for row in second_rows]
