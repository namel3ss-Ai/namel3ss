from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.extract import extract_pages
from namel3ss.ingestion.normalize import sanitize_text
from namel3ss.ingestion.policy import (
    ACTION_INGESTION_REVIEW,
    evaluate_ingestion_policy,
    load_ingestion_policy,
    policy_error,
)
from namel3ss.runtime.backend.upload_contract import clean_upload_filename
from namel3ss.runtime.backend.document_highlight import fallback_highlights, highlights_from_state
from namel3ss.persistence.local_store import LocalStore
from namel3ss.runtime.backend.upload_store import list_uploads
from namel3ss.secrets import collect_secret_values


@dataclass(frozen=True)
class DocumentPayload:
    document_id: str
    source_name: str
    page_count: int
    checksum: str
    content: bytes
    detected: dict

    @property
    def info(self) -> dict:
        return {
            "document_id": self.document_id,
            "source_name": self.source_name,
            "page_count": self.page_count,
            "checksum": self.checksum,
        }


def handle_document_pdf(
    ctx,
    *,
    document_id: str,
    identity: dict | None = None,
    policy_decl: object | None = None,
) -> tuple[bytes, dict, str]:
    payload = _load_document(
        ctx,
        document_id=document_id,
        identity=identity,
        policy_decl=policy_decl,
        require_page_metadata=False,
    )
    filename = clean_upload_filename(payload.source_name)
    return payload.content, payload.info, filename


def handle_document_page(
    ctx,
    *,
    document_id: str,
    page_number: object,
    state: dict | None = None,
    chunk_id: str | None = None,
    citation_id: str | None = None,
    identity: dict | None = None,
    policy_decl: object | None = None,
    secret_values: list[str] | None = None,
) -> dict:
    payload = _load_document(ctx, document_id=document_id, identity=identity, policy_decl=policy_decl)
    page_value = _coerce_page_number(page_number)
    if page_value is None:
        raise Namel3ssError(_page_number_message(page_number))
    if page_value < 1 or page_value > payload.page_count:
        raise Namel3ssError(_page_range_message(page_value, payload.page_count))
    if state is None:
        cleaned = _page_text_from_pdf(ctx, payload, page_value, secret_values=secret_values)
        highlights = fallback_highlights(payload.document_id, page_value, chunk_id, citation_id=citation_id)
    else:
        cleaned = _page_text_from_state(state, payload, page_value)
        highlights = highlights_from_state(
            state,
            payload.document_id,
            page_value,
            chunk_id,
            cleaned,
            citation_id=citation_id,
        )
    return {
        "ok": True,
        "document": payload.info,
        "page": {
            "number": page_value,
            "text": cleaned,
        },
        "pdf_url": f"/api/documents/{payload.document_id}/pdf#page={page_value}",
        "highlights": highlights,
    }


def _load_document(
    ctx,
    *,
    document_id: str,
    identity: dict | None,
    policy_decl: object | None,
    require_page_metadata: bool = True,
) -> DocumentPayload:
    doc_id = _normalize_document_id(document_id)
    _require_uploads_capability(ctx)
    _require_review_policy(ctx, identity=identity, policy_decl=policy_decl)
    metadata = _resolve_metadata(ctx, doc_id)
    content = _read_upload_bytes(ctx, metadata)
    detected = detect_upload(metadata, content=content)
    source_name = _source_name_from_metadata(metadata)
    doc_type = str(detected.get("type") or "")
    if doc_type != "pdf":
        raise Namel3ssError(_pdf_only_message(source_name))
    page_count_raw = detected.get("page_count")
    has_page_count = isinstance(page_count_raw, int) and not isinstance(page_count_raw, bool) and page_count_raw > 0
    if require_page_metadata and not has_page_count:
        raise Namel3ssError(_pdf_page_count_message(source_name))
    page_count = int(page_count_raw) if has_page_count else 0
    checksum = metadata.get("checksum")
    checksum_value = checksum if isinstance(checksum, str) and checksum else doc_id
    return DocumentPayload(
        document_id=doc_id,
        source_name=source_name,
        page_count=page_count,
        checksum=checksum_value,
        content=content,
        detected=detected,
    )


