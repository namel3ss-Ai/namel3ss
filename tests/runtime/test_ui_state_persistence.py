import json

import pytest

from namel3ss.runtime.ui_state_engine import UIStateEngineError, persist_state, restore_state, storage_keys
from tests.conftest import lower_ir_program


def _declaration():
    source = """spec is "1.0"

capabilities:
  ui_state

ui_state:
  ephemeral:
    stream_phase is text
  session:
    current_page is text
    drawer_open is boolean
  persistent:
    theme is text

page "Home":
  text is "Ready"
"""
    program = lower_ir_program(source)
    return getattr(program, "ui_state", None)


def test_ui_state_restore_merges_defaults_and_restored_values() -> None:
    declaration = _declaration()
    keys = storage_keys("demo_app")
    session_store = {keys["session"]: json.dumps({"current_page": "Sources"})}
    persistent_store = {keys["persistent"]: json.dumps({"theme": "dark"})}
    state, sources = restore_state(
        base_state={},
        declaration=declaration,
        app_id="demo_app",
        session_store=session_store,
        persistent_store=persistent_store,
    )
    assert state == {
        "ui": {
            "stream_phase": "",
            "current_page": "Sources",
            "drawer_open": False,
            "theme": "dark",
        }
    }
    assert sources == {
        "ui.current_page": "restored",
        "ui.drawer_open": "default",
        "ui.stream_phase": "default",
        "ui.theme": "restored",
    }


def test_ui_state_persist_writes_canonical_json() -> None:
    declaration = _declaration()
    keys = storage_keys("demo_app")
    session_store: dict[str, str] = {}
    persistent_store: dict[str, str] = {}
    state = {
        "ui": {
            "stream_phase": "streaming",
            "current_page": "Chat",
            "drawer_open": True,
            "theme": "light",
        }
    }
    persist_state(
        state=state,
        declaration=declaration,
        app_id="demo_app",
        session_store=session_store,
        persistent_store=persistent_store,
    )
    first_session = session_store[keys["session"]]
    first_persistent = persistent_store[keys["persistent"]]
    persist_state(
        state=state,
        declaration=declaration,
        app_id="demo_app",
        session_store=session_store,
        persistent_store=persistent_store,
    )
    assert session_store[keys["session"]] == first_session
    assert persistent_store[keys["persistent"]] == first_persistent
    assert first_session == '{"current_page":"Chat","drawer_open":true}'
    assert first_persistent == '{"theme":"light"}'


def test_ui_state_restore_rejects_invalid_json_payload() -> None:
    declaration = _declaration()
    keys = storage_keys("demo_app")
    with pytest.raises(UIStateEngineError) as exc:
        restore_state(
            base_state={},
            declaration=declaration,
            app_id="demo_app",
            session_store={keys["session"]: "not-json"},
            persistent_store={},
        )
    assert "invalid JSON" in str(exc.value)
