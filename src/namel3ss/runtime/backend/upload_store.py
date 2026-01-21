from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.backend.file_store import _file_root, _scope_name
from namel3ss.utils.slugify import slugify_text


DEFAULT_CONTENT_TYPE = "application/octet-stream"


def store_upload(
    ctx,
    *,
    filename: str | None,
    content_type: str | None,
    stream: io.BufferedReader | list[bytes] | tuple[bytes, ...] | object,
) -> dict:
    uploads_root = _uploads_root(ctx)
    uploads_root.mkdir(parents=True, exist_ok=True)
    original_name = _clean_filename(filename)
    base, ext = _split_filename(original_name)
    safe_base = slugify_text(base) or "upload"
    temp_name = f".pending-{safe_base}{ext}"
    temp_path = uploads_root / temp_name
    size, checksum = _write_stream(temp_path, stream)
    final_name = f"{safe_base}-{checksum[:12]}{ext}"
    final_path = uploads_root / final_name
    if temp_path != final_path:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(final_path)
    scope = _scope_name(ctx.project_root, ctx.app_path)
    stored_path = f"{scope}/uploads/{final_name}"
    metadata = {
        "name": original_name,
        "content_type": (content_type or DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE,
        "bytes": size,
        "checksum": checksum,
        "stored_path": stored_path,
    }
    _update_index(uploads_root, metadata)
    return metadata


def list_uploads(ctx) -> list[dict]:
    uploads_root = _uploads_root(ctx)
    index_path = uploads_root / "index.json"
    if not index_path.exists():
        return []
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _uploads_root(ctx) -> Path:
    root = _file_root(ctx)
    return root / "uploads"


def _write_stream(path: Path, stream: object) -> tuple[int, str]:
    hasher = hashlib.sha256()
    size = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        if hasattr(stream, "read"):
            reader = stream  # type: ignore[assignment]
            while True:
                chunk = reader.read(8192)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray)):
                    raise Namel3ssError("Upload stream returned non-bytes data.")
                data = bytes(chunk)
                hasher.update(data)
                size += len(data)
                handle.write(data)
        else:
            for chunk in stream if stream is not None else []:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise Namel3ssError("Upload stream returned non-bytes data.")
                data = bytes(chunk)
                hasher.update(data)
                size += len(data)
                handle.write(data)
    return size, hasher.hexdigest()


def _split_filename(name: str) -> tuple[str, str]:
    path = Path(name)
    suffix = path.suffix.lower()
    if suffix and not _safe_suffix(suffix):
        suffix = ""
    return path.stem, suffix


def _safe_suffix(value: str) -> bool:
    if not value.startswith("."):
        return False
    for ch in value[1:]:
        if not (ch.isalnum() or ch == "."):
            return False
    return True


def _clean_filename(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "upload"
    normalized = raw.replace("\\", "/")
    name = normalized.split("/")[-1].strip()
    return name or "upload"


def _update_index(root: Path, entry: dict) -> None:
    index_path = root / "index.json"
    entries: list[dict] = []
    if index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            raw = []
        if isinstance(raw, list):
            entries = [item for item in raw if isinstance(item, dict)]
    entries = [item for item in entries if item.get("stored_path") != entry.get("stored_path")]
    entries.append(entry)
    entries.sort(key=lambda item: (str(item.get("stored_path", "")), str(item.get("checksum", ""))))
    index_path.write_text(canonical_json_dumps(entries, pretty=True), encoding="utf-8")


__all__ = ["list_uploads", "store_upload"]
