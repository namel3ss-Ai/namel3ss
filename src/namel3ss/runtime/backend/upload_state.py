from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.backend.upload_contract import UPLOAD_STATES


def upload_state_entry(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise Namel3ssError(_metadata_type_message())
    name = _require_text(metadata, "name", _missing_metadata_message("name"))
    content_type = _require_text(metadata, "content_type", _missing_metadata_message("content_type"))
    size = _require_int(metadata, "bytes", _missing_metadata_message("bytes"))
    checksum = _require_text(metadata, "checksum", _missing_metadata_message("checksum"))
    entry = {
        "id": checksum,
        "name": name,
        "size": size,
        "type": content_type,
        "checksum": checksum,
    }
    preview = _preview_entry(metadata.get("preview"))
    if preview:
        entry["preview"] = preview
    progress = _progress_entry(metadata.get("progress"))
    if progress:
        entry["progress"] = progress
    state = _state_entry(metadata.get("state"))
    if state:
        entry["state"] = state
    error = _error_entry(metadata.get("error"))
    if error:
        entry["error"] = error
    return entry


def apply_upload_selection(state: dict, *, upload_name: str, entry: dict, multiple: bool) -> None:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    if not isinstance(upload_name, str) or not upload_name.strip():
        raise Namel3ssError(_upload_name_message())
    if not isinstance(entry, dict):
        raise Namel3ssError(_entry_type_message())
    uploads = state.get("uploads")
    if uploads is None:
        uploads = {}
    if not isinstance(uploads, dict):
        raise Namel3ssError(_uploads_shape_message())
    state["uploads"] = uploads
    existing = _normalize_upload_bucket(uploads.get(upload_name), upload_name)
    entry_id = _entry_id(entry)
    if multiple:
        next_bucket = dict(existing)
        next_bucket[entry_id] = entry
        uploads[upload_name] = next_bucket
    else:
        uploads[upload_name] = {entry_id: entry}


def clear_upload_selection(state: dict, *, upload_name: str, upload_id: str | None = None) -> None:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    if not isinstance(upload_name, str) or not upload_name.strip():
        raise Namel3ssError(_upload_name_message())
    uploads = state.get("uploads")
    if uploads is None:
        uploads = {}
    if not isinstance(uploads, dict):
        raise Namel3ssError(_uploads_shape_message())
    state["uploads"] = uploads
    current = _normalize_upload_bucket(uploads.get(upload_name), upload_name)
    if upload_id is None:
        uploads[upload_name] = {}
        return
    if not isinstance(upload_id, str) or not upload_id.strip():
        raise Namel3ssError(_upload_id_message())
    next_bucket = dict(current)
    next_bucket.pop(upload_id, None)
    uploads[upload_name] = next_bucket


def normalized_upload_entries(state: dict, *, upload_name: str) -> dict[str, dict]:
    if not isinstance(state, dict):
        raise Namel3ssError(_state_type_message())
    uploads = state.get("uploads")
    if uploads is None:
        return {}
    if not isinstance(uploads, dict):
        raise Namel3ssError(_uploads_shape_message())
    return _normalize_upload_bucket(uploads.get(upload_name), upload_name)


def _normalize_upload_bucket(value: object, upload_name: str) -> dict[str, dict]:
    if value is None:
        return {}
    if isinstance(value, dict):
        if _looks_like_upload_entry(value):
            entry_id = _entry_id(value)
            return {entry_id: value}
        bucket: dict[str, dict] = {}
        for key, entry in value.items():
            if not isinstance(entry, dict):
                raise Namel3ssError(_upload_bucket_message(upload_name))
            entry_id = _entry_id(entry, fallback_key=key)
            bucket[entry_id] = entry
        return bucket
    if isinstance(value, list):
        bucket: dict[str, dict] = {}
        for entry in value:
            if not isinstance(entry, dict):
                raise Namel3ssError(_upload_bucket_message(upload_name))
            entry_id = _entry_id(entry)
            bucket[entry_id] = entry
        return bucket
    raise Namel3ssError(_upload_bucket_message(upload_name))


def _entry_id(entry: dict, *, fallback_key: object | None = None) -> str:
    value = entry.get("id")
    if not isinstance(value, str) or not value.strip():
        value = entry.get("checksum")
    if not isinstance(value, str) or not value.strip():
        if isinstance(fallback_key, str) and fallback_key.strip():
            value = fallback_key.strip()
        else:
            raise Namel3ssError(_entry_id_message())
    return value.strip()


def _looks_like_upload_entry(value: dict) -> bool:
    identifier = value.get("id") if isinstance(value.get("id"), str) and value.get("id") else value.get("checksum")
    name = value.get("name")
    return isinstance(name, str) and bool(name.strip()) and isinstance(identifier, str) and bool(identifier.strip())


def _require_text(metadata: dict, key: str, message: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(message)
    return value.strip()


def _require_int(metadata: dict, key: str, message: str) -> int:
    value = metadata.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise Namel3ssError(message)
    return value


def _preview_entry(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    filename = _text_or_none(value.get("filename"))
    content_type = _text_or_none(value.get("content_type"))
    size = _int_or_none(value.get("size"))
    checksum = _text_or_none(value.get("checksum"))
    if not filename or not content_type or size is None or checksum is None:
        return None
    entry: dict[str, object] = {
        "filename": filename,
        "content_type": content_type,
        "size": size,
        "checksum": checksum,
    }
    page_count = _int_or_none(value.get("page_count"))
    if page_count is not None:
        entry["page_count"] = page_count
    item_count = _int_or_none(value.get("item_count"))
    if item_count is not None:
        entry["item_count"] = item_count
    return entry


def _progress_entry(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    bytes_received = _int_or_none(value.get("bytes_received"))
    if bytes_received is None:
        return None
    total_bytes = _int_or_none(value.get("total_bytes"))
    percent_complete = value.get("percent_complete")
    if not isinstance(percent_complete, int) or isinstance(percent_complete, bool) or not (0 <= percent_complete <= 100):
        percent_complete = None
    return {
        "bytes_received": bytes_received,
        "total_bytes": total_bytes,
        "percent_complete": percent_complete,
    }


def _state_entry(value: object) -> str | None:
    if isinstance(value, str) and value in UPLOAD_STATES:
        return value
    return None


def _error_entry(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    code = _text_or_none(value.get("code"))
    reason = _text_or_none(value.get("reason"))
    if not code or not reason:
        return None
    entry: dict[str, object] = {"code": code, "reason": reason}
    message = _text_or_none(value.get("message"))
    if message:
        entry["message"] = message
    remediation = _text_or_none(value.get("remediation"))
    if remediation:
        entry["remediation"] = remediation
    actions = value.get("recovery_actions")
    if isinstance(actions, list):
        cleaned = [action for action in actions if isinstance(action, str) and action]
        if cleaned:
            entry["recovery_actions"] = cleaned
    return entry


def _int_or_none(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _text_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _metadata_type_message() -> str:
    return build_guidance_message(
        what="Upload metadata must be an object.",
        why="Upload selection expects the metadata returned by /api/upload.",
        fix="Send the upload metadata object.",
        example='{"name":"report.pdf","content_type":"application/pdf","bytes":12,"checksum":"..."}',
    )


def _missing_metadata_message(field_name: str) -> str:
    return build_guidance_message(
        what=f"Upload metadata is missing '{field_name}'.",
        why="Upload selection needs deterministic metadata to populate state.",
        fix=f"Include '{field_name}' from the /api/upload response.",
        example='{"name":"report.pdf","content_type":"application/pdf","bytes":12,"checksum":"..."}',
    )


def _state_type_message() -> str:
    return build_guidance_message(
        what="State must be an object.",
        why="Upload selection writes metadata into state.uploads.",
        fix="Ensure state is a JSON object.",
        example='{"uploads":{}}',
    )


def _upload_name_message() -> str:
    return build_guidance_message(
        what="Upload selection is missing a target name.",
        why="Upload actions map metadata to a named upload request.",
        fix="Use the upload name declared in the UI.",
        example='upload receipt',
    )


def _entry_type_message() -> str:
    return build_guidance_message(
        what="Upload state entry must be an object.",
        why="Upload selection writes structured metadata into state.",
        fix="Ensure upload metadata is a dictionary.",
        example='{"id":"...","name":"file.txt","size":12,"type":"text/plain","checksum":"..."}',
    )


def _uploads_shape_message() -> str:
    return build_guidance_message(
        what="state.uploads must be an object.",
        why="Uploads are stored by name under state.uploads.",
        fix="Ensure state.uploads is a map of upload names to upload metadata maps.",
        example='{"uploads":{"receipt":{}}}',
    )


def _upload_bucket_message(upload_name: str) -> str:
    return build_guidance_message(
        what=f"state.uploads.{upload_name} must be an object, list, or upload metadata entry.",
        why="Upload state is normalized to a deterministic map keyed by file id.",
        fix="Use an object keyed by upload id or provide a list of upload metadata entries.",
        example=f'{{"uploads":{{"{upload_name}":{{}}}}}}',
    )


def _upload_id_message() -> str:
    return build_guidance_message(
        what="Upload removal requires a valid upload id.",
        why="Remove operations target a specific selected upload by id.",
        fix="Pass the upload id returned in state.uploads.<name>.",
        example='{"upload_id":"<checksum>"}',
    )


def _entry_id_message() -> str:
    return build_guidance_message(
        what="Upload entry is missing id/checksum.",
        why="Upload state maps entries by deterministic file ids.",
        fix="Include id or checksum in upload metadata entries.",
        example='{"id":"<checksum>","name":"file.txt","size":12,"type":"text/plain","checksum":"<checksum>"}',
    )


__all__ = ["apply_upload_selection", "clear_upload_selection", "normalized_upload_entries", "upload_state_entry"]
