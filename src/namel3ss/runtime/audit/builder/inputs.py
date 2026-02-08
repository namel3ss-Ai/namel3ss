from __future__ import annotations

from pathlib import Path

from namel3ss.utils.path_display import display_path_hint


def build_inputs(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    identity: dict,
    upload_id: str | None,
    query: str | None,
    state: dict,
) -> dict:
    payload: dict[str, object] = {}
    if app_path is not None:
        base = Path(project_root) if project_root else None
        payload["app"] = {"path": display_path_hint(app_path, base=base)}
    if identity:
        payload["identity"] = identity
    subject: dict[str, object] = {}
    if upload_id:
        subject["upload_id"] = upload_id
    if query is not None:
        subject["query"] = query
    if subject:
        payload["subject"] = subject
    payload["state"] = _state_summary(state)
    return payload


def _state_summary(state: dict) -> dict:
    uploads = state.get("uploads") if isinstance(state, dict) else None
    ingestion = state.get("ingestion") if isinstance(state, dict) else None
    index = state.get("index") if isinstance(state, dict) else None
    chunks = index.get("chunks") if isinstance(index, dict) else None
    return {
        "uploads": _count_upload_entries(uploads),
        "ingestion_reports": len(ingestion) if isinstance(ingestion, dict) else 0,
        "index_chunks": len(chunks) if isinstance(chunks, list) else 0,
    }


def _count_upload_entries(uploads: object) -> int:
    if not isinstance(uploads, dict):
        return 0
    total = 0
    for entry in uploads.values():
        if isinstance(entry, list):
            total += len(entry)
            continue
        if isinstance(entry, dict):
            if _looks_like_upload_entry(entry):
                total += 1
            else:
                total += sum(1 for value in entry.values() if isinstance(value, dict))
    return total


def _looks_like_upload_entry(entry: dict) -> bool:
    identifier = entry.get("id") if isinstance(entry.get("id"), str) and entry.get("id") else entry.get("checksum")
    name = entry.get("name")
    return isinstance(identifier, str) and bool(identifier) and isinstance(name, str) and bool(name)


__all__ = ["build_inputs"]
