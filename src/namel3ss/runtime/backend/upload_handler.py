from __future__ import annotations

import io
from typing import Iterable

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.observability.context import ObservabilityContext
from namel3ss.runtime.backend.studio_effect_adapter_uploads import (
    record_upload_received,
    record_upload_stored,
)
from namel3ss.runtime.backend.upload_store import list_uploads, store_upload


def handle_upload(
    ctx,
    *,
    headers: dict[str, str],
    rfile,
    content_length: int | None,
    upload_name: str | None,
) -> dict:
    _require_uploads_capability(ctx)
    obs, owns_obs = _resolve_observability(ctx)
    span_id = None
    span_status = "ok"
    normalized = {key.lower(): value for key, value in headers.items()}
    content_type = normalized.get("content-type", "").strip()
    is_chunked = "chunked" in normalized.get("transfer-encoding", "").lower()
    if obs and owns_obs:
        obs.start_session()
    try:
        if content_type.startswith("multipart/form-data"):
            boundary = _multipart_boundary(content_type)
            body = _read_body(rfile, content_length, is_chunked=is_chunked)
            filename, part_type, data = _parse_multipart(body, boundary)
            name = filename or upload_name or "upload"
            if obs and span_id is None:
                span_id = obs.start_span(
                    None,
                    name=f"upload:{name}",
                    kind="upload",
                    details={"name": name},
                    timing_name="upload",
                    timing_labels={"name": name},
                )
            stream = io.BytesIO(data)
            metadata = store_upload(
                ctx,
                filename=name,
                content_type=part_type,
                stream=stream,
            )
        else:
            name = upload_name or _header_filename(normalized) or "upload"
            if obs and span_id is None:
                span_id = obs.start_span(
                    None,
                    name=f"upload:{name}",
                    kind="upload",
                    details={"name": name},
                    timing_name="upload",
                    timing_labels={"name": name},
                )
            stream = _iter_body(rfile, content_length, is_chunked=is_chunked)
            metadata = store_upload(
                ctx,
                filename=name,
                content_type=content_type,
                stream=stream,
            )
    except Exception:
        span_status = "error"
        raise
    finally:
        if span_id:
            obs.end_span(None, span_id, status=span_status)
        if obs and owns_obs:
            obs.flush()
    traces: list[dict] = []
    record_upload_received(
        traces,
        name=metadata["name"],
        content_type=metadata["content_type"],
        bytes_len=metadata["bytes"],
        checksum=metadata["checksum"],
    )
    record_upload_stored(traces, name=metadata["name"], stored_path=metadata["stored_path"])
    return {"ok": True, "upload": metadata, "traces": traces}


def handle_upload_list(ctx) -> dict:
    _require_uploads_capability(ctx)
    uploads = list_uploads(ctx)
    return {"ok": True, "uploads": uploads}


def _resolve_observability(ctx) -> tuple[ObservabilityContext | None, bool]:
    obs = getattr(ctx, "observability", None)
    if obs is not None:
        return obs, False
    app_path = getattr(ctx, "app_path", None)
    project_root = getattr(ctx, "project_root", None)
    config = None
    try:
        config = load_config(app_path=app_path, root=project_root)
    except Exception:
        config = None
    obs = ObservabilityContext.from_config(
        project_root=project_root,
        app_path=app_path,
        config=config,
    )
    return obs, True


def _multipart_boundary(content_type: str) -> bytes:
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            value = part.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value.encode("utf-8")
    raise Namel3ssError(
        build_guidance_message(
            what="Multipart upload is missing a boundary.",
            why="Multipart data needs a boundary marker to separate parts.",
            fix="Send a multipart/form-data request with a boundary.",
            example="Content-Type: multipart/form-data; boundary=...",
        )
    )


def _read_body(rfile, content_length: int | None, *, is_chunked: bool) -> bytes:
    if is_chunked:
        chunks = list(_iter_chunked(rfile))
        return b"".join(chunks)
    if content_length is None:
        raise Namel3ssError("Upload is missing Content-Length.")
    if content_length <= 0:
        return b""
    return rfile.read(content_length)


def _iter_body(rfile, content_length: int | None, *, is_chunked: bool) -> Iterable[bytes]:
    if is_chunked:
        return _iter_chunked(rfile)
    if content_length is None:
        raise Namel3ssError("Upload is missing Content-Length.")
    return _iter_length(rfile, content_length)


def _iter_length(rfile, length: int) -> Iterable[bytes]:
    remaining = length
    while remaining > 0:
        chunk = rfile.read(min(8192, remaining))
        if not chunk:
            break
        remaining -= len(chunk)
        yield chunk


def _iter_chunked(rfile) -> Iterable[bytes]:
    while True:
        line = rfile.readline()
        if not line:
            break
        try:
            size_text = line.strip().split(b";", 1)[0]
            size = int(size_text, 16)
        except Exception as exc:
            raise Namel3ssError("Invalid chunked upload encoding.") from exc
        if size == 0:
            _consume_trailer(rfile)
            break
        chunk = rfile.read(size)
        rfile.read(2)
        if chunk:
            yield chunk


def _consume_trailer(rfile) -> None:
    while True:
        line = rfile.readline()
        if not line or line in {b"\r\n", b"\n"}:
            break


def _parse_multipart(body: bytes, boundary: bytes) -> tuple[str | None, str | None, bytes]:
    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    for part in parts:
        if not part:
            continue
        if part.startswith(b"--"):
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        header_blob, _, data = part.partition(b"\r\n\r\n")
        if not header_blob:
            continue
        headers = _parse_headers(header_blob.decode("utf-8", errors="replace"))
        disposition = headers.get("content-disposition", "")
        filename = _parse_filename(disposition)
        if filename is None:
            continue
        content_type = headers.get("content-type")
        return filename, content_type, data
    raise Namel3ssError("Multipart upload did not include a file.")


def _parse_headers(text: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in text.split("\r\n"):
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return headers


def _parse_filename(disposition: str) -> str | None:
    for part in disposition.split(";"):
        part = part.strip()
        if part.startswith("filename="):
            value = part.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value or None
    return None


def _header_filename(headers: dict[str, str]) -> str | None:
    disposition = headers.get("content-disposition", "")
    return _parse_filename(disposition)


def _require_uploads_capability(ctx) -> None:
    allowed = set(getattr(ctx, "capabilities", ()) or ())
    if "uploads" in allowed:
        return
    raise Namel3ssError(
        build_guidance_message(
            what="Uploads capability is not enabled.",
            why="Uploads are deny-by-default and must be explicitly allowed.",
            fix="Add 'uploads' to the capabilities block in app.ai.",
            example="capabilities:\n  uploads",
        )
    )


__all__ = ["handle_upload", "handle_upload_list"]
