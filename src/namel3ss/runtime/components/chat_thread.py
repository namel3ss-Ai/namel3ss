from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


class ChatThreadError(RuntimeError):
    """Raised when chat thread state transitions are invalid."""


def normalize_chat_state(state: Mapping[str, object] | None) -> dict[str, object]:
    source = dict(state or {})
    messages = _normalize_messages(source.get("messages"))
    streaming = _normalize_streaming(source.get("streaming"))
    selected_citation = source.get("selected_citation")
    return {
        "messages": messages,
        "streaming": streaming,
        "selected_citation": str(selected_citation) if isinstance(selected_citation, str) and selected_citation else None,
    }


def apply_chat_event(
    chat_state: Mapping[str, object] | None,
    event: Mapping[str, object],
) -> dict[str, object]:
    state = normalize_chat_state(chat_state)
    event_type = str(event.get("type") or "")
    if event_type == "chat.message.add":
        return _apply_message_add(state, event)
    if event_type == "chat.stream.start":
        return _apply_stream_start(state, event)
    if event_type == "chat.stream.chunk":
        return _apply_stream_chunk(state, event)
    if event_type == "chat.stream.complete":
        return _apply_stream_complete(state, event)
    if event_type == "chat.citation.select":
        return _apply_citation_select(state, event)
    raise ChatThreadError(f"Unsupported chat event type '{event_type}'.")