def _normalize_document_id(document_id: str) -> str:
    if not isinstance(document_id, str) or not document_id.strip():
        raise Namel3ssError(_document_id_message())
    return document_id.strip()


def _resolve_metadata(ctx, document_id: str) -> dict:
    uploads = list_uploads(ctx)
    for entry in uploads:
        if entry.get("checksum") == document_id:
            return entry
    raise Namel3ssError(_missing_document_message(document_id))


def _read_upload_bytes(ctx, metadata: dict) -> bytes:
    stored_path = metadata.get("stored_path")
    if not isinstance(stored_path, str) or not stored_path:
        raise Namel3ssError(_stored_path_message())
    store = LocalStore(getattr(ctx, "project_root", None), getattr(ctx, "app_path", None))
    base = store.uploads_root.parent.parent
    target = _resolve_stored_path(base, stored_path)
    try:
        return target.read_bytes()
    except OSError:
        raise Namel3ssError(_missing_file_message()) from None


def _resolve_stored_path(root: Path, stored_path: str) -> Path:
    posix = PurePosixPath(stored_path)
    if posix.is_absolute() or ".." in posix.parts:
        raise Namel3ssError(_stored_path_message())
    target = root / Path(*posix.parts)
    root_resolved = root.resolve(strict=False)
    target_resolved = target.resolve(strict=False)
    if not str(target_resolved).startswith(str(root_resolved)):
        raise Namel3ssError(_stored_path_message())
    return target


def _source_name_from_metadata(metadata: dict) -> str:
    name = metadata.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "upload"


def _validate_pdf_pages(pages: list[str], expected: int, source_name: str) -> list[str]:
    if not pages:
        pages = [""]
    if len(pages) != expected:
        raise Namel3ssError(_pdf_page_mismatch_message(source_name, expected, len(pages)))
    return pages


def _page_text_from_pdf(
    ctx,
    payload: DocumentPayload,
    page_value: int,
    *,
    secret_values: list[str] | None,
) -> str:
    pages, _ = extract_pages(payload.content, detected=payload.detected, mode="layout")
    pages = _validate_pdf_pages(pages, payload.page_count, payload.source_name)
    page_text = pages[page_value - 1] if pages else ""
    resolved_secrets = secret_values if secret_values is not None else _resolve_secret_values(ctx)
    return sanitize_text(
        page_text,
        project_root=getattr(ctx, "project_root", None),
        app_path=getattr(ctx, "app_path", None),
        secret_values=resolved_secrets,
    )


def _page_text_from_state(state: dict, payload: DocumentPayload, page_value: int) -> str:
    if not isinstance(state, dict):
        raise Namel3ssError(_page_text_missing_message(payload.source_name))
    ingestion = state.get("ingestion")
    if not isinstance(ingestion, dict):
        raise Namel3ssError(_page_text_missing_message(payload.source_name))
    report = ingestion.get(payload.document_id)
    if not isinstance(report, dict):
        raise Namel3ssError(_page_text_missing_message(payload.source_name))
    page_text = report.get("page_text")
    if not isinstance(page_text, list):
        raise Namel3ssError(_page_text_shape_message(payload.source_name))
    if len(page_text) != payload.page_count:
        raise Namel3ssError(_page_text_count_message(payload.source_name, payload.page_count, len(page_text)))
    if page_value - 1 >= len(page_text):
        raise Namel3ssError(_page_text_count_message(payload.source_name, payload.page_count, len(page_text)))
    text = page_text[page_value - 1]
    if not isinstance(text, str):
        raise Namel3ssError(_page_text_shape_message(payload.source_name))
    return text


def _require_uploads_capability(ctx) -> None:
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if "uploads" in allowed:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Document previews require access to stored uploads.",
            fix="Add 'uploads' to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


def _require_review_policy(ctx, *, identity: dict | None, policy_decl: object | None) -> None:
    policy = load_ingestion_policy(
        getattr(ctx, "project_root", None),
        getattr(ctx, "app_path", None),
        policy_decl=policy_decl,
    )
    decision = evaluate_ingestion_policy(policy, ACTION_INGESTION_REVIEW, identity)
    if not decision.allowed:
        raise policy_error(ACTION_INGESTION_REVIEW, decision)


