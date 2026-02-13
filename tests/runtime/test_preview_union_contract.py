from __future__ import annotations

from types import SimpleNamespace

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.preview.preview_contract import (
    PREVIEW_STATUS_OK,
    PREVIEW_STATUS_UNAVAILABLE,
    PREVIEW_UNION_CONTRACT_ERROR_CODE,
)
from namel3ss.runtime.preview.preview_endpoint import handle_preview_page_request


def test_preview_endpoint_returns_ok_union_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "namel3ss.runtime.preview.preview_endpoint.handle_document_page",
        lambda *args, **kwargs: {
            "document": {
                "checksum": "doc-1",
                "document_id": "doc-1",
                "page_count": 3,
                "source_name": "demo.pdf",
            },
            "highlights": [{"chunk_id": "doc-1:0"}],
            "page": {"number": 2, "text": "Second page text"},
            "pdf_url": "/api/documents/doc-1/pdf#page=2",
        },
    )
    payload, status = handle_preview_page_request(
        SimpleNamespace(),
        document_id="doc-1",
        page_number=2,
        state=None,
        chunk_id=None,
        citation_id=None,
        identity=None,
        policy_decl=None,
    )
    assert status == 200
    assert payload["status"] == PREVIEW_STATUS_OK
    assert payload["page"]["text"] == "Second page text"
    assert payload["reason_code"] == ""


def test_preview_endpoint_returns_unavailable_union_for_non_pdf(monkeypatch) -> None:
    monkeypatch.setattr(
        "namel3ss.runtime.preview.preview_endpoint.handle_document_page",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            Namel3ssError('What happened: "notes.txt" is not a PDF document.')
        ),
    )
    payload, status = handle_preview_page_request(
        SimpleNamespace(),
        document_id="doc-text",
        page_number=1,
        state={"ingestion": {"doc-text": {"preview": "fallback text"}}},
        chunk_id=None,
        citation_id=None,
        identity=None,
        policy_decl=None,
    )
    assert status == 200
    assert payload["status"] == PREVIEW_STATUS_UNAVAILABLE
    assert payload["reason_code"] == "preview_non_pdf"
    assert payload["fallback_snippet"] == "fallback text"


def test_preview_endpoint_uses_4xx_for_true_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "namel3ss.runtime.preview.preview_endpoint.handle_document_page",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            Namel3ssError(
                "Page out of range.",
                details={"error_code": "runtime.preview_page_out_of_range"},
            )
        ),
    )
    payload, status = handle_preview_page_request(
        SimpleNamespace(),
        document_id="doc-1",
        page_number=99,
        state=None,
        chunk_id=None,
        citation_id=None,
        identity=None,
        policy_decl=None,
    )
    assert status == 400
    assert payload["error_code"] == "runtime.preview_page_out_of_range"


def test_preview_endpoint_reports_union_contract_violations(monkeypatch) -> None:
    monkeypatch.setattr(
        "namel3ss.runtime.preview.preview_endpoint.handle_document_page",
        lambda *args, **kwargs: {
            "document": {"checksum": "", "document_id": "", "page_count": 0, "source_name": ""},
            "page": {"number": 0, "text": ""},
            "pdf_url": "",
            "highlights": [],
        },
    )
    payload, status = handle_preview_page_request(
        SimpleNamespace(),
        document_id="",
        page_number=0,
        state=None,
        chunk_id=None,
        citation_id=None,
        identity=None,
        policy_decl=None,
    )
    assert status == 500
    assert payload["error_code"] == PREVIEW_UNION_CONTRACT_ERROR_CODE
