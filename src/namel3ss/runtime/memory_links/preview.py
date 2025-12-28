from __future__ import annotations

import re

from namel3ss.runtime.memory.facts import SENSITIVE_MARKERS

MAX_PREVIEW_LENGTH = 80

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

_BRACKET_CHARS = str.maketrans({")": " ", "(": " ", "]": " ", "[": " ", "}": " ", "{": " "})


def preview_text(value: object, *, max_length: int = MAX_PREVIEW_LENGTH) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    cleaned = _sanitize_text(text)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if _is_sensitive(lowered, cleaned):
        return "redacted"
    if len(cleaned) > max_length:
        trimmed = cleaned[:max_length].rstrip()
        return f"{trimmed} truncated"
    return cleaned


def _sanitize_text(text: str) -> str:
    sanitized = text.translate(_BRACKET_CHARS)
    sanitized = " ".join(sanitized.split())
    return sanitized.strip()


def _is_sensitive(lowered: str, raw_text: str) -> bool:
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        return True
    if _EMAIL_RE.search(raw_text):
        return True
    if _SSN_RE.search(raw_text):
        return True
    return False


__all__ = ["MAX_PREVIEW_LENGTH", "preview_text"]