def _resolve_secret_values(ctx) -> list[str]:
    try:
        config = load_config(app_path=getattr(ctx, "app_path", None), root=getattr(ctx, "project_root", None))
    except Exception:
        config = None
    return collect_secret_values(config)


def _coerce_page_number(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _document_id_message() -> str:
    return build_guidance_message(
        what="Document id is required.",
        why="Document preview requires a specific document identifier.",
        fix="Use the document_id from ingestion provenance.",
        example="/api/documents/<checksum>/pages/1",
    )


def _missing_document_message(document_id: str) -> str:
    return build_guidance_message(
        what=f"Document '{document_id}' was not found.",
        why="The document id must match a stored upload checksum.",
        fix="Re-upload the file or use a valid document id.",
        example="/api/documents/<checksum>/pdf",
    )


def _stored_path_message() -> str:
    return build_guidance_message(
        what="Document storage path is missing.",
        why="Document preview needs the stored upload path.",
        fix="Re-upload the file and retry.",
        example="POST /api/upload",
    )


def _missing_root_message() -> str:
    return build_guidance_message(
        what="Document storage root could not be resolved.",
        why="Document preview needs access to the runtime upload store.",
        fix="Ensure the runtime persistence root is available.",
        example="n3 run app.ai",
    )


def _missing_file_message() -> str:
    return build_guidance_message(
        what="Document bytes were not found.",
        why="The upload store entry exists but the file is missing.",
        fix="Re-upload the file and retry.",
        example="POST /api/upload",
    )


def _pdf_only_message(source_name: str) -> str:
    return build_guidance_message(
        what=f'"{source_name}" is not a PDF document.',
        why="Source preview is only supported for PDF uploads.",
        fix="Upload a PDF document to enable page previews.",
        example="POST /api/upload",
    )


def _pdf_page_count_message(source_name: str) -> str:
    return build_guidance_message(
        what=f'PDF "{source_name}" is missing page metadata.',
        why="Page previews require deterministic page numbers.",
        fix="Provide a valid PDF with readable page objects.",
        example="/api/documents/<checksum>/pages/1",
    )


def _pdf_page_mismatch_message(source_name: str, expected: int, found: int) -> str:
    return build_guidance_message(
        what=f'Page preview for "{source_name}" expected {expected} pages but found {found}.',
        why="Page previews require deterministic page numbers.",
        fix="Provide a PDF with readable page structure.",
        example="/api/documents/<checksum>/pages/1",
    )


def _page_number_message(value: object) -> str:
    return build_guidance_message(
        what=f"Page number '{value}' is invalid.",
        why="Page previews require a positive integer page number.",
        fix="Provide a page number like 1.",
        example="/api/documents/<checksum>/pages/1",
    )


def _page_range_message(page_number: int, page_count: int) -> str:
    return build_guidance_message(
        what=f"Page {page_number} is out of range.",
        why=f"Document has {page_count} pages.",
        fix=f"Choose a page between 1 and {page_count}.",
        example="/api/documents/<checksum>/pages/1",
    )


def _page_text_missing_message(source_name: str) -> str:
    return build_guidance_message(
        what=f'Page text for "{source_name}" is unavailable.',
        why="Highlight anchors require stored page text from ingestion.",
        fix="Re-run ingestion to rebuild page text and highlights.",
        example='{"upload_id":"<checksum>"}',
    )


def _page_text_shape_message(source_name: str) -> str:
    return build_guidance_message(
        what=f'Page text for "{source_name}" is invalid.',
        why="Stored page text must be a list of pages.",
        fix="Re-run ingestion to rebuild page text and highlights.",
        example='{"upload_id":"<checksum>"}',
    )


def _page_text_count_message(source_name: str, expected: int, found: int) -> str:
    return build_guidance_message(
        what=f'Page text for "{source_name}" expected {expected} pages but found {found}.',
        why="Highlight anchors require a page text entry for every page.",
        fix="Re-run ingestion to rebuild page text and highlights.",
        example='{"upload_id":"<checksum>"}',
    )


__all__ = ["handle_document_page", "handle_document_pdf"]
