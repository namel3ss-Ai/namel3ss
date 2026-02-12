from __future__ import annotations

import pytest

from namel3ss.studio.preview.preview_panel import render_preview_panel


def test_preview_panel_renders_ok_payload_snapshot() -> None:
    payload = {
        "doc_meta": {
            "checksum": "doc-1",
            "document_id": "doc-1",
            "page_count": 2,
            "requested_page": 1,
            "source_name": "doc.pdf",
        },
        "fallback_snippet": "",
        "highlights": [{"chunk_id": "doc-1:0"}],
        "page": {"number": 1, "text": "Alpha"},
        "pdf_url": "/api/documents/doc-1/pdf#page=1",
        "reason": "",
        "reason_code": "",
        "status": "ok",
    }
    assert render_preview_panel(payload) == {
        "doc_meta": {
            "checksum": "doc-1",
            "document_id": "doc-1",
            "page_count": 2,
            "requested_page": 1,
            "source_name": "doc.pdf",
        },
        "highlights": [{"chunk_id": "doc-1:0"}],
        "panel": {
            "message": "",
            "mode": "ok",
            "page_number": 1,
            "page_text": "Alpha",
            "reason": "",
            "reason_code": "",
        },
        "pdf_url": "/api/documents/doc-1/pdf#page=1",
    }


def test_preview_panel_renders_unavailable_payload_snapshot() -> None:
    payload = {
        "doc_meta": {
            "checksum": "doc-2",
            "document_id": "doc-2",
            "page_count": 0,
            "requested_page": 1,
            "source_name": "",
        },
        "fallback_snippet": "Fallback chunk text",
        "highlights": [],
        "page": {"number": 1, "text": ""},
        "pdf_url": "",
        "reason": "Preview unavailable",
        "reason_code": "preview_unavailable",
        "status": "unavailable",
    }
    assert render_preview_panel(payload) == {
        "doc_meta": {
            "checksum": "doc-2",
            "document_id": "doc-2",
            "page_count": 0,
            "requested_page": 1,
            "source_name": "",
        },
        "highlights": [],
        "panel": {
            "message": "Preview unavailable\n\nFallback snippet:\nFallback chunk text",
            "mode": "unavailable",
            "page_number": 1,
            "page_text": "",
            "reason": "Preview unavailable",
            "reason_code": "preview_unavailable",
        },
        "pdf_url": "",
    }


def test_preview_panel_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError) as excinfo:
        render_preview_panel({"status": "ok"})
    assert "N3E_PREVIEW_UNION_CONTRACT_VIOLATION" in str(excinfo.value)
