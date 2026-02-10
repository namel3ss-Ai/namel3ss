from __future__ import annotations

import pytest

from namel3ss.runtime.layout_state import (
    LayoutStateError,
    apply_layout_action,
    apply_layout_actions,
    build_layout_state,
    normalize_layout_state,
)


def test_build_layout_state_collects_drawers_sticky_and_selection() -> None:
    layout = [
        {
            "type": "layout.drawer",
            "id": "drawer.sources",
            "open_state": False,
            "bindings": {},
            "children": [],
        },
        {
            "type": "layout.sticky",
            "id": "sticky.composer",
            "position": "bottom",
            "visible": True,
            "bindings": {},
            "children": [],
        },
        {
            "type": "component.card",
            "id": "card.documents",
            "bindings": {"selected_item": "ui.selected_document"},
            "children": [],
        },
    ]
    state = {"ui": {"selected_document": "doc-1"}}
    layout_state = build_layout_state(layout, state=state)
    assert layout_state == {
        "drawers": {"drawer.sources": False},
        "sticky": {"sticky.composer": {"position": "bottom", "visible": True}},
        "selection": {"ui.selected_document": "doc-1"},
    }


def test_apply_layout_action_drawer_transitions() -> None:
    state = normalize_layout_state({"drawers": {"drawer.sources": False}, "sticky": {}, "selection": {}})
    opened = apply_layout_action(state, {"type": "layout.drawer.open", "target": "drawer.sources"})
    assert opened["drawers"]["drawer.sources"] is True
    toggled = apply_layout_action(opened, {"type": "layout.drawer.toggle", "target": "drawer.sources"})
    assert toggled["drawers"]["drawer.sources"] is False
    closed = apply_layout_action(toggled, {"type": "layout.drawer.close", "target": "drawer.sources"})
    assert closed["drawers"]["drawer.sources"] is False


def test_apply_layout_action_sticky_visibility_transitions() -> None:
    state = normalize_layout_state(
        {
            "drawers": {},
            "sticky": {"sticky.composer": {"position": "bottom", "visible": True}},
            "selection": {},
        }
    )
    hidden = apply_layout_action(state, {"type": "layout.sticky.hide", "target": "sticky.composer"})
    assert hidden["sticky"]["sticky.composer"]["visible"] is False
    shown = apply_layout_action(hidden, {"type": "layout.sticky.show", "target": "sticky.composer"})
    assert shown["sticky"]["sticky.composer"]["visible"] is True


def test_apply_layout_action_selection_update() -> None:
    state = normalize_layout_state({"drawers": {}, "sticky": {}, "selection": {}})
    updated = apply_layout_action(
        state,
        {"type": "layout.selection.set"},
        payload={"path": "ui.selected_document", "value": "doc-2"},
    )
    assert updated["selection"]["ui.selected_document"] == "doc-2"


def test_apply_layout_actions_runs_in_deterministic_order() -> None:
    state = normalize_layout_state({"drawers": {"drawer.sources": False}, "sticky": {}, "selection": {}})
    actions = [
        {"id": "b", "type": "layout.drawer.toggle", "target": "drawer.sources", "order": 2},
        {"id": "a", "type": "layout.drawer.open", "target": "drawer.sources", "order": 1},
    ]
    result = apply_layout_actions(state, actions)
    assert result["drawers"]["drawer.sources"] is False


def test_unknown_target_raises_clear_error() -> None:
    state = normalize_layout_state({"drawers": {}, "sticky": {}, "selection": {}})
    with pytest.raises(LayoutStateError) as err:
        apply_layout_action(state, {"type": "layout.drawer.open", "target": "drawer.unknown"})
    assert "Unknown drawer target" in str(err.value)
