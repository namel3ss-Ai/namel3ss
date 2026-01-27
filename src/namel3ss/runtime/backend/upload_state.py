from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def upload_state_entry(metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise Namel3ssError(_metadata_type_message())
    name = _require_text(metadata, "name", _missing_metadata_message("name"))
    content_type = _require_text(metadata, "content_type", _missing_metadata_message("content_type"))
    size = _require_int(metadata, "bytes", _missing_metadata_message("bytes"))
    checksum = _require_text(metadata, "checksum", _missing_metadata_message("checksum"))
    return {
        "id": checksum,
        "name": name,
        "size": size,
        "type": content_type,
        "checksum": checksum,
    }


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
    existing = uploads.get(upload_name)
    if existing is None:
        existing = []
    if not isinstance(existing, list):
        raise Namel3ssError(_upload_list_message(upload_name))
    if multiple:
        uploads[upload_name] = list(existing) + [entry]
    else:
        uploads[upload_name] = [entry]


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
        fix="Ensure state.uploads is a map of upload names to lists.",
        example='{"uploads":{"receipt":[]}}',
    )


def _upload_list_message(upload_name: str) -> str:
    return build_guidance_message(
        what=f"state.uploads.{upload_name} must be a list.",
        why="Each upload name stores a list of metadata entries.",
        fix="Replace the value with a list of upload entries.",
        example=f'{{"uploads":{{"{upload_name}":[]}}}}',
    )


__all__ = ["apply_upload_selection", "upload_state_entry"]
