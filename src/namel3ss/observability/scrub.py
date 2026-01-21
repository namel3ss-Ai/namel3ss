from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from namel3ss.security import redact_sensitive_payload


_SAFE_PREFIXES = ("/api/", "/health", "/version", "/ui", "/docs/")
_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\\\[^\\s]+")
_POSIX_PATH = re.compile(r"/[^\\s]+")


def scrub_payload(
    value: object,
    *,
    secret_values: Iterable[str],
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> object:
    redacted = redact_sensitive_payload(value, secret_values)
    return _scrub_paths(redacted, project_root=project_root, app_path=app_path)


def scrub_text(
    text: str,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> str:
    if not text:
        return text
    cleaned = text
    cleaned = _replace_known_path(cleaned, project_root)
    cleaned = _replace_known_path(cleaned, app_path)
    cleaned = _replace_known_path(cleaned, Path.home())
    if "://" in cleaned and not cleaned.startswith("file://"):
        return cleaned
    cleaned = _WINDOWS_PATH.sub("<path>", cleaned)
    cleaned = _POSIX_PATH.sub(lambda match: _replace_posix(match.group(0)), cleaned)
    return cleaned


def _replace_known_path(text: str, path_value: str | Path | None) -> str:
    if not path_value:
        return text
    try:
        path = Path(path_value)
    except Exception:
        return text.replace(str(path_value), "<path>")
    posix = path.as_posix()
    return text.replace(posix, "<path>").replace(str(path), "<path>")


def _replace_posix(path: str) -> str:
    if path.startswith(_SAFE_PREFIXES):
        return path
    return "<path>"


def _scrub_paths(
    value: object,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> object:
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, item in value.items():
            key_text = scrub_text(str(key), project_root=project_root, app_path=app_path)
            cleaned[key_text] = _scrub_paths(item, project_root=project_root, app_path=app_path)
        return cleaned
    if isinstance(value, list):
        return [_scrub_paths(item, project_root=project_root, app_path=app_path) for item in value]
    if isinstance(value, Path):
        return "<path>"
    if isinstance(value, str):
        return scrub_text(value, project_root=project_root, app_path=app_path)
    return value


__all__ = ["scrub_payload", "scrub_text"]
