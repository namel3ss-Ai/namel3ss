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


__all__ = ["record_upload_received", "record_upload_stored"]
