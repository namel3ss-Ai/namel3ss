from __future__ import annotations

from copy import deepcopy

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.state.chat_shell import ensure_chat_shell_state
from namel3ss.runtime.ui.state.pdf_preview_state import ensure_pdf_preview_state, normalize_pdf_preview_state

THREAD_SNAPSHOTS_KEY = "thread_snapshots"


def ensure_thread_snapshot_state(state: dict) -> tuple[dict, dict[str, dict]]:
    chat = ensure_chat_shell_state(state)
    ensure_pdf_preview_state(chat)
    snapshots = _normalize_snapshots(chat.get(THREAD_SNAPSHOTS_KEY), selected_model_ids=chat.get("selected_model_ids"))
    active_thread_id = _normalized_text(chat.get("active_thread_id"))
    if active_thread_id is not None:
        snapshots = _with_snapshot(snapshots, active_thread_id, _capture_chat_snapshot(chat))
    chat[THREAD_SNAPSHOTS_KEY] = snapshots
    return chat, snapshots


def list_thread_summaries(state: dict) -> list[dict]:
    chat, snapshots = ensure_thread_snapshot_state(state)
    rows: list[dict] = []
    active_thread_id = str(chat.get("active_thread_id") or "")
    default_models = chat.get("selected_model_ids")
    for thread in list(chat.get("threads") or []):
        if not isinstance(thread, dict):
            continue
        thread_id = _normalized_text(thread.get("id"))
        if thread_id is None:
            continue
        thread_name = _normalized_text(thread.get("name")) or thread_id
        snapshot = snapshots.get(thread_id)
        if snapshot is None:
            snapshot = _empty_snapshot(selected_model_ids=default_models)
        nodes = list(((snapshot.get("messages_graph") or {}).get("nodes") or []))
        last_message_id = ""
        if nodes and isinstance(nodes[-1], dict):
            last_message_id = _normalized_text(nodes[-1].get("id")) or ""
        rows.append(
            {
                "active": thread_id == active_thread_id,
                "id": thread_id,
                "last_message_id": last_message_id,
                "message_count": len(nodes),
                "name": thread_name,
            }
        )
    return rows


def load_thread_snapshot(
    state: dict,
    *,
    thread_id: str,
    activate: bool,
) -> tuple[dict, dict]:
    thread_text = _require_thread_id(thread_id)
    chat, snapshots = ensure_thread_snapshot_state(state)
    thread = _ensure_thread(chat, thread_id=thread_text, preferred_name=None)
    current_active = _normalized_text(chat.get("active_thread_id"))
    if activate and current_active and current_active != thread_text:
        snapshots = _with_snapshot(snapshots, current_active, _capture_chat_snapshot(chat))
    snapshot = snapshots.get(thread_text)
    if snapshot is None:
        snapshot = _empty_snapshot(selected_model_ids=chat.get("selected_model_ids"))
        snapshots = _with_snapshot(snapshots, thread_text, snapshot)
    chat[THREAD_SNAPSHOTS_KEY] = snapshots
    if activate:
        _apply_snapshot(chat, thread_id=thread_text, snapshot=snapshot)
    return thread, deepcopy(snapshot)


def save_thread_snapshot(
    state: dict,
    *,
    thread_id: str,
    payload: dict,
    activate: bool,
) -> tuple[dict, dict]:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat thread save payload must be a JSON object.")
    thread_text = _require_thread_id(thread_id)
    chat, snapshots = ensure_thread_snapshot_state(state)
    thread_name = _payload_text(payload, "name", "thread_name", "title")
    thread = _ensure_thread(chat, thread_id=thread_text, preferred_name=thread_name)

    current_active = _normalized_text(chat.get("active_thread_id"))
    if activate and current_active and current_active != thread_text:
        snapshots = _with_snapshot(snapshots, current_active, _capture_chat_snapshot(chat))

    base_snapshot = snapshots.get(thread_text)
    if base_snapshot is None:
        base_snapshot = _empty_snapshot(selected_model_ids=chat.get("selected_model_ids"))

    merged_snapshot = {
        "composer_state": payload.get("composer_state", base_snapshot.get("composer_state")),
        "messages": payload.get("messages", base_snapshot.get("messages")),
        "messages_graph": payload.get("messages_graph", base_snapshot.get("messages_graph")),
        "pdf_preview_state": payload.get("pdf_preview_state", base_snapshot.get("pdf_preview_state")),
        "selected_model_ids": payload.get("selected_model_ids", base_snapshot.get("selected_model_ids")),
        "stream_state": payload.get("stream_state", base_snapshot.get("stream_state")),
    }
    normalized_snapshot = _normalize_snapshot(merged_snapshot, selected_model_ids=chat.get("selected_model_ids"))
    snapshots = _with_snapshot(snapshots, thread_text, normalized_snapshot)
    chat[THREAD_SNAPSHOTS_KEY] = snapshots

    if activate or current_active == thread_text:
        _apply_snapshot(chat, thread_id=thread_text, snapshot=normalized_snapshot)

    return thread, deepcopy(normalized_snapshot)


