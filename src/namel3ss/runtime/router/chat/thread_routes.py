from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.conventions.errors import build_error_envelope
from namel3ss.runtime.router.chat.thread_state import (
    ensure_thread_snapshot_state,
    list_thread_summaries,
    load_thread_snapshot,
    save_thread_snapshot,
)
from namel3ss.runtime.router.request import read_json_body


@dataclass(frozen=True)
class ChatThreadRoutePayload:
    response: dict
    status: int
    yield_messages: list[dict]


def dispatch_chat_thread_route(
    *,
    method: str,
    path: str,
    query_values: dict[str, str],
    headers: dict[str, str],
    rfile,
    store,
    program,
) -> ChatThreadRoutePayload | None:
    segments = _segments(path)
    if segments[:3] != ("api", "chat", "threads"):
        return None
    if not _has_state_store(store):
        return _error_payload(program, "Chat thread routes require a stateful runtime store.", status=500)

    method_name = str(method or "").upper()
    if len(segments) == 3:
        if method_name != "GET":
            return _method_not_allowed(program, allowed=("GET",))
        state = _load_state(store)
        rows = list_thread_summaries(state)
        chat = (state.get("chat") or {}) if isinstance(state, dict) else {}
        response = {
            "chat": {
                "active_thread_id": str(chat.get("active_thread_id") or ""),
                "threads": rows,
            },
            "ok": True,
        }
        store.save_state(state)
        return ChatThreadRoutePayload(
            response=response,
            status=200,
            yield_messages=[_event("chat.thread.list", output={"thread_count": len(rows)})],
        )

    thread_id = _decode_thread_id(segments[3])
    if thread_id is None:
        return _error_payload(program, "Chat thread id is required.", status=400)

    tail = segments[4:]
    if method_name == "GET" and not tail:
        return _load_thread_route(program, store, thread_id=thread_id, query_values=query_values, activate_default=True)
    if method_name == "POST" and tail == ("load",):
        return _load_thread_route(program, store, thread_id=thread_id, query_values=query_values, activate_default=True)
    if method_name in {"POST", "PUT"} and (not tail or tail == ("save",)):
        payload = read_json_body(headers, rfile)
        return _save_thread_route(program, store, thread_id=thread_id, query_values=query_values, payload=payload)
    return _error_payload(program, "Chat thread route not found.", status=404)


def _load_thread_route(
    program,
    store,
    *,
    thread_id: str,
    query_values: dict[str, str],
    activate_default: bool,
) -> ChatThreadRoutePayload:
    state = _load_state(store)
    activate = _query_bool(query_values, "activate", default=activate_default)
    thread, snapshot = load_thread_snapshot(state, thread_id=thread_id, activate=activate)
    chat = ensure_thread_snapshot_state(state)[0]
    store.save_state(state)
    response = {
        "chat": {
            "active_thread_id": str(chat.get("active_thread_id") or ""),
            "composer_state": snapshot.get("composer_state") or {},
            "messages_graph": snapshot.get("messages_graph") or {"active_message_id": None, "edges": [], "nodes": []},
            "pdf_preview_state": snapshot.get("pdf_preview_state") or {},
            "selected_model_ids": list(snapshot.get("selected_model_ids") or []),
            "stream_state": snapshot.get("stream_state") or {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []},
        },
        "ok": True,
        "thread": {"id": thread.get("id"), "name": thread.get("name")},
    }
    node_count = len(list(((snapshot.get("messages_graph") or {}).get("nodes") or [])))
    return ChatThreadRoutePayload(
        response=response,
        status=200,
        yield_messages=[_event("chat.thread.load", output={"message_count": node_count, "thread_id": thread_id})],
    )


def _save_thread_route(
    program,
    store,
    *,
    thread_id: str,
    query_values: dict[str, str],
    payload: dict[str, object],
) -> ChatThreadRoutePayload:
    if not isinstance(payload, dict):
        raise Namel3ssError("Chat thread save payload must be a JSON object.")
    state = _load_state(store)
    activate = _query_bool(query_values, "activate", default=False)
    thread, snapshot = save_thread_snapshot(state, thread_id=thread_id, payload=payload, activate=activate)
    chat = ensure_thread_snapshot_state(state)[0]
    store.save_state(state)
    response = {
        "chat": {
            "active_thread_id": str(chat.get("active_thread_id") or ""),
            "composer_state": snapshot.get("composer_state") or {},
            "messages_graph": snapshot.get("messages_graph") or {"active_message_id": None, "edges": [], "nodes": []},
            "pdf_preview_state": snapshot.get("pdf_preview_state") or {},
            "selected_model_ids": list(snapshot.get("selected_model_ids") or []),
            "stream_state": snapshot.get("stream_state") or {"active_message_id": None, "cancel_requested": False, "phase": "idle", "tokens": []},
        },
        "ok": True,
        "thread": {"id": thread.get("id"), "name": thread.get("name")},
    }
    node_count = len(list(((snapshot.get("messages_graph") or {}).get("nodes") or [])))
    return ChatThreadRoutePayload(
        response=response,
        status=200,
        yield_messages=[_event("chat.thread.save", output={"message_count": node_count, "thread_id": thread_id})],
    )


def _error_payload(program, message: str, *, status: int) -> ChatThreadRoutePayload:
    error = Namel3ssError(message, details={"http_status": status, "category": "chat_router"})
    return ChatThreadRoutePayload(
        response=build_error_envelope(error=error, project_root=getattr(program, "project_root", None)),
        status=status,
        yield_messages=[],
    )


def _method_not_allowed(program, *, allowed: tuple[str, ...]) -> ChatThreadRoutePayload:
    message = f"Method is not allowed for chat thread route. Allowed methods: {', '.join(allowed)}"
    payload = _error_payload(program, message, status=405)
    response = dict(payload.response)
    response["allowed_methods"] = list(allowed)
    return ChatThreadRoutePayload(response=response, status=payload.status, yield_messages=payload.yield_messages)


def _event(event_type: str, *, output: dict) -> dict:
    return {
        "event_type": event_type,
        "flow_name": "chat.threads",
        "output": output,
        "sequence": 1,
        "stream_channel": "chat",
        "stream_id": "chat.threads",
    }


def _load_state(store) -> dict:
    value = store.load_state()
    if isinstance(value, dict):
        return value
    return {}


def _segments(path: str) -> tuple[str, ...]:
    return tuple(part for part in str(path or "").strip("/").split("/") if part)


def _decode_thread_id(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    decoded = unquote(value)
    text = decoded.strip()
    if not text:
        return None
    return text


def _query_bool(query_values: dict[str, str], key: str, *, default: bool) -> bool:
    raw = query_values.get(key)
    if raw is None:
        return default
    token = str(raw).strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _has_state_store(store) -> bool:
    return bool(store and hasattr(store, "load_state") and hasattr(store, "save_state"))


__all__ = ["ChatThreadRoutePayload", "dispatch_chat_thread_route"]
