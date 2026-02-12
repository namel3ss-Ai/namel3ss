from __future__ import annotations

from namel3ss.studio.status.status_renderer import render_status_panel


def test_status_renderer_returns_deterministic_empty_state() -> None:
    payload = render_status_panel([])
    assert payload == {
        "empty_state": {
            "hint": "",
            "text": "Run your app to populate deterministic status updates.",
            "title": "No status events",
        },
        "events": [],
        "summary": {"error": 0, "info": 0, "warn": 0},
    }


def test_status_renderer_sorts_events_by_order_then_id() -> None:
    payload = render_status_panel(
        [
            {"event_id": "b", "kind": "warn", "message": "later", "order": 2},
            {"event_id": "a", "kind": "info", "message": "earlier", "order": 1},
        ]
    )
    assert [event["event_id"] for event in payload["events"]] == ["a", "b"]
    assert payload["summary"] == {"error": 0, "info": 1, "warn": 1}