def _ensure_thread(chat: dict, *, thread_id: str, preferred_name: str | None) -> dict:
    rows = list(chat.get("threads") or [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = _normalized_text(row.get("id"))
        if row_id != thread_id:
            continue
        if preferred_name:
            row["name"] = preferred_name
        return row
    name = preferred_name or thread_id
    entry = {"id": thread_id, "name": name}
    rows.append(entry)
    chat["threads"] = rows
    return entry


def _capture_chat_snapshot(chat: dict) -> dict:
    payload = {
        "composer_state": deepcopy(chat.get("composer_state") or {}),
        "messages": deepcopy(chat.get("messages") or []),
        "messages_graph": deepcopy(chat.get("messages_graph") or {}),
        "pdf_preview_state": deepcopy(chat.get("pdf_preview_state") or {}),
        "selected_model_ids": list(chat.get("selected_model_ids") or []),
        "stream_state": deepcopy(chat.get("stream_state") or {}),
    }
    return _normalize_snapshot(payload, selected_model_ids=payload.get("selected_model_ids"))


def _apply_snapshot(chat: dict, *, thread_id: str, snapshot: dict) -> None:
    chat["active_thread_id"] = thread_id
    chat["active_thread"] = thread_id
    chat["messages"] = deepcopy(snapshot.get("messages") or [])
    chat["messages_graph"] = deepcopy(snapshot.get("messages_graph") or {"active_message_id": None, "edges": [], "nodes": []})
    chat["composer_state"] = deepcopy(snapshot.get("composer_state") or {"attachments": [], "draft": "", "tools": [], "web_search": False})
    chat["pdf_preview_state"] = normalize_pdf_preview_state(snapshot.get("pdf_preview_state"))
    selected_model_ids = list(snapshot.get("selected_model_ids") or [])
    chat["selected_model_ids"] = selected_model_ids
    chat["active_models"] = list(selected_model_ids)
    chat["stream_state"] = deepcopy(snapshot.get("stream_state") or {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []})


def _normalize_snapshots(value: object, *, selected_model_ids: object) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        thread_id = _normalized_text(key)
        if thread_id is None:
            continue
        normalized[thread_id] = _normalize_snapshot(value.get(key), selected_model_ids=selected_model_ids)
    return normalized


def _normalize_snapshot(value: object, *, selected_model_ids: object) -> dict:
    payload = value if isinstance(value, dict) else {}
    temp_state = {
        "chat": {
            "composer_state": deepcopy(payload.get("composer_state")),
            "messages": deepcopy(payload.get("messages")),
            "messages_graph": deepcopy(payload.get("messages_graph")),
            "selected_model_ids": deepcopy(payload.get("selected_model_ids", selected_model_ids)),
            "stream_state": deepcopy(payload.get("stream_state")),
        }
    }
    normalized_chat = ensure_chat_shell_state(temp_state)
    return {
        "composer_state": deepcopy(normalized_chat.get("composer_state") or {}),
        "messages": deepcopy(normalized_chat.get("messages") or []),
        "messages_graph": deepcopy(normalized_chat.get("messages_graph") or {"active_message_id": None, "edges": [], "nodes": []}),
        "pdf_preview_state": normalize_pdf_preview_state(payload.get("pdf_preview_state")),
        "selected_model_ids": list(normalized_chat.get("selected_model_ids") or []),
        "stream_state": deepcopy(normalized_chat.get("stream_state") or {}),
    }


def _empty_snapshot(*, selected_model_ids: object) -> dict:
    return _normalize_snapshot({}, selected_model_ids=selected_model_ids)


def _with_snapshot(snapshots: dict[str, dict], thread_id: str, snapshot: dict) -> dict[str, dict]:
    updated = dict(snapshots)
    updated[thread_id] = deepcopy(snapshot)
    return {key: updated[key] for key in sorted(updated.keys())}


def _require_thread_id(value: object) -> str:
    thread_id = _normalized_text(value)
    if thread_id is None:
        raise Namel3ssError("Chat thread id must be text.")
    return thread_id


def _payload_text(payload: dict, *keys: str) -> str | None:
    for key in keys:
        value = _normalized_text(payload.get(key))
        if value is not None:
            return value
    return None


def _normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


__all__ = [
    "THREAD_SNAPSHOTS_KEY",
    "ensure_thread_snapshot_state",
    "list_thread_summaries",
    "load_thread_snapshot",
    "save_thread_snapshot",
]
