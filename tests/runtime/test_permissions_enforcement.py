from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _retrieval_action_id(program) -> str:
    manifest = build_manifest(program, state={}, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == "retrieval_run":
            return action_id
    raise AssertionError("retrieval_run action not found")


def test_runtime_denies_retrieval_when_uploads_read_is_denied() -> None:
    source = '''spec is "1.0"

capabilities:
  uploads
  app_permissions

permissions:
  uploads:
    read: denied
    write: allowed

page "Home":
  text is "Ready"
'''
    program = lower_ir_program(source)
    action_id = _retrieval_action_id(program)

    with pytest.raises(Namel3ssError) as exc:
        handle_action(
            program,
            action_id=action_id,
            payload={"query": "hello"},
            state={},
            store=MemoryStore(),
        )
    assert "uploads.read" in str(exc.value)


def test_runtime_allows_retrieval_when_uploads_read_is_allowed() -> None:
    source = '''spec is "1.0"

capabilities:
  uploads
  app_permissions

permissions:
  uploads:
    read: allowed
    write: denied

page "Home":
  text is "Ready"
'''
    program = lower_ir_program(source)
    action_id = _retrieval_action_id(program)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"query": "hello"},
        state={},
        store=MemoryStore(),
    )
    assert response.get("ok") is True


def test_runtime_legacy_mode_keeps_existing_behavior() -> None:
    source = '''spec is "1.0"

capabilities:
  uploads

page "Home":
  text is "Ready"
'''
    program = lower_ir_program(source)
    assert getattr(program, "app_permissions_enabled", False) is False
    action_id = _retrieval_action_id(program)
    response = handle_action(
        program,
        action_id=action_id,
        payload={"query": "hello"},
        state={},
        store=MemoryStore(),
    )
    assert response.get("ok") is True
