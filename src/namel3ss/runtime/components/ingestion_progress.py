from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


class IngestionProgressError(RuntimeError):
    """Raised when ingestion progress updates are invalid."""


STAGE_ORDER = ("idle", "uploading", "chunking", "embedding", "indexing", "complete", "failed")


def normalize_ingestion_progress_state(state: Mapping[str, object] | None) -> dict[str, object]:
    source = dict(state or {})
    status = _normalize_stage(source.get("status"))
    percent = _normalize_percent(source.get("percent"))
    errors = _normalize_errors(source.get("errors"))
    return {
        "status": status,
        "percent": percent,
        "errors": errors,
    }


def apply_ingestion_event(
    ingestion_state: Mapping[str, object] | None,
    event: Mapping[str, object],
) -> dict[str, object]:
    state = normalize_ingestion_progress_state(ingestion_state)
    event_type = str(event.get("type") or "")
    if event_type == "ingestion.stage.set":
        stage = _normalize_stage(event.get("stage"))
        state["status"] = stage
        if stage == "complete":
            state["percent"] = 100
        return state
    if event_type == "ingestion.percent.set":
        state["percent"] = _normalize_percent(event.get("percent"))
        return state
    if event_type == "ingestion.error.add":
        message = str(event.get("message") or "").strip()
        if not message:
            raise IngestionProgressError("ingestion.error.add requires a message.")
        state["status"] = "failed"
        state["errors"] = [*state["errors"], message]
        return state
    if event_type == "ingestion.retry":
        state["status"] = "uploading"
        state["percent"] = 0
        state["errors"] = []
        return state
    if event_type == "ingestion.complete":
        state["status"] = "complete"
        state["percent"] = 100
        return state
    raise IngestionProgressError(f"Unsupported ingestion event type '{event_type}'.")


def apply_ingestion_events(
    ingestion_state: Mapping[str, object] | None,
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    state = normalize_ingestion_progress_state(ingestion_state)
    ordered = sorted(list(events), key=_event_sort_key)
    for event in ordered:
        state = apply_ingestion_event(state, event)
    return state


def build_ingestion_progress_payload(
    ingestion_state: Mapping[str, object] | None,
    *,
    component_id: str,
    retry_action_id: str | None = None,
) -> dict[str, object]:
    state = normalize_ingestion_progress_state(ingestion_state)
    return {
        "type": "component.ingestion_progress",
        "id": component_id,
        "status": state["status"],
        "percent": state["percent"],
        "errors": deepcopy(state["errors"]),
        "stages": list(STAGE_ORDER),
        "bindings": {
            "on_click": retry_action_id,
            "keyboard_shortcut": None,
            "selected_item": None,
        },
    }


def _event_sort_key(event: Mapping[str, object]) -> tuple[int, int, int, str]:
    return (
        _safe_int(event.get("order")),
        _safe_int(event.get("line")),
        _safe_int(event.get("column")),
        str(event.get("id") or ""),
    )


def _normalize_stage(raw: object) -> str:
    value = str(raw or "idle").strip().lower()
    if value in STAGE_ORDER:
        return value
    raise IngestionProgressError(f"Unknown ingestion stage '{value}'.")


def _normalize_percent(raw: object) -> int:
    if isinstance(raw, int):
        return max(0, min(100, raw))
    return 0


def _normalize_errors(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(entry) for entry in raw if str(entry).strip()]


def _safe_int(value: object) -> int:
    return int(value) if isinstance(value, int) else 0


__all__ = [
    "IngestionProgressError",
    "STAGE_ORDER",
    "apply_ingestion_event",
    "apply_ingestion_events",
    "build_ingestion_progress_payload",
    "normalize_ingestion_progress_state",
]
