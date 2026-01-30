from __future__ import annotations

from types import SimpleNamespace

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.chunk import chunk_text
from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.extract import extract_fallback, extract_text
from namel3ss.ingestion.gate import gate_quality, should_fallback
from namel3ss.ingestion.normalize import normalize_text, preview_text, sanitize_text
from namel3ss.ingestion.signals import compute_signals
from namel3ss.ingestion.store import drop_index, store_report, update_index
from namel3ss.runtime.backend.upload_store import list_uploads
from pathlib import Path

from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.slugify import slugify_text


def run_ingestion(
    *,
    upload_id: str,
    mode: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None = None,
) -> dict:
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    upload_id = upload_id.strip()
    resolved_mode = _normalize_mode(mode)
    ctx = SimpleNamespace(project_root=project_root, app_path=app_path)
    metadata = _resolve_metadata(ctx, upload_id)
    content = _read_upload_bytes(ctx, metadata)
    detected = detect_upload(metadata, content=content)
    if resolved_mode in {"layout", "ocr"}:
        text, method_used = extract_text(content, detected=detected, mode=resolved_mode)
        primary_signals = compute_signals(normalize_text(text), detected=detected)
    else:
        text, method_used = extract_text(content, detected=detected, mode="primary")
        normalized_primary = normalize_text(text)
        primary_signals = compute_signals(normalized_primary, detected=detected)
        if should_fallback(primary_signals, detected):
            text, method_used = extract_fallback(content, detected=detected)
    normalized = normalize_text(text)
    signals = compute_signals(normalized, detected=detected)
    status, reasons = gate_quality(signals)
    sanitized = sanitize_text(
        normalized,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    report = {
        "upload_id": upload_id,
        "status": status,
        "method_used": method_used,
        "detected": detected,
        "signals": signals,
        "preview": preview_text(
            sanitized,
            project_root=project_root,
            app_path=app_path,
            secret_values=secret_values,
        ),
        "reasons": list(reasons),
    }
    store_report(state, upload_id=upload_id, report=report)
    if status == "block":
        drop_index(state, upload_id=upload_id)
        chunks: list[dict] = []
    else:
        chunks = chunk_text(sanitized)
        update_index(state, upload_id=upload_id, chunks=chunks, low_quality=status == "warn")
    return {
        "report": report,
        "status": status,
        "chunks": chunks,
        "detected": detected,
        "signals": signals,
    }


def _normalize_mode(mode: str | None) -> str:
    if mode is None:
        return "primary"
    value = str(mode).strip().lower()
    if value in {"primary", "layout", "ocr"}:
        return value
    raise Namel3ssError(_mode_message(value))


def _resolve_metadata(ctx, upload_id: str) -> dict:
    uploads = list_uploads(ctx)
    for entry in uploads:
        if entry.get("checksum") == upload_id:
            return entry
    raise Namel3ssError(_missing_upload_message(upload_id))


def _read_upload_bytes(ctx, metadata: dict) -> bytes:
    stored_path = metadata.get("stored_path")
    if not isinstance(stored_path, str) or not stored_path:
        raise Namel3ssError(_stored_path_message())
    filename = stored_path.split("/")[-1]
    root = resolve_persistence_root(ctx.project_root, ctx.app_path, allow_create=False)
    if root is None:
        raise Namel3ssError(_missing_root_message())
    scope = _scope_name(ctx.project_root, ctx.app_path)
    uploads_root = root / ".namel3ss" / "files" / scope / "uploads"
    target = uploads_root / filename
    try:
        return target.read_bytes()
    except OSError:
        raise Namel3ssError(_missing_file_message()) from None


def _upload_id_message() -> str:
    return build_guidance_message(
        what="Upload ingestion requires an upload_id.",
        why="Ingestion runs against a specific uploaded file.",
        fix="Provide the upload checksum from state.uploads.",
        example='{"upload_id":"<checksum>"}',
    )


def _mode_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported ingestion mode '{value}'.",
        why="Ingestion modes must be primary, layout, or ocr.",
        fix="Use primary, layout, or ocr.",
        example='{"mode":"primary"}',
    )


def _missing_upload_message(upload_id: str) -> str:
    return build_guidance_message(
        what=f"Upload '{upload_id}' was not found.",
        why="The upload id must match an existing upload checksum.",
        fix="Select a file first and use its checksum.",
        example='{"upload_id":"<checksum>"}',
    )


def _stored_path_message() -> str:
    return build_guidance_message(
        what="Upload metadata is missing stored_path.",
        why="Ingestion needs the stored upload path to read bytes.",
        fix="Re-upload the file or check the upload store index.",
        example='GET /api/uploads',
    )


def _missing_root_message() -> str:
    return build_guidance_message(
        what="Upload storage root could not be resolved.",
        why="Ingestion needs access to the runtime upload store.",
        fix="Ensure the runtime persistence root is available.",
        example="n3 run app.ai",
    )


def _missing_file_message() -> str:
    return build_guidance_message(
        what="Upload bytes were not found.",
        why="The upload store entry exists but the file is missing.",
        fix="Re-upload the file and retry ingestion.",
        example="POST /api/upload",
    )


def _scope_name(project_root: str | None, app_path: str | None) -> str:
    if app_path:
        path = Path(app_path)
        root = resolve_project_root(project_root, path)
        if root:
            try:
                rel = path.resolve().relative_to(root.resolve())
                return slugify_text(rel.as_posix())
            except Exception:
                pass
        return slugify_text(path.name)
    return "app"


__all__ = ["run_ingestion"]
