from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.policy import ACTION_INGESTION_REVIEW, evaluate_ingestion_policy, load_ingestion_policy, policy_error
from namel3ss.runtime.backend.document_handler import handle_document_page, handle_document_pdf
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


def test_document_pdf_bytes_retrievable(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    pdf_bytes = _build_pdf(["Page one text.", "Page two text."])
    metadata = store_upload(
        ctx,
        filename="preview.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )

    content, info, filename = handle_document_pdf(ctx, document_id=metadata["checksum"])

    assert content == pdf_bytes
    assert filename == "preview.pdf"
    assert info == {
        "document_id": metadata["checksum"],
        "source_name": "preview.pdf",
        "page_count": 2,
        "checksum": metadata["checksum"],
    }


def test_document_page_render_is_deterministic(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    pdf_bytes = _build_pdf(["Alpha page one.", "Beta page two."])
    metadata = store_upload(
        ctx,
        filename="stable.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )

    first = handle_document_page(ctx, document_id=metadata["checksum"], page_number=2)
    second = handle_document_page(ctx, document_id=metadata["checksum"], page_number="2")

    assert first == second
    assert first["page"]["text"] == "Beta page two."


def test_document_page_invalid_number_fails(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    pdf_bytes = _build_pdf(["One.", "Two."])
    metadata = store_upload(
        ctx,
        filename="limits.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )

    expected = build_guidance_message(
        what="Page 3 is out of range.",
        why="Document has 2 pages.",
        fix="Choose a page between 1 and 2.",
        example="/api/documents/<checksum>/pages/1",
    )
    with pytest.raises(Namel3ssError) as excinfo:
        handle_document_page(ctx, document_id=metadata["checksum"], page_number=3)
    assert str(excinfo.value) == expected


def test_document_preview_policy_enforced(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    pdf_bytes = _build_pdf(["Policy page."])
    metadata = store_upload(
        ctx,
        filename="policy.pdf",
        content_type="application/pdf",
        stream=io.BytesIO(pdf_bytes),
    )
    policy_path = Path(ctx.project_root) / "ingestion.policy.toml"
    policy_path.write_text("[ingestion]\nreview = false\n", encoding="utf-8")

    policy = load_ingestion_policy(ctx.project_root, ctx.app_path, policy_decl=None)
    decision = evaluate_ingestion_policy(policy, ACTION_INGESTION_REVIEW, identity=None)
    expected = policy_error(ACTION_INGESTION_REVIEW, decision)

    with pytest.raises(Namel3ssError) as excinfo:
        handle_document_page(ctx, document_id=metadata["checksum"], page_number=1)

    assert str(excinfo.value) == str(expected)
