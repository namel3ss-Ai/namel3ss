from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.actions.chat import message_sender


def test_chat_message_send_runs_deterministic_model_fanout_and_restores_selection(monkeypatch) -> None:
    state = _sample_state()
    calls: list[dict] = []

    def fake_handle_call_flow_action(program_ir, action, action_id, payload, state, store, runtime_theme, **kwargs):
        calls.append(
            {
                "fanout_count": payload.get("fanout_count"),
                "fanout_index": payload.get("fanout_index"),
                "model_id": payload.get("model_id"),
                "model_ids": list(payload.get("model_ids") or []),
                "selected": list((state.get("chat") or {}).get("selected_model_ids") or []),
            }
        )
        return {
            "ok": True,
            "result": {"model_id": payload.get("model_id")},
            "state": state,
        }, None

    monkeypatch.setattr(message_sender, "handle_call_flow_action", fake_handle_call_flow_action)
    response, action_error = message_sender.handle_chat_message_send_action(
        None,
        {"flow": "send"},
        "chat.send",
        {},
        state,
        store=None,
        runtime_theme=None,
        raise_on_error=False,
    )

    assert action_error is None
    assert [entry["model_id"] for entry in calls] == ["model.alpha", "model.beta"]
    assert [entry["selected"] for entry in calls] == [["model.alpha"], ["model.beta"]]
    assert [entry["model_ids"] for entry in calls] == [["model.alpha"], ["model.beta"]]
    assert [entry["fanout_index"] for entry in calls] == [1, 2]
    assert [entry["fanout_count"] for entry in calls] == [2, 2]
    assert state["chat"]["selected_model_ids"] == ["model.alpha", "model.beta"]
    assert state["chat"]["active_models"] == ["model.alpha", "model.beta"]
    assert state["chat"]["composer_state"]["draft"] == ""
    assert state["chat"]["messages"][-1]["content"] == "Need docs"

    fanout = response["result"]["fanout"]
    assert fanout == {
        "completed": True,
        "enabled": True,
        "model_count": 2,
        "models": ["model.alpha", "model.beta"],
        "runs": [
            {"index": 1, "model_id": "model.alpha", "ok": True},
            {"index": 2, "model_id": "model.beta", "ok": True},
        ],
    }


def test_chat_message_send_with_single_explicit_model_skips_fanout(monkeypatch) -> None:
    state = _sample_state()
    calls: list[dict] = []

    def fake_handle_call_flow_action(program_ir, action, action_id, payload, state, store, runtime_theme, **kwargs):
        calls.append(
            {
                "fanout_count": payload.get("fanout_count"),
                "fanout_index": payload.get("fanout_index"),
                "model_id": payload.get("model_id"),
                "model_ids": list(payload.get("model_ids") or []),
            }
        )
        return {
            "ok": True,
            "result": {"reply": "ok"},
            "state": state,
        }, None

    monkeypatch.setattr(message_sender, "handle_call_flow_action", fake_handle_call_flow_action)
    response, action_error = message_sender.handle_chat_message_send_action(
        None,
        {"flow": "send"},
        "chat.send",
        {"message": "hello", "model_ids": ["model.beta"]},
        state,
        store=None,
        runtime_theme=None,
        raise_on_error=False,
    )

    assert action_error is None
    assert calls == [
        {
            "fanout_count": 1,
            "fanout_index": 1,
            "model_id": "model.beta",
            "model_ids": ["model.beta"],
        }
    ]
    assert response["result"] == {"reply": "ok"}


def test_chat_message_send_rejects_invalid_model_ids_payload_shape() -> None:
    state = _sample_state()
    with pytest.raises(Namel3ssError) as err:
        message_sender.handle_chat_message_send_action(
            None,
            {"flow": "send"},
            "chat.send",
            {"message": "hello", "model_ids": {"bad": "shape"}},
            state,
            store=None,
            runtime_theme=None,
            raise_on_error=False,
        )
    assert "model_ids must be text or a list of text ids" in str(err.value)


def _sample_state() -> dict:
    return {
        "chat": {
            "messages": [],
            "threads": [{"id": "thread.main", "name": "Main"}],
            "active_thread": "thread.main",
            "models": [
                {"id": "model.beta", "name": "Beta"},
                {"id": "model.alpha", "name": "Alpha"},
            ],
            "active_models": ["model.beta", "model.alpha"],
            "composer_state": {
                "attachments": ["upload.a"],
                "draft": "Need docs",
                "tools": ["web.lookup"],
                "web_search": True,
            },
        }
    }
