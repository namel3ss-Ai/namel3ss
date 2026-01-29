from __future__ import annotations


def record_upload_received(target: list, *, name: str, content_type: str, bytes_len: int, checksum: str) -> dict:
    event = {
        "type": "upload_received",
        "title": "Upload received",
        "name": name,
        "content_type": content_type,
        "bytes": bytes_len,
        "checksum": checksum,
    }
    target.append(event)
    return event


def record_upload_stored(target: list, *, name: str, stored_path: str) -> dict:
    event = {
        "type": "upload_stored",
        "title": "Upload stored",
        "name": name,
        "stored_path": stored_path,
    }
    target.append(event)
    return event


def record_upload_state(
    target: list,
    *,
    name: str | None,
    state: str,
    progress: dict | None = None,
    error: dict | None = None,
) -> dict:
    event = {
        "type": "upload_state",
        "title": "Upload state",
        "state": state,
    }
    if name:
        event["name"] = name
    if progress:
        event.update(progress)
    if error:
        event["error"] = dict(error)
    target.append(event)
    return event


def record_upload_progress(target: list, *, name: str | None, progress: dict) -> dict:
    event = {
        "type": "upload_progress",
        "title": "Upload progress",
    }
    if name:
        event["name"] = name
    event.update(progress)
    target.append(event)
    return event


def record_upload_preview(target: list, *, name: str | None, preview: dict) -> dict:
    event = {
        "type": "upload_preview",
        "title": "Upload preview",
    }
    if name:
        event["name"] = name
    event["preview"] = dict(preview)
    target.append(event)
    return event


def record_upload_error(target: list, *, name: str | None, error: dict) -> dict:
    event = {
        "type": "upload_error",
        "title": "Upload error",
    }
    if name:
        event["name"] = name
    event["error"] = dict(error)
    target.append(event)
    return event


__all__ = [
    "record_upload_error",
    "record_upload_preview",
    "record_upload_progress",
    "record_upload_received",
    "record_upload_state",
    "record_upload_stored",
]
