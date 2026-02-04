from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.api import run_ingestion
from namel3ss.ingestion.highlight import attach_highlight_anchors
from namel3ss.runtime.backend.document_handler import handle_document_page
from namel3ss.runtime.backend.upload_store import store_upload


def _ctx(tmp_path: Path) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text(
        'spec is "1.0"\ncapabilities:\n  uploads\nflow "demo":\n  return "ok"\n',
        encoding="utf-8",
    )
    return SimpleNamespace(
        capabilities=("uploads",),
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _build_pdf(pages: list[str]) -> bytes:
    catalog_id = 1
    pages_id = 2
    page_ids = list(range(3, 3 + len(pages)))
    content_ids = list(range(3 + len(pages), 3 + len(pages) * 2))
    objects: list[str] = [
        "%PDF-1.4",
        f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj",
        f"{pages_id} 0 obj\n<< /Type /Pages /Count {len(pages)} /Kids [{_kids_refs(page_ids)}] >>\nendobj",
    ]
    for page_id, content_id in zip(page_ids, content_ids):
        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent {pages_id} 0 R /Contents {content_id} 0 R >>\nendobj"
        )
    for content_id, text in zip(content_ids, pages):
        stream = f"({text})"
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj"
        )
    objects.append("%%EOF")
    return ("\n".join(objects) + "\n").encode("utf-8")


def _kids_refs(page_ids: list[int]) -> str:
    return " ".join(f"{page_id} 0 R" for page_id in page_ids)


def test_highlight_anchor_matches_page_text(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    page_text = (
        "Alpha page contains distinct words about invoices policies and stability so ingestion remains deterministic."
    )
    pdf_bytes = _build_pdf([page_text])
    metadata = store_upload(
        ctx,
        filename="highlight.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    chunk = result["chunks"][0]
    highlight = chunk["highlight"]
    assert highlight["status"] == "exact"
    report_text = result["report"]["page_text"][0]
    assert report_text[highlight["start_char"] : highlight["end_char"]] == chunk["text"]


def test_highlight_unavailable_for_mismatch() -> None:
    pages = ["Alpha page text."]
    chunks = [
        {
            "chunk_index": 0,
            "page_number": 1,
            "text": "Different text.",
        }
    ]
    attach_highlight_anchors(pages, chunks, document_id="doc-1", max_chars=800, overlap=100)
    highlight = chunks[0]["highlight"]
    assert highlight["status"] == "unavailable"
    assert highlight["start_char"] is None
    assert highlight["end_char"] is None


def test_document_page_invalid_highlight_span_fails(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    page_text = "Alpha page text."
    pdf_bytes = _build_pdf([page_text])
    metadata = store_upload(
        ctx,
        filename="bad-highlight.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )
    bad_highlight = {
        "document_id": metadata["checksum"],
        "page_number": 1,
        "chunk_id": f"{metadata['checksum']}:0",
        "start_char": 0,
        "end_char": len(page_text) + 4,
        "status": "exact",
    }
    state = {
        "ingestion": {metadata["checksum"]: {"page_text": [page_text]}},
        "index": {
            "chunks": [
                {
                    "upload_id": metadata["checksum"],
                    "document_id": metadata["checksum"],
                    "source_name": "bad-highlight.pdf",
                    "page_number": 1,
                    "chunk_index": 0,
                    "chunk_id": f"{metadata['checksum']}:0",
                    "highlight": bad_highlight,
                }
            ]
        },
    }
    expected = build_guidance_message(
        what="Highlight span is out of range.",
        why="Highlight offsets must fit within the page text.",
        fix="Re-run ingestion to rebuild highlight anchors.",
        example='{"status":"exact","start_char":0,"end_char":42}',
    )
    with pytest.raises(Namel3ssError) as excinfo:
        handle_document_page(ctx, document_id=metadata["checksum"], page_number=1, state=state)
    assert str(excinfo.value) == expected
