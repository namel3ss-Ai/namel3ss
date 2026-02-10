from __future__ import annotations

from copy import deepcopy
from typing import Mapping


class DocumentLibraryError(RuntimeError):
    """Raised when document library state transitions are invalid."""


def normalize_document_library_state(state: Mapping[str, object] | None) -> dict[str, object]:
    source = dict(state or {})
    documents = _normalize_documents(source.get("documents"))
    selected_document_id = source.get("selected_document_id")
    return {
        "documents": documents,
        "selected_document_id": (
            str(selected_document_id)
            if isinstance(selected_document_id, str) and selected_document_id
            else None
        ),
    }


def select_document(library_state: Mapping[str, object] | None, document_id: str) -> dict[str, object]:
    state = normalize_document_library_state(library_state)
    target = document_id.strip()
    if not target:
        raise DocumentLibraryError("document_id is required.")
    ids = {entry["id"] for entry in state["documents"]}
    if target not in ids:
        raise DocumentLibraryError(f'Unknown document "{target}".')
    state["selected_document_id"] = target
    return state


def remove_document(library_state: Mapping[str, object] | None, document_id: str) -> dict[str, object]:
    state = normalize_document_library_state(library_state)
    target = document_id.strip()
    if not target:
        raise DocumentLibraryError("document_id is required.")
    next_documents = [entry for entry in state["documents"] if entry["id"] != target]
    if len(next_documents) == len(state["documents"]):
        raise DocumentLibraryError(f'Unknown document "{target}".')
    state["documents"] = next_documents
    if state["selected_document_id"] == target:
        state["selected_document_id"] = None
    return state


def upsert_document(
    library_state: Mapping[str, object] | None,
    *,
    document_id: str,
    name: str,
    status: str | None = None,
) -> dict[str, object]:
    state = normalize_document_library_state(library_state)
    entry_id = document_id.strip()
    if not entry_id:
        raise DocumentLibraryError("document_id is required.")
    entry_name = name.strip()
    if not entry_name:
        raise DocumentLibraryError("name is required.")
    next_status = _normalize_status(status)

    updated = False
    for entry in state["documents"]:
        if entry["id"] != entry_id:
            continue
        entry["name"] = entry_name
        entry["status"] = next_status
        updated = True
        break
    if not updated:
        state["documents"].append({"id": entry_id, "name": entry_name, "status": next_status})
        state["documents"] = _normalize_documents(state["documents"])
    return state


def build_document_library_payload(
    library_state: Mapping[str, object] | None,
    *,
    component_id: str,
    select_action_id: str | None = None,
    delete_action_id: str | None = None,
) -> dict[str, object]:
    state = normalize_document_library_state(library_state)
    return {
        "type": "component.document_library",
        "id": component_id,
        "documents": deepcopy(state["documents"]),
        "selected_document_id": state["selected_document_id"],
        "actions": {
            "select": select_action_id,
            "delete": delete_action_id,
        },
        "bindings": {
            "on_click": select_action_id,
            "keyboard_shortcut": None,
            "selected_item": None,
        },
    }


def _normalize_documents(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            continue
        document_id = str(entry.get("id") or f"document.{index}").strip()
        if not document_id:
            document_id = f"document.{index}"
        if document_id in seen_ids:
            raise DocumentLibraryError(f'Duplicate document id "{document_id}".')
        seen_ids.add(document_id)
        name = str(entry.get("name") or document_id)
        status = _normalize_status(entry.get("status"))
        normalized.append({"id": document_id, "name": name, "status": status})
    normalized.sort(key=lambda item: (item["name"].lower(), item["id"]))
    return normalized


def _normalize_status(raw: object) -> str:
    value = str(raw or "ready").strip().lower()
    if value in {"ready", "processing", "failed", "deleted"}:
        return value
    return "ready"


__all__ = [
    "DocumentLibraryError",
    "build_document_library_payload",
    "normalize_document_library_state",
    "remove_document",
    "select_document",
    "upsert_document",
]
