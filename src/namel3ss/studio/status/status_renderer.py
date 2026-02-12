from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.studio.status.status_events import normalize_status_events
from namel3ss.ui.components.empty_state import build_empty_state


def render_status_panel(
    events: Sequence[Mapping[str, object]] | None,
    *,
    empty_title: str = "No status events",
    empty_text: str = "Run your app to populate deterministic status updates.",
) -> dict[str, object]:
    normalized = normalize_status_events(events)
    if not normalized:
        return {
            "empty_state": build_empty_state(title=empty_title, text=empty_text),
            "events": [],
            "summary": {"error": 0, "info": 0, "warn": 0},
        }
    summary = {
        "error": len([event for event in normalized if event.kind == "error"]),
        "info": len([event for event in normalized if event.kind == "info"]),
        "warn": len([event for event in normalized if event.kind == "warn"]),
    }
    return {
        "empty_state": None,
        "events": [event.to_dict() for event in normalized],
        "summary": summary,
    }


__all__ = ["render_status_panel"]
