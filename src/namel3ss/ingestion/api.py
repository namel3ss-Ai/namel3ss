from __future__ import annotations

from types import SimpleNamespace

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ingestion.detect import detect_upload
from namel3ss.ingestion.extract import extract_pages, extract_pages_fallback
from namel3ss.ingestion.gate import gate_quality, should_fallback
from namel3ss.ingestion.gate_probe import probe_content
from namel3ss.ingestion.normalize import normalize_text, preview_text, sanitize_text
from namel3ss.ingestion.quality_gate import evaluate_gate
from namel3ss.ingestion.progressive import (
    DEEP_SCAN_JOB_NAME,
    DEEP_SCAN_MAX_CHARS,
    DEEP_SCAN_OVERLAP,
    PHASE_DEEP,
    PHASE_QUICK,
    QUICK_SCAN_MAX_CHARS,
    QUICK_SCAN_OVERLAP,
    chunk_with_phase,
    deep_scan_job_handler,
    initial_phase_status,
    phase_summary,
    quick_progress_events,
)
from namel3ss.ingestion.signals import compute_signals
from namel3ss.ingestion.store import drop_index, store_report, update_index
from namel3ss.runtime.backend.job_queue import enqueue_system_job, register_system_job
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
    prepared = _prepare_ingestion(
        upload_id=upload_id,
        mode=mode,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    report = prepared.report
    store_report(state, upload_id=upload_id, report=report)
    if prepared.status == "block":
        drop_index(state, upload_id=upload_id)
        chunks: list[dict] = []
    else:
        chunks = chunk_with_phase(
            prepared.sanitized_pages,
            document_id=upload_id,
            source_name=prepared.source_name,
            phase=PHASE_DEEP,
            max_chars=DEEP_SCAN_MAX_CHARS,
            overlap=DEEP_SCAN_OVERLAP,
            include_highlights=True,
        )
        update_index(state, upload_id=upload_id, chunks=chunks, low_quality=prepared.status == "warn")
    return {
        "report": report,
        "status": prepared.status,
        "chunks": chunks,
        "detected": prepared.detected,
        "signals": prepared.signals,
    }


def run_ingestion_progressive(
    *,
    upload_id: str,
    mode: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None = None,
    job_ctx: object | None = None,
) -> dict:
    prepared = _prepare_ingestion(
        upload_id=upload_id,
        mode=mode,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    report = prepared.report
    report["phases"] = initial_phase_status(prepared.status)
    report["progress"] = list(quick_progress_events(upload_id, prepared.source_name, prepared.status))
    store_report(state, upload_id=upload_id, report=report)
    if prepared.status == "block":
        drop_index(state, upload_id=upload_id)
        report["phases"]["deep"] = {
            "status": "failed",
            "reason": "blocked",
        }
        store_report(state, upload_id=upload_id, report=report)
        chunks: list[dict] = []
        return {
            "report": report,
            "status": prepared.status,
            "chunks": chunks,
            "detected": prepared.detected,
            "signals": prepared.signals,
            "progress": list(report.get("progress") or []),
        }

    chunks = chunk_with_phase(
        prepared.sanitized_pages,
        document_id=upload_id,
        source_name=prepared.source_name,
        phase=PHASE_QUICK,
        max_chars=QUICK_SCAN_MAX_CHARS,
        overlap=QUICK_SCAN_OVERLAP,
        include_highlights=True,
    )
    update_index(state, upload_id=upload_id, chunks=chunks, low_quality=prepared.status == "warn")
    report["phases"]["quick"] = phase_summary("complete", chunks, result_status=prepared.status)
    store_report(state, upload_id=upload_id, report=report)
    if job_ctx is not None:
        enqueue_system_job(
            job_ctx,
            DEEP_SCAN_JOB_NAME,
            {"upload_id": upload_id, "mode": mode},
            line=None,
            column=None,
            reason="deep_scan",
        )
    return {
        "report": report,
        "status": prepared.status,
        "chunks": chunks,
        "detected": prepared.detected,
        "signals": prepared.signals,
        "progress": list(report.get("progress") or []),
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


def _join_pages(pages: list[str]) -> str:
    if not pages:
        return ""
    return "\f".join(pages)


def _source_name_from_metadata(metadata: dict) -> str:
    name = metadata.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "upload"


def _validate_page_provenance(*, pages: list[str], detected: dict, source_name: str) -> list[str]:
    kind = str(detected.get("type") or "")
    if kind != "pdf":
        return pages if pages else [""]
    page_count = detected.get("page_count")
    if not isinstance(page_count, int) or page_count <= 0:
        raise Namel3ssError(_pdf_page_count_message(source_name))
    if not pages:
        pages = [""]
    if len(pages) != page_count:
        raise Namel3ssError(_pdf_page_mismatch_message(source_name, page_count, len(pages)))
    return pages


def _pdf_page_count_message(source_name: str) -> str:
    return build_guidance_message(
        what=f'PDF "{source_name}" is missing page metadata.',
        why="Ingestion requires deterministic page numbers for every chunk.",
        fix="Provide a valid PDF with readable page objects.",
        example='{"upload_id":"<checksum>"}',
    )


def _pdf_page_mismatch_message(source_name: str, expected: int, found: int) -> str:
    return build_guidance_message(
        what=f'Page provenance for "{source_name}" expected {expected} pages but found {found}.',
        why="Ingestion requires deterministic page numbers for every chunk.",
        fix="Provide a PDF with readable page structure or convert it to text with form-feed page breaks.",
        example='{"upload_id":"<checksum>"}',
    )


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


def _prepare_ingestion(
    *,
    upload_id: str,
    mode: str | None,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None,
) -> SimpleNamespace:
    resolved_mode = _normalize_mode(mode)
    ctx = SimpleNamespace(project_root=project_root, app_path=app_path)
    metadata = _resolve_metadata(ctx, upload_id)
    content = _read_upload_bytes(ctx, metadata)
    detected = detect_upload(metadata, content=content)
    probe = probe_content(content, metadata=metadata, detected=detected)
    probe_blocked = probe.get("status") == "block"
    normalized: str | None = None
    method_used = "primary"
    pages: list[str] = []
    if not probe_blocked:
        if resolved_mode in {"layout", "ocr"}:
            pages, method_used = extract_pages(content, detected=detected, mode=resolved_mode)
            normalized = normalize_text(_join_pages(pages))
        else:
            pages, method_used = extract_pages(content, detected=detected, mode="primary")
            normalized_primary = normalize_text(_join_pages(pages))
            primary_signals = compute_signals(normalized_primary, detected=detected)
            if should_fallback(primary_signals, detected):
                pages, method_used = extract_pages_fallback(content, detected=detected)
            normalized = normalize_text(_join_pages(pages))
        pages = _validate_page_provenance(
            pages=pages,
            detected=detected,
            source_name=_source_name_from_metadata(metadata),
        )
    normalized_for_signals = normalized or ""
    signals = compute_signals(normalized_for_signals, detected=detected)
    status, reasons = gate_quality(signals)
    gate = evaluate_gate(
        content=content,
        metadata=metadata,
        detected=detected,
        normalized_text=normalized,
        quality_status=status,
        quality_reasons=reasons,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
        probe=probe,
    )
    if gate.get("status") == "blocked":
        status = "block"
    sanitized = sanitize_text(
        normalized_for_signals,
        project_root=project_root,
        app_path=app_path,
        secret_values=secret_values,
    )
    source_name = _source_name_from_metadata(metadata)
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
        "gate": gate,
        "provenance": {
            "document_id": upload_id,
            "source_name": source_name,
        },
    }
    sanitized_pages = sanitized.split("\f") if "\f" in sanitized else [sanitized]
    report["page_text"] = list(sanitized_pages)
    return SimpleNamespace(
        upload_id=upload_id,
        metadata=metadata,
        content=content,
        detected=detected,
        probe=probe,
        pages=pages,
        normalized=normalized,
        sanitized=sanitized,
        signals=signals,
        status=status,
        reasons=reasons,
        gate=gate,
        method_used=method_used,
        source_name=source_name,
        report=report,
        sanitized_pages=sanitized_pages,
        resolved_mode=resolved_mode,
    )


register_system_job(DEEP_SCAN_JOB_NAME, deep_scan_job_handler(_prepare_ingestion))


__all__ = ["run_ingestion", "run_ingestion_progressive"]
