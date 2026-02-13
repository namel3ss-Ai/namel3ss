from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps

_FLOW_STREAM_EVENT_ORDER = {"yield": 0}
_AI_STREAM_EVENT_ORDER = {"progress": 0, "token": 1, "finish": 2, "error": 3}
_CHAT_STREAM_EVENT_ORDER = {
    "chat.thread.list": 0,
    "chat.thread.load": 1,
    "chat.thread.save": 2,
}
_CHANNEL_ORDER = {"": 0, "flow": 0, "chat": 1, "ai": 2}


def build_sse_body(yield_messages: list[dict], response: dict) -> bytes:
    lines: list[str] = []
    for message in yield_messages:
        channel = _safe_stream_channel(message.get("stream_channel") if isinstance(message, dict) else None)
        event_type = _safe_event_type(message.get("event_type") if isinstance(message, dict) else None, channel=channel)
        lines.append(f"event: {event_type}")
        lines.append(f"data: {canonical_json_dumps(message, pretty=False, drop_run_keys=False)}")
        lines.append("")
    lines.append("event: return")
    lines.append(f"data: {canonical_json_dumps(response, pretty=False, drop_run_keys=False)}")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def sorted_yield_messages(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        channel = _safe_stream_channel(item.get("stream_channel"))
        event_type = _safe_event_type(item.get("event_type"), channel=channel)
        payload = {
            "event_type": event_type,
            "flow_name": str(item.get("flow_name") or ""),
            "output": item.get("output"),
            "sequence": _safe_int(item.get("sequence")),
            "timestamp": _safe_timestamp(item.get("timestamp")),
        }
        if "data" in item:
            payload["data"] = item.get("data")
        if "stream_id" in item:
            payload["stream_id"] = str(item.get("stream_id") or "")
        if channel:
            payload["stream_channel"] = channel
        rows.append(payload)
    rows.sort(key=_event_sort_key)
    return rows


def should_stream_response(query: dict[str, str], headers: dict[str, str], yield_messages: list[dict]) -> bool:
    explicit_request = _explicit_stream_requested(query, headers)
    if _contains_non_explicit_stream_yields(yield_messages):
        return True
    if _contains_stream_channel(yield_messages, "ai"):
        return explicit_request
    if _contains_stream_channel(yield_messages, "chat"):
        return explicit_request
    return explicit_request


def _explicit_stream_requested(query: dict[str, str], headers: dict[str, str]) -> bool:
    stream = str(query.get("stream") or "").strip().lower()
    if stream in {"1", "true", "yes", "on"}:
        return True
    accept = str(headers.get("Accept") or headers.get("accept") or "").lower()
    if "text/event-stream" in accept:
        return True
    header_stream = str(headers.get("X-N3-Stream") or headers.get("x-n3-stream") or "").strip().lower()
    return header_stream in {"1", "true", "yes", "on"}


def _contains_non_explicit_stream_yields(yield_messages: list[dict]) -> bool:
    for item in yield_messages:
        if not isinstance(item, dict):
            return True
        channel = _safe_stream_channel(item.get("stream_channel"))
        if channel in {"ai", "chat"}:
            continue
        return True
    return False


def _contains_stream_channel(yield_messages: list[dict], channel: str) -> bool:
    for item in yield_messages:
        if not isinstance(item, dict):
            continue
        if _safe_stream_channel(item.get("stream_channel")) == channel:
            return True
    return False


def _event_sort_key(entry: dict) -> tuple:
    channel = _safe_stream_channel(entry.get("stream_channel"))
    event_type = _safe_event_type(entry.get("event_type"), channel=channel)
    output_dump = canonical_json_dumps(entry.get("output"), pretty=False, drop_run_keys=False)
    data_dump = canonical_json_dumps(entry.get("data"), pretty=False, drop_run_keys=False)
    return (
        _safe_int(entry.get("sequence")),
        _CHANNEL_ORDER.get(channel, 9),
        _event_order(channel=channel, event_type=event_type),
        str(entry.get("flow_name") or ""),
        str(entry.get("stream_id") or ""),
        output_dump,
        data_dump,
    )


def _event_order(*, channel: str, event_type: str) -> int:
    if channel == "ai":
        return _AI_STREAM_EVENT_ORDER.get(event_type, 99)
    if channel == "chat":
        return _CHAT_STREAM_EVENT_ORDER.get(event_type, 99)
    if event_type in _FLOW_STREAM_EVENT_ORDER:
        return _FLOW_STREAM_EVENT_ORDER[event_type]
    if event_type in _AI_STREAM_EVENT_ORDER:
        return _AI_STREAM_EVENT_ORDER[event_type]
    if event_type in _CHAT_STREAM_EVENT_ORDER:
        return _CHAT_STREAM_EVENT_ORDER[event_type]
    return 99


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except Exception:
        return 0
    if parsed < 0:
        return 0
    return parsed


def _safe_event_type(value: object, *, channel: str) -> str:
    token = str(value or "").strip().lower()
    if channel == "ai":
        if token in _AI_STREAM_EVENT_ORDER:
            return token
        return "yield"
    if channel == "chat":
        if token in _CHAT_STREAM_EVENT_ORDER:
            return token
        return "yield"
    if token in _FLOW_STREAM_EVENT_ORDER:
        return token
    if token in _AI_STREAM_EVENT_ORDER:
        return token
    if token in _CHAT_STREAM_EVENT_ORDER:
        return token
    return "yield"


def _safe_stream_channel(value: object) -> str:
    token = str(value or "").strip().lower()
    if token in {"ai", "chat", "flow"}:
        return token
    return ""


def _safe_timestamp(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "build_sse_body",
    "should_stream_response",
    "sorted_yield_messages",
]
