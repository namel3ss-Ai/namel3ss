from __future__ import annotations

import json
from typing import Any

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


__all__ = ["SUMMARY_MAX_LENGTH", "summarize_payload", "summarize_text"]
