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
from namel3ss.runtime.backend.upload_store import list_uploads
from namel3ss.runtime.persistence_paths import resolve_persistence_root
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
    payload = _load_document(ctx, document_id=document_id, identity=identity, policy_decl=policy_decl)
    filename = clean_upload_filename(payload.source_name)
    return payload.content, payload.info, filename


def handle_document_page(
    ctx,
    *,
    document_id: str,
    page_number: object,
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
    pages, _ = extract_pages(payload.content, detected=payload.detected, mode="layout")
    pages = _validate_pdf_pages(pages, payload.page_count, payload.source_name)
    page_text = pages[page_value - 1] if pages else ""
    resolved_secrets = secret_values if secret_values is not None else _resolve_secret_values(ctx)
    cleaned = sanitize_text(
        page_text,
        project_root=getattr(ctx, "project_root", None),
        app_path=getattr(ctx, "app_path", None),
        secret_values=resolved_secrets,
    )
    return {
        "ok": True,
        "document": payload.info,
        "page": {
            "number": page_value,
            "text": cleaned,
        },
        "pdf_url": f"/api/documents/{payload.document_id}/pdf#page={page_value}",
    }


def _load_document(
    ctx,
    *,
    document_id: str,
    identity: dict | None,
    policy_decl: object | None,
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
    page_count = detected.get("page_count")
    if not isinstance(page_count, int) or page_count <= 0:
        raise Namel3ssError(_pdf_page_count_message(source_name))
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
    root = resolve_persistence_root(getattr(ctx, "project_root", None), getattr(ctx, "app_path", None), allow_create=False)
    if root is None:
        raise Namel3ssError(_missing_root_message())
    base = root / ".namel3ss" / "files"
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


__all__ = ["handle_document_page", "handle_document_pdf"]
