from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from namel3ss.determinism import canonical_json_dump
from namel3ss.runtime.persistence_paths import resolve_persistence_root


LOG_LEVELS = {"debug", "info", "warn", "error"}
LOG_DIRNAME = "logs"
LOG_FILENAME = "logs.json"


def logs_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=True)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / LOG_DIRNAME / LOG_FILENAME


def _legacy_logs_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / LOG_FILENAME


class LogStore:
    def __init__(
        self,
        *,
        project_root: str | Path | None,
        app_path: str | Path | None,
        scrubber: Callable[[object], object],
    ) -> None:
        self._project_root = project_root
        self._app_path = app_path
        self._scrub = scrubber
        self._logs: list[dict] = []
        self._seq = 0

    def reset(self) -> None:
        self._logs = []
        self._seq = 0

    def record(
        self,
        *,
        level: str,
        message: object,
        fields: object | None = None,
        span_id: str | None = None,
    ) -> dict:
        normalized_level = level.lower().strip()
        if normalized_level not in LOG_LEVELS:
            normalized_level = "info"
        self._seq += 1
        event = {
            "id": f"log:{self._seq:04d}",
            "level": normalized_level,
            "message": _coerce_message(message),
        }
        if span_id:
            event["span_id"] = span_id
        if fields is not None:
            event["fields"] = fields
        scrubbed = self._scrub(event)
        if isinstance(scrubbed, dict):
            self._logs.append(scrubbed)
            return scrubbed
        self._logs.append(event)
        return event

    def snapshot(self) -> list[dict]:
        return list(self._logs)

    def flush(self) -> None:
        path = logs_path(self._project_root, self._app_path)
        if path is None:
            return
        canonical_json_dump(path, self.snapshot(), pretty=True)


def read_logs(project_root: str | Path | None, app_path: str | Path | None) -> list[dict]:
    path = logs_path(project_root, app_path)
    if path is None:
        return []
    if not path.exists():
        legacy = _legacy_logs_path(project_root, app_path)
        if legacy is None or not legacy.exists():
            return []
        path = legacy
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _coerce_message(message: object) -> str:
    if message is None:
        return ""
    if isinstance(message, str):
        return message
    return str(message)


__all__ = ["LOG_LEVELS", "LogStore", "logs_path", "read_logs"]
