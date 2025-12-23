from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

from namel3ss.secrets import redact_payload
from namel3ss.utils.json_tools import dumps as json_dumps


EVENTS_FILENAME = ".namel3ss/observe.jsonl"


def events_path(project_root: Path) -> Path:
    return project_root / EVENTS_FILENAME


def record_event(project_root: Path, event: dict, *, secret_values: Iterable[str] | None = None) -> None:
    payload = dict(event)
    if "time" not in payload:
        payload["time"] = time.time()
    if secret_values:
        payload = redact_payload(payload, secret_values)  # type: ignore[assignment]
    path = events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json_dumps(payload) + "\n")


def read_events(project_root: Path) -> list[dict]:
    path = events_path(project_root)
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def filter_events(events: list[dict], since_seconds: float | None) -> list[dict]:
    if since_seconds is None:
        return sorted(events, key=lambda e: e.get("time", 0))
    threshold = time.time() - since_seconds
    filtered = [event for event in events if event.get("time", 0) >= threshold]
    return sorted(filtered, key=lambda e: e.get("time", 0))


__all__ = ["EVENTS_FILENAME", "events_path", "record_event", "read_events", "filter_events"]
