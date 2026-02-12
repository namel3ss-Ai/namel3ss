from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class StatusEvent:
    event_id: str
    kind: str
    message: str
    order: int

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "message": self.message,
            "order": self.order,
        }


def normalize_status_events(events: Sequence[Mapping[str, object]] | None) -> list[StatusEvent]:
    rows: list[StatusEvent] = []
    for index, event in enumerate(events or (), start=1):
        event_id = _text(event.get("event_id")) or f"event_{index}"
        kind = _text(event.get("kind")) or "info"
        message = _text(event.get("message")) or "No details."
        order = _int_value(event.get("order"), default=index)
        rows.append(StatusEvent(event_id=event_id, kind=kind, message=message, order=order))
    rows.sort(key=lambda item: (item.order, item.event_id, item.kind, item.message))
    return rows


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int_value(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return default


__all__ = ["StatusEvent", "normalize_status_events"]
