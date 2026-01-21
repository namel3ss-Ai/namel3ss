from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from namel3ss.determinism import canonical_json_dump
from namel3ss.runtime.persistence_paths import resolve_persistence_root


TRACE_DIRNAME = "traces"
TRACE_FILENAME = "trace.json"


def trace_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=True)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / TRACE_DIRNAME / TRACE_FILENAME


def _legacy_trace_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / "observability" / TRACE_FILENAME


class TraceStore:
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
        self._spans: list[dict] = []
        self._seq = 0
        self._stack: list[str] = []

    def reset(self) -> None:
        self._spans = []
        self._seq = 0
        self._stack = []

    def current_span_id(self) -> str | None:
        return self._stack[-1] if self._stack else None

    def start_span(
        self,
        *,
        name: str,
        kind: str,
        start_step: int,
        details: dict | None = None,
        parent_id: str | None = None,
    ) -> str:
        self._seq += 1
        span_id = f"span:{self._seq:04d}"
        parent = parent_id or self.current_span_id()
        span = {
            "id": span_id,
            "name": name,
            "kind": kind,
            "start_step": int(start_step),
        }
        if parent:
            span["parent_id"] = parent
        if details:
            span["details"] = details
        scrubbed = self._scrub(span)
        if isinstance(scrubbed, dict):
            span = scrubbed
        self._spans.append(span)
        self._stack.append(span_id)
        return span_id

    def end_span(self, span_id: str, *, status: str, end_step: int) -> dict | None:
        span = _find_span(self._spans, span_id)
        if span is None:
            return None
        span["status"] = status
        span["end_step"] = int(end_step)
        duration = span["end_step"] - int(span.get("start_step", 0))
        span["duration_steps"] = max(0, duration)
        if self._stack and self._stack[-1] == span_id:
            self._stack.pop()
        return span

    def snapshot(self) -> list[dict]:
        return list(self._spans)

    def flush(self) -> None:
        path = trace_path(self._project_root, self._app_path)
        if path is None:
            return
        canonical_json_dump(path, self.snapshot(), pretty=True)


def read_spans(project_root: str | Path | None, app_path: str | Path | None) -> list[dict]:
    path = trace_path(project_root, app_path)
    if path is None:
        return []
    if not path.exists():
        legacy = _legacy_trace_path(project_root, app_path)
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


def _find_span(spans: list[dict], span_id: str) -> dict | None:
    for span in reversed(spans):
        if span.get("id") == span_id:
            return span
    return None


__all__ = ["TraceStore", "read_spans", "trace_path"]
