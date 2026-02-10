from __future__ import annotations

import pytest

from namel3ss.runtime.interaction_dispatcher import (
    InteractionDispatcherError,
    dispatch_interactions,
    keyboard_action_ids,
    normalize_action_registry,
)


def test_normalize_action_registry_is_deterministic_for_iterables() -> None:
    actions = [
        {"id": "b", "type": "call_flow", "target": "second"},
        {"id": "a", "type": "call_flow", "target": "first"},
    ]
    first = normalize_action_registry(actions)
    second = normalize_action_registry(actions)
    assert list(first.keys()) == ["a", "b"]
    assert first == second


def test_keyboard_action_ids_sort_by_order_and_source_location() -> None:
    actions = {
        "action.z": {
            "id": "action.z",
            "type": "layout.shortcut",
            "shortcut": "ctrl+enter",
            "order": 3,
            "line": 20,
            "column": 2,
        },
        "action.a": {
            "id": "action.a",
            "type": "layout.shortcut",
            "shortcut": "ctrl+enter",
            "order": 1,
            "line": 10,
            "column": 1,
        },
        "action.b": {
            "id": "action.b",
            "type": "layout.shortcut",
            "target": "ctrl+enter",
            "order": 2,
            "line": 10,
            "column": 4,
        },
    }
    assert keyboard_action_ids(actions, "ENTER+CTRL") == ["action.a", "action.b", "action.z"]


def test_dispatch_interactions_applies_layout_state_actions_in_event_order() -> None:
    actions = {
        "open": {"id": "open", "type": "layout.drawer.open", "target": "drawer.sources"},
        "toggle": {"id": "toggle", "type": "layout.drawer.toggle", "target": "drawer.sources"},
    }
    initial = {"drawers": {"drawer.sources": False}, "sticky": {}, "selection": {}}
    result = dispatch_interactions(
        initial,
        actions=actions,
        events=[
            {"action_id": "toggle", "order": 2},
            {"action_id": "open", "order": 1},
        ],
    )
    assert result["executed"] == ["open", "toggle"]
    assert result["state"]["drawers"]["drawer.sources"] is False


def test_dispatch_interactions_delegates_non_state_layout_actions() -> None:
    actions = {
        "shortcut": {
            "id": "shortcut",
            "type": "layout.shortcut",
            "shortcut": "ctrl+enter",
            "payload": {"dispatch_action_id": "send"},
        },
        "send": {"id": "send", "type": "layout.interaction", "target": "send_message"},
    }
    delegated: list[tuple[str, object]] = []

    def executor(action: dict, payload: dict | None) -> str:
        delegated.append((str(action.get("id")), payload))
        return "ok"

    result = dispatch_interactions(
        {"drawers": {}, "sticky": {}, "selection": {}},
        actions=actions,
        events=[{"action_id": "shortcut"}, {"action_id": "send", "order": 1}],
        executor=executor,
    )
    assert [entry["status"] for entry in result["results"]] == ["delegated", "delegated"]
    assert delegated[0][0] == "shortcut"
    assert delegated[1][0] == "send"


def test_dispatch_interactions_raises_for_unknown_action_id() -> None:
    with pytest.raises(InteractionDispatcherError) as err:
        dispatch_interactions(
            {"drawers": {}, "sticky": {}, "selection": {}},
            actions={},
            events=[{"action_id": "missing"}],
        )
    assert "Unknown action id" in str(err.value)


def test_dispatch_interactions_rejects_event_without_action_id() -> None:
    with pytest.raises(InteractionDispatcherError) as err:
        dispatch_interactions(
            {"drawers": {}, "sticky": {}, "selection": {}},
            actions={},
            events=[{"payload": {"x": 1}}],
        )
    assert "require action_id" in str(err.value)
