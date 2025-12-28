from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

SUMMARY_MAX_LENGTH = 200
_SENSITIVE_KEYS = ("key", "secret", "token", "password", "authorization")


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}... (truncated)"


def _sanitize(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in _SENSITIVE_KEYS):
        return "(redacted)"
    return text


def summarize_text(value: Any, *, max_length: int = SUMMARY_MAX_LENGTH) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    flattened = " ".join(text.split())
    return _truncate(_sanitize(flattened), max_length)


def summarize_payload(value: Any, *, max_length: int = SUMMARY_MAX_LENGTH) -> str:
    try:
        serialized = json.dumps(value, default=str)
    except Exception:
        serialized = str(value)
    return _truncate(_sanitize(serialized), max_length)


def redact_memory_item(item: Mapping[str, Any]) -> dict:
    data = dict(item)
    if "text" in data:
        data["text"] = summarize_text(data.get("text"))
    kind = data.get("kind")
    if hasattr(kind, "value"):
        data["kind"] = getattr(kind, "value")
    if data.get("meta") is None:
        data["meta"] = {}
    return data


def redact_memory_items(items: Iterable[Mapping[str, Any]]) -> list[dict]:
    return [redact_memory_item(item) for item in items]


def redact_memory_context(context: Mapping[str, Any]) -> dict:
    return {key: redact_memory_items(context.get(key, [])) for key in ("short_term", "semantic", "profile")}


__all__ = [
    "SUMMARY_MAX_LENGTH",
    "redact_memory_context",
    "redact_memory_item",
    "redact_memory_items",
    "summarize_payload",
    "summarize_text",
]