def apply_chat_events(
    chat_state: Mapping[str, object] | None,
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    state = normalize_chat_state(chat_state)
    ordered_events = sorted(list(events), key=_event_sort_key)
    for event in ordered_events:
        state = apply_chat_event(state, event)
    return state


def build_chat_thread_payload(chat_state: Mapping[str, object] | None, *, component_id: str) -> dict[str, object]:
    state = normalize_chat_state(chat_state)
    return {
        "type": "component.chat_thread",
        "id": component_id,
        "messages": deepcopy(state["messages"]),
        "streaming": bool(state["streaming"]),
        "selected_citation": state["selected_citation"],
    }


def _apply_message_add(state: dict[str, object], event: Mapping[str, object]) -> dict[str, object]:
    next_state = normalize_chat_state(state)
    message_id = str(event.get("message_id") or "").strip() or _next_message_id(next_state["messages"])
    if _find_message(next_state["messages"], message_id) is not None:
        raise ChatThreadError(f'Message "{message_id}" already exists.')
    role = _normalize_role(event.get("role"))
    content = str(event.get("content") or "")
    citations = _normalize_citations(event.get("citations"))
    next_state["messages"].append(
        {
            "id": message_id,
            "role": role,
            "content": content,
            "citations": citations,
            "status": "complete",
            "error": None,
        }
    )
    return next_state


def _apply_stream_start(state: dict[str, object], event: Mapping[str, object]) -> dict[str, object]:
    next_state = normalize_chat_state(state)
    message_id = str(event.get("message_id") or "").strip()
    if not message_id:
        raise ChatThreadError("chat.stream.start requires message_id.")
    role = _normalize_role(event.get("role"))
    stream_map = next_state["streaming"]
    if message_id in stream_map:
        raise ChatThreadError(f'Stream already active for message "{message_id}".')
    stream_map[message_id] = {"role": role, "chunks": []}
    message = _find_message(next_state["messages"], message_id)
    if message is None:
        next_state["messages"].append(
            {
                "id": message_id,
                "role": role,
                "content": "",
                "citations": [],
                "status": "streaming",
                "error": None,
            }
        )
    else:
        message["status"] = "streaming"
        message["error"] = None
    return next_state


def _apply_stream_chunk(state: dict[str, object], event: Mapping[str, object]) -> dict[str, object]:
    next_state = normalize_chat_state(state)
    message_id = str(event.get("message_id") or "").strip()
    if not message_id:
        raise ChatThreadError("chat.stream.chunk requires message_id.")
    chunk = str(event.get("chunk") or "")
    if not chunk:
        return next_state
    stream_map = next_state["streaming"]
    stream = stream_map.get(message_id)
    if not isinstance(stream, dict):
        raise ChatThreadError(f'No active stream for message "{message_id}".')
    stream["chunks"].append(chunk)
    message = _find_message(next_state["messages"], message_id)
    if message is None:
        raise ChatThreadError(f'Stream chunk target message "{message_id}" does not exist.')
    message["content"] = f'{message.get("content", "")}{chunk}'
    message["status"] = "streaming"
    return next_state


def _apply_stream_complete(state: dict[str, object], event: Mapping[str, object]) -> dict[str, object]:
    next_state = normalize_chat_state(state)
    message_id = str(event.get("message_id") or "").strip()
    if not message_id:
        raise ChatThreadError("chat.stream.complete requires message_id.")
    stream_map = next_state["streaming"]
    if message_id not in stream_map:
        raise ChatThreadError(f'No active stream for message "{message_id}".')
    stream_map.pop(message_id, None)
    message = _find_message(next_state["messages"], message_id)
    if message is None:
        raise ChatThreadError(f'Stream completion target message "{message_id}" does not exist.')
    error_text = event.get("error")
    if isinstance(error_text, str) and error_text.strip():
        message["status"] = "error"
        message["error"] = error_text
    else:
        message["status"] = "complete"
        message["error"] = None
    return next_state


def _apply_citation_select(state: dict[str, object], event: Mapping[str, object]) -> dict[str, object]:
    next_state = normalize_chat_state(state)
    citation_id = str(event.get("citation_id") or "").strip()
    if not citation_id:
        raise ChatThreadError("chat.citation.select requires citation_id.")
    next_state["selected_citation"] = citation_id
    return next_state


def _event_sort_key(event: Mapping[str, object]) -> tuple[int, int, int, str, str]:
    order = _safe_int(event.get("order"))
    line = _safe_int(event.get("line"))
    column = _safe_int(event.get("column"))
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    return (order, line, column, event_id, event_type)


def _normalize_messages(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            continue
        message_id = str(entry.get("id") or f"message.{index}").strip()
        if not message_id:
            message_id = f"message.{index}"
        if message_id in seen_ids:
            raise ChatThreadError(f'Duplicate message id "{message_id}".')
        seen_ids.add(message_id)
        normalized.append(
            {
                "id": message_id,
                "role": _normalize_role(entry.get("role")),
                "content": str(entry.get("content") or ""),
                "citations": _normalize_citations(entry.get("citations")),
                "status": _normalize_status(entry.get("status")),
                "error": str(entry.get("error")) if isinstance(entry.get("error"), str) else None,
            }
        )
    return normalized


def _normalize_streaming(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, Mapping):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for message_id, entry in sorted(raw.items(), key=lambda item: str(item[0])):
        message_key = str(message_id).strip()
        if not message_key:
            continue
        role = "assistant"
        chunks: list[str] = []
        if isinstance(entry, Mapping):
            role = _normalize_role(entry.get("role"))
            raw_chunks = entry.get("chunks")
            if isinstance(raw_chunks, list):
                chunks = [str(chunk) for chunk in raw_chunks]
        normalized[message_key] = {"role": role, "chunks": chunks}
    return normalized


def _normalize_role(raw: object) -> str:
    role = str(raw or "assistant").strip().lower()
    if role in {"system", "user", "assistant", "tool"}:
        return role
    return "assistant"


def _normalize_status(raw: object) -> str:
    value = str(raw or "complete").strip().lower()
    if value in {"complete", "streaming", "error"}:
        return value
    return "complete"


def _normalize_citations(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    citations: list[str] = []
    for entry in raw:
        value = str(entry).strip()
        if not value:
            continue
        citations.append(value)
    return citations


def _find_message(messages: list[dict[str, object]], message_id: str) -> dict[str, object] | None:
    for message in messages:
        if message.get("id") == message_id:
            return message
    return None


def _next_message_id(messages: list[dict[str, object]]) -> str:
    return f"message.{len(messages) + 1}"


def _safe_int(value: object) -> int:
    return int(value) if isinstance(value, int) else 0


__all__ = [
    "ChatThreadError",
    "apply_chat_event",
    "apply_chat_events",
    "build_chat_thread_payload",
    "normalize_chat_state",
]
