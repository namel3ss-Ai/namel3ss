from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from namel3ss.observability.context import ObservabilityContext


def run_ingestion(
    *,
    upload_id: str,
    mode: str | None,
    state: dict,
    project_root: str | None,
    app_path: str | None,
    secret_values: list[str] | None = None,
    observability: ObservabilityContext | None = None,
) -> dict:
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    upload_id = upload_id.strip()
    resolved_mode = _normalize_mode(mode)
    obs = observability
    span_id = None
    span_status = "ok"
    if obs:
        span_id = obs.start_span(
            None,
            name="ingestion:run",
            kind="ingestion",
            details={"upload_id": upload_id},
            timing_name="ingestion",
            timing_labels={"scope": "ingestion"},
        )
        obs.metrics.add("errors", value=0, labels={"scope": "ingestion"})
        obs.metrics.add("blocks", value=0, labels={"scope": "ingestion"})
        obs.metrics.add("retries", value=0, labels={"scope": "ingestion"})
    try:
        ctx = SimpleNamespace(project_root=project_root, app_path=app_path)
        metadata = _resolve_metadata(ctx, upload_id)
        accept_summary = {
            "upload_id": upload_id,
            "content_type": str(metadata.get("content_type") or ""),
            "size": int(metadata.get("size") or 0),
        }
        _record_stage(obs, span_id, "ingestion:accept", accept_summary)
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
        extract_summary = {
            "method_used": str(method_used or ""),
            "detected_type": str(detected.get("type") or ""),
            "text_chars": int(signals.get("text_chars") or 0),
        }
        _record_stage(obs, span_id, "ingestion:extract", extract_summary)
        status, reasons = gate_quality(signals)
        quality_summary = {"status": status, "reasons": list(reasons)}
        _record_stage(obs, span_id, "ingestion:quality_gate", quality_summary)
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
        chunk_chars = sum(int(chunk.get("chars") or 0) for chunk in chunks if isinstance(chunk, dict))
        chunk_summary = {"chunk_count": len(chunks), "chunk_chars": chunk_chars}
        _record_stage(obs, span_id, "ingestion:chunk", chunk_summary)
        index_summary = {
            "indexed_chunks": _count_index_entries(state, upload_id),
            "low_quality": status == "warn",
        }
        _record_stage(obs, span_id, "ingestion:index", index_summary)
        report_summary = {"report_status": status}
        _record_stage(obs, span_id, "ingestion:report", report_summary)
        if obs:
            outcome = "blocked" if status == "block" else "ok"
            obs.record_event(
                event_kind="run",
                scope="ingestion",
                outcome=outcome,
                identifiers={"upload_id": upload_id},
                payload={
                    "status": status,
                    "method": str(method_used or ""),
                    "detected_type": str(detected.get("type") or ""),
                    "chunk_count": len(chunks),
                },
            )
            obs.metrics.increment("requests", labels={"scope": "ingestion", "outcome": outcome})
            if outcome == "blocked":
                obs.metrics.increment("blocks", labels={"scope": "ingestion"})
        return {
            "report": report,
            "status": status,
            "chunks": chunks,
            "detected": detected,
            "signals": signals,
        }
    except Exception as err:
        span_status = "error"
        if obs:
            obs.record_event(
                event_kind="run",
                scope="ingestion",
                outcome="failed",
                identifiers={"upload_id": upload_id},
                payload={
                    "error_kind": err.__class__.__name__,
                    "error_category": _error_category(err),
                },
            )
            obs.metrics.increment("requests", labels={"scope": "ingestion", "outcome": "failed"})
            obs.metrics.increment("errors", labels={"scope": "ingestion"})
        raise
    finally:
        if obs and span_id:
            obs.end_span(None, span_id, status=span_status)


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


def _count_index_entries(state: dict, upload_id: str) -> int:
    index = state.get("index")
    if not isinstance(index, dict):
        return 0
    chunks = index.get("chunks")
    if not isinstance(chunks, list):
        return 0
    return sum(1 for entry in chunks if isinstance(entry, dict) and entry.get("upload_id") == upload_id)


def _record_stage(obs, parent_id: str | None, name: str, details: dict) -> None:
    if not obs:
        return
    span_id = obs.start_span(
        None,
        name=name,
        kind="ingestion_stage",
        details=details,
        parent_id=parent_id,
    )
    obs.end_span(None, span_id, status="ok")


def _error_category(err: Exception) -> str:
    if isinstance(err, Namel3ssError):
        details = err.details or {}
        category = str(details.get("category") or "").strip().lower()
        if category in {"input", "policy", "dependency", "internal"}:
            return category
        return "input"
    return "internal"


__all__ = ["run_ingestion"]
