from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''
spec is "1.0"

page "docs":
  scope_selector from state.documents active in state.active_docs
'''.lstrip()


def _scope_selector_action_id(program, state: dict) -> str:
    manifest = build_manifest(program, state=state, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == "scope_select":
            return action_id
    raise AssertionError("Scope selector action not found")


def test_scope_selector_updates_state() -> None:
    program = lower_ir_program(SOURCE)
    state = {
        "documents": [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}],
        "active_docs": ["a"],
    }
    action_id = _scope_selector_action_id(program, state)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"active": ["b"]},
        state=state,
        store=MemoryStore(),
    )
    assert response["state"]["active_docs"] == ["b"]


def test_scope_selector_requires_text_ids() -> None:
    program = lower_ir_program(SOURCE)
    state = {
        "documents": [{"id": "a", "name": "Alpha"}],
        "active_docs": [],
    }
    action_id = _scope_selector_action_id(program, state)
    with pytest.raises(Namel3ssError) as exc:
        handle_action(
            program,
            action_id=action_id,
            payload={"active": [1]},
            state=state,
            store=MemoryStore(),
        )
    assert "scope selector payload" in str(exc.value).lower()
