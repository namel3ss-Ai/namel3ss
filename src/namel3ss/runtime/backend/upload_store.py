from __future__ import annotations

import hashlib
import io
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.persistence.local_store import LocalStore
from namel3ss.persistence.dataset_inference import infer_dataset_schema
from namel3ss.runtime.backend.upload_contract import (
    DEFAULT_CONTENT_TYPE,
    UPLOAD_ERROR_STREAM,
    UPLOAD_STATE_STORED,
    UploadPreviewCounter,
    build_progress,
    build_upload_preview,
    clean_upload_filename,
    upload_error_details,
)


def normalize_hash_bytes(data: bytes) -> bytes:
    if not data:
        return b""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _normalize_hash_chunk(data: bytes, *, pending_cr: bool) -> tuple[bytes, bool]:
    if pending_cr:
        data = b"\r" + data
        pending_cr = False
    if not data:
        return b"", False
    if data.endswith(b"\r"):
        pending_cr = True
        data = data[:-1]
    return normalize_hash_bytes(data), pending_cr


def store_upload(
    ctx,
    *,
    filename: str | None,
    content_type: str | None,
    stream: io.BufferedReader | list[bytes] | tuple[bytes, ...] | object,
    progress=None,
) -> dict:
    store = LocalStore(getattr(ctx, "project_root", None), getattr(ctx, "app_path", None))
    uploads_root = store.uploads_root
    uploads_root.mkdir(parents=True, exist_ok=True)
    original_name = clean_upload_filename(filename)
    temp_path = uploads_root / ".pending"
    preview_counter = UploadPreviewCounter.for_upload(filename=original_name, content_type=content_type)
    size, checksum = _write_stream(temp_path, stream, progress=progress, preview=preview_counter)
    final_path = store.upload_path_for(checksum)
    if temp_path != final_path:
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
        else:
            temp_path.replace(final_path)
    stored_path = f"uploads/{store.project_name}/{checksum}"
    metadata = {
        "upload_id": checksum,
        "name": original_name,
        "content_type": (content_type or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE,
        "type": (content_type or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE,
        "bytes": size,
        "size": size,
        "checksum": checksum,
        "stored_path": stored_path,
        "path": stored_path,
        "owner": "anonymous",
    }
    metadata["preview"] = build_upload_preview(metadata, preview_counter.snapshot())
    store.upsert_upload(metadata)
    _maybe_register_dataset(store, metadata)
    return metadata


def list_uploads(ctx) -> list[dict]:
    store = LocalStore(getattr(ctx, "project_root", None), getattr(ctx, "app_path", None))
    entries = store.load_uploads()
    normalized: list[dict] = []
    for entry in entries:
        item = dict(entry)
        preview = item.get("preview")
        if not isinstance(preview, dict):
            item["preview"] = build_upload_preview(item, {})
        if not isinstance(item.get("state"), str):
            item["state"] = UPLOAD_STATE_STORED
        if not isinstance(item.get("progress"), dict):
            size = item.get("bytes")
            progress_value = build_progress(size if isinstance(size, int) else 0, size if isinstance(size, int) else None)
            item["progress"] = progress_value
        if "upload_id" not in item and isinstance(item.get("checksum"), str):
            item["upload_id"] = item.get("checksum")
        if "path" not in item and isinstance(item.get("stored_path"), str):
            item["path"] = item.get("stored_path")
        normalized.append(item)
    normalized.sort(key=lambda item: (str(item.get("stored_path", "")), str(item.get("checksum", ""))))
    return normalized


def _write_stream(path: Path, stream: object, *, progress=None, preview: UploadPreviewCounter | None = None) -> tuple[int, str]:
    hasher = hashlib.sha256()
    size = 0
    pending_cr = False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        if hasattr(stream, "read"):
            reader = stream  # type: ignore[assignment]
            while True:
                chunk = reader.read(8192)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray)):
                    raise Namel3ssError(
                        "Upload stream returned non-bytes data.",
                        details=upload_error_details(UPLOAD_ERROR_STREAM),
                    )
                data = bytes(chunk)
                normalized, pending_cr = _normalize_hash_chunk(data, pending_cr=pending_cr)
                hasher.update(normalized)
                size += len(data)
                if progress is not None:
                    progress(len(data))
                if preview is not None:
                    preview.consume(data)
                handle.write(data)
        else:
            for chunk in stream if stream is not None else []:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise Namel3ssError(
                        "Upload stream returned non-bytes data.",
                        details=upload_error_details(UPLOAD_ERROR_STREAM),
                    )
                data = bytes(chunk)
                normalized, pending_cr = _normalize_hash_chunk(data, pending_cr=pending_cr)
                hasher.update(normalized)
                size += len(data)
                if progress is not None:
                    progress(len(data))
                if preview is not None:
                    preview.consume(data)
                handle.write(data)
    if pending_cr:
        hasher.update(b"\n")
    return size, hasher.hexdigest()


def _maybe_register_dataset(store: LocalStore, metadata: dict) -> None:
    upload_id = metadata.get("checksum")
    if not isinstance(upload_id, str) or not upload_id:
        return
    path = store.upload_path_for(upload_id)
    if not path.exists():
        return
    schema = infer_dataset_schema(
        filename=metadata.get("name"),
        content_type=metadata.get("content_type"),
        data=path.read_bytes(),
    )
    if not schema:
        return
    dataset = {
        "dataset_id": upload_id,
        "name": metadata.get("name") or upload_id,
        "schema": schema,
        "source": upload_id,
        "owner": "anonymous",
    }
    store.upsert_dataset(dataset)


__all__ = ["list_uploads", "normalize_hash_bytes", "store_upload"]
