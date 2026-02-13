from __future__ import annotations

from namel3ss.determinism import canonical_json_dumps
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.ui.actions.chat import message_sender
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


def test_chat_model_select_is_deterministic_for_unsorted_payload() -> None:
    program = lower_ir_program(SOURCE)
    first_state = _sample_state()
    second_state = _sample_state()
    action_id = _action_id(program, first_state, "chat.model.select")
    payload = {"active": ["model.beta", "model.alpha", "model.beta"]}

    first_response = handle_action(
        program,
        action_id=action_id,
        payload=payload,
        state=first_state,
        store=MemoryStore(),
    )
    second_response = handle_action(
        program,
        action_id=action_id,
        payload=payload,
        state=second_state,
        store=MemoryStore(),
    )

    assert canonical_json_dumps(first_response, pretty=False, drop_run_keys=False) == canonical_json_dumps(
        second_response,
        pretty=False,
        drop_run_keys=False,
    )
    assert first_state["chat"]["selected_model_ids"] == ["model.alpha", "model.beta"]
    assert first_state["chat"]["active_models"] == ["model.alpha", "model.beta"]


def test_chat_message_send_fanout_is_deterministic(monkeypatch) -> None:
    program = lower_ir_program(SOURCE)
    calls: list[dict] = []

    def fake_handle_call_flow_action(program_ir, action, action_id, payload, state, store, runtime_theme, **kwargs):
        calls.append(
            {
                "model_id": payload.get("model_id"),
                "model_ids": list(payload.get("model_ids") or []),
                "fanout_index": payload.get("fanout_index"),
                "fanout_count": payload.get("fanout_count"),
            }
        )
        return {
            "ok": True,
            "result": {"reply": "ok"},
            "state": state,
        }, None

    monkeypatch.setattr(message_sender, "handle_call_flow_action", fake_handle_call_flow_action)
    payload = {
        "message": "Need docs",
        "model_ids": ["model.beta", "model.alpha", "model.beta"],
        "attachments": ["upload.b", "upload.a"],
        "tools": ["web.lookup"],
        "web_search": True,
    }

    first_state = _sample_state()
    action_id = _action_id(program, first_state, "chat.message.send")
    second_state = _sample_state()

    first_response = handle_action(
        program,
        action_id=action_id,
        payload=payload,
        state=first_state,
        store=MemoryStore(),
    )
    first_calls = list(calls)
    calls.clear()
    second_response = handle_action(
        program,
        action_id=action_id,
        payload=payload,
        state=second_state,
        store=MemoryStore(),
    )
    second_calls = list(calls)

    assert canonical_json_dumps(first_response, pretty=False, drop_run_keys=False) == canonical_json_dumps(
        second_response,
        pretty=False,
        drop_run_keys=False,
    )
    assert first_calls == second_calls == [
        {
            "model_id": "model.alpha",
            "model_ids": ["model.alpha"],
            "fanout_index": 1,
            "fanout_count": 2,
        },
        {
            "model_id": "model.beta",
            "model_ids": ["model.beta"],
            "fanout_index": 2,
            "fanout_count": 2,
        },
    ]
    assert first_state["chat"]["selected_model_ids"] == ["model.alpha", "model.beta"]
    assert first_state["chat"]["composer_state"]["draft"] == ""


def _action_id(program, state: dict, action_type: str) -> str:
    manifest = build_manifest(program, state=state, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == action_type:
            return action_id
    raise AssertionError(f"{action_type} action not found")


def _sample_state() -> dict:
    return {
        "chat": {
            "messages": [],
            "threads": [
                {"id": "thread.main", "name": "Main"},
                {"id": "thread.docs", "name": "Docs"},
            ],
            "active_thread": "thread.main",
            "models": [
                {"id": "model.beta", "name": "Beta"},
                {"id": "model.alpha", "name": "Alpha"},
            ],
            "active_models": ["model.beta", "model.alpha"],
            "composer_state": {
                "attachments": [],
                "draft": "Need docs",
                "tools": [],
                "web_search": False,
            },
        }
    }
