from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.api import run_ingestion
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


def test_pdf_page_provenance_multi_page(tmp_path: Path) -> None:
    page_one = (
        "Alpha page one contains distinct words about invoices policies and stability so ingestion stays deterministic."
    )
    page_two = (
        "Beta page two adds unique language about audits provenance and tracing so page references remain stable."
    )
    pdf_bytes = _build_pdf([page_one, page_two])
    metadata = store_upload(
        _ctx(tmp_path),
        filename="sample.pdf",
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

    assert result["status"] == "pass"
    expected_chunks = [
        {
            "chunk_index": 0,
            "text": page_one,
            "chars": len(page_one),
            "page_number": 1,
            "document_id": metadata["checksum"],
            "source_name": "sample.pdf",
        },
        {
            "chunk_index": 1,
            "text": page_two,
            "chars": len(page_two),
            "page_number": 2,
            "document_id": metadata["checksum"],
            "source_name": "sample.pdf",
        },
    ]
    assert result["chunks"] == expected_chunks
    assert result["report"]["provenance"] == {
        "document_id": metadata["checksum"],
        "source_name": "sample.pdf",
    }

    assert state["index"]["chunks"] == [
        {
            "upload_id": metadata["checksum"],
            "document_id": metadata["checksum"],
            "source_name": "sample.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "chunk_id": f"{metadata['checksum']}:0",
            "order": 0,
            "text": page_one,
            "chars": len(page_one),
            "low_quality": False,
        },
        {
            "upload_id": metadata["checksum"],
            "document_id": metadata["checksum"],
            "source_name": "sample.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "chunk_id": f"{metadata['checksum']}:1",
            "order": 1,
            "text": page_two,
            "chars": len(page_two),
            "low_quality": False,
        },
    ]


def test_pdf_page_provenance_is_deterministic(tmp_path: Path) -> None:
    page_one = "Determinism starts with a stable first page and explicit provenance."
    page_two = "Determinism continues with a stable second page and ordered chunks."
    pdf_bytes = _build_pdf([page_one, page_two])
    metadata = store_upload(
        _ctx(tmp_path),
        filename="stable.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )

    first_state: dict = {}
    second_state: dict = {}
    first = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=first_state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    second = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=second_state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )

    assert first["report"] == second["report"]
    assert first["chunks"] == second["chunks"]
    assert first_state["index"]["chunks"] == second_state["index"]["chunks"]


def test_pdf_missing_page_info_fails_explicitly(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.4\n/Type /Page\n/Type /Page\n%%EOF"
    metadata = store_upload(
        _ctx(tmp_path),
        filename="bad.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )
    expected = build_guidance_message(
        what='Page provenance for "bad.pdf" expected 2 pages but found 1.',
        why="Ingestion requires deterministic page numbers for every chunk.",
        fix="Provide a PDF with readable page structure or convert it to text with form-feed page breaks.",
        example='{"upload_id":"<checksum>"}',
    )
    with pytest.raises(Namel3ssError) as excinfo:
        run_ingestion(
            upload_id=metadata["checksum"],
            mode=None,
            state={},
            project_root=str(tmp_path),
            app_path=(tmp_path / "app.ai").as_posix(),
        )
    assert str(excinfo.value) == expected


def test_text_ingestion_single_page_provenance_is_compatible(tmp_path: Path) -> None:
    payload = (
        b"Simple text with enough distinct words to pass the deterministic quality gate for ingestion and retrieval."
    )
    metadata = store_upload(
        _ctx(tmp_path),
        filename="notes.txt",
        content_type="text/plain",
        stream=io.BytesIO(payload),
    )
    state: dict = {}
    result = run_ingestion(
        upload_id=metadata["checksum"],
        mode=None,
        state=state,
        project_root=str(tmp_path),
        app_path=(tmp_path / "app.ai").as_posix(),
    )
    text = payload.decode("utf-8")
    assert result["chunks"] == [
        {
            "chunk_index": 0,
            "text": text,
            "chars": len(text),
            "page_number": 1,
            "document_id": metadata["checksum"],
            "source_name": "notes.txt",
        }
    ]
