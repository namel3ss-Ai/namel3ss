from __future__ import annotations

import re

from namel3ss.runtime.execution.normalize import stable_truncate

_SAFE_PREFIXES = ("/api/", "/health", "/version", "/ui", "/docs/")
_INLINE_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\\\[^\\s]+")
_INLINE_POSIX_PATH = re.compile(r"/[^\\s]+")


def _safe_text(value: object) -> str:
    text = _string(value)
    if not text:
        return ""
    cleaned = _scrub_inline_paths(text)
    return stable_truncate(cleaned, limit=200)


def _scrub_inline_paths(text: str) -> str:
    def _replace_posix(match: re.Match) -> str:
        path = match.group(0)
        if path.startswith(_SAFE_PREFIXES):
            return path
        return "<path>"

    cleaned = _INLINE_WINDOWS_PATH.sub("<path>", text)
    cleaned = _INLINE_POSIX_PATH.sub(_replace_posix, cleaned)
    return cleaned


def _string(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
