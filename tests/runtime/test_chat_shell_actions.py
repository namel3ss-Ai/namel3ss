from __future__ import annotations

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.ui.actions.build.action_registry import dispatch_action
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.contracts.action_kind import canonical_action_kind
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  ui_rag

flow "send":
  return "ok"

page "chat":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "send"
      threads from is state.chat.threads
      active_thread when is state.chat.active_thread
      models from is state.chat.models
      active_models when is state.chat.active_models
      composer_state when is state.chat.composer_state
'''.lstrip()


def _action_id(program, state: dict, action_type: str) -> str:
    manifest = build_manifest(program, state=state, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == action_type:
            return action_id
    raise AssertionError(f"{action_type} action not found")


def test_chat_thread_select_updates_state() -> None:
    program = lower_ir_program(SOURCE)
    state = _sample_state()
    action_id = _action_id(program, state, "chat.thread.select")
    response = handle_action(
        program,
        action_id=action_id,
        payload={"active": ["thread.docs"]},
        state=state,
        store=MemoryStore(),
    )
    assert response["state"]["chat"]["active_thread"] == "thread.docs"
    assert response["state"]["chat"]["active_thread_id"] == "thread.docs"
    assert response["state"]["chat"]["selected_model_ids"] == ["model.alpha"]
    assert response["state"]["chat"]["messages_graph"]["nodes"]
    assert response["state"]["chat"]["composer_state"]["draft"] == ""
    assert response["state"]["chat"]["stream_state"]["phase"] == "idle"


def test_chat_model_select_updates_state() -> None:
    program = lower_ir_program(SOURCE)
    state = _sample_state()
    action_id = _action_id(program, state, "chat.model.select")
    response = handle_action(
        program,
        action_id=action_id,
        payload={"active": ["model.beta"]},
        state=state,
        store=MemoryStore(),
    )
    assert response["state"]["chat"]["active_models"] == ["model.beta"]
    assert response["state"]["chat"]["selected_model_ids"] == ["model.beta"]
    assert response["state"]["chat"]["active_thread_id"] == "thread.main"


def test_chat_thread_select_rejects_unknown_thread() -> None:
    program = lower_ir_program(SOURCE)
    state = _sample_state()
    action_id = _action_id(program, state, "chat.thread.select")
    with pytest.raises(Namel3ssError) as err:
        handle_action(
            program,
            action_id=action_id,
            payload={"active": ["thread.missing"]},
            state=state,
            store=MemoryStore(),
        )
    assert "unknown thread id" in str(err.value).lower()


def test_chat_message_send_uses_composer_state_and_clears_draft() -> None:
    program = lower_ir_program(SOURCE)
    state = _sample_state()
    state["chat"]["composer_state"] = {"attachments": [], "draft": "Need docs", "tools": [], "web_search": False}
    action_id = _action_id(program, state, "chat.message.send")
    response = handle_action(
        program,
        action_id=action_id,
        payload={},
        state=state,
        store=MemoryStore(),
    )
    assert response["state"]["chat"]["composer_state"]["draft"] == ""
    assert response["state"]["chat"]["messages_graph"]["nodes"][-1]["content"] == "Need docs"
    assert response["state"]["chat"]["messages_graph"]["nodes"][-1]["role"] == "user"
    assert response["state"]["chat"]["stream_state"]["phase"] == "thinking"


def test_dispatch_accepts_legacy_chat_action_aliases() -> None:
    program = lower_ir_program(SOURCE)
    state = _sample_state()
    store = MemoryStore()
    config = load_config(
        app_path=getattr(program, "app_path", None),
        root=getattr(program, "project_root", None),
    )
    legacy_action = {
        "id": "legacy.chat.thread.select",
        "type": "chat_thread_select",
        "target_state": "state.chat.active_thread",
        "options_state": "state.chat.threads",
    }
    ctx = ActionDispatchContext(
        program_ir=program,
        action=legacy_action,
        action_id=legacy_action["id"],
        action_type=canonical_action_kind(legacy_action["type"]),
        payload={"active": ["thread.docs"]},
        state=state,
        store=store,
        runtime_theme=None,
        config=config,
        manifest={"actions": {legacy_action["id"]: legacy_action}},
        identity=None,
        auth_context=None,
        session=None,
        source=None,
        secret_values=[],
        memory_manager=None,
        preference_store=None,
        preference_key=None,
        allow_theme_override=None,
        raise_on_error=True,
        ui_mode="studio",
        diagnostics_enabled=False,
    )
    response, action_error = dispatch_action(ctx)
    assert action_error is None
    assert response["state"]["chat"]["active_thread_id"] == "thread.docs"


def _sample_state() -> dict:
    return {
        "chat": {
            "messages": [{"role": "user", "content": "Hi"}],
            "threads": [
                {"id": "thread.main", "name": "Main"},
                {"id": "thread.docs", "name": "Docs"},
            ],
            "active_thread": "thread.main",
            "models": [
                {"id": "model.alpha", "name": "Alpha"},
                {"id": "model.beta", "name": "Beta"},
            ],
            "active_models": ["model.alpha"],
        }
    }
