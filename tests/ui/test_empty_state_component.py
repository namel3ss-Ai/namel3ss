from __future__ import annotations

from namel3ss.ui.components.empty_state import build_empty_state


def test_empty_state_component_is_stable() -> None:
    assert build_empty_state(title="  No rows  ", text="  Add data  ", hint="  Try upload  ") == {
        "hint": "Try upload",
        "text": "Add data",
        "title": "No rows",
    }


def test_empty_state_component_defaults_hint_to_empty_text() -> None:
    assert build_empty_state(title="No rows", text="Add data") == {
        "hint": "",
        "text": "Add data",
        "title": "No rows",
    }
