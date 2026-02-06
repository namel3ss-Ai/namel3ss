from __future__ import annotations

from namel3ss.runtime.ui_api.contracts import (
    UI_API_VERSION,
    build_action_result_payload,
    build_ui_actions_payload,
    build_ui_manifest_payload,
    build_ui_state_payload,
)


def test_manifest_contract_collects_components_and_flows() -> None:
    manifest = {
        "ok": True,
        "pages": [
            {
                "name": "home",
                "elements": [
                    {"type": "button"},
                    {"type": "form", "children": [{"type": "input"}]},
                ],
            }
        ],
        "actions": {
            "page.home.button.send": {"type": "call_flow", "flow": "echo"},
            "page.home.form.submit": {"type": "submit_form", "record": "User"},
        },
        "theme": {"current": "light"},
    }

    payload = build_ui_manifest_payload(manifest, revision="abc123")

    assert payload["ok"] is True
    assert payload["api_version"] == UI_API_VERSION
    assert payload["manifest"]["flows"] == ["echo"]
    assert payload["manifest"]["components"] == ["button", "form", "input"]
    assert payload["revision"] == "abc123"


def test_actions_contract_is_stable_list() -> None:
    manifest = {
        "ok": True,
        "actions": {
            "b.action": {"type": "submit_form", "record": "User"},
            "a.action": {"type": "call_flow", "flow": "run"},
        },
    }

    payload = build_ui_actions_payload(manifest)

    assert payload["ok"] is True
    assert [item["id"] for item in payload["actions"]] == ["a.action", "b.action"]


def test_state_and_action_result_contracts() -> None:
    state_payload = build_ui_state_payload({"ok": True, "state": {"counter": 1, "page": "home"}, "revision": "rev1"})
    assert state_payload["state"]["current_page"] == "home"
    assert state_payload["state"]["values"] == {"counter": 1, "page": "home"}
    assert state_payload["revision"] == "rev1"

    action_payload = build_action_result_payload({"ok": True, "state": {"counter": 2}, "result": "ok", "revision": "rev2"})
    assert action_payload["success"] is True
    assert action_payload["new_state"] == {"counter": 2}
    assert action_payload["result"] == "ok"
    assert action_payload["revision"] == "rev2"


def test_contract_error_payloads_are_explicit() -> None:
    manifest_error = build_ui_manifest_payload({"ok": False, "error": {"message": "bad"}})
    assert manifest_error["ok"] is False
    assert manifest_error["error"]["message"] == "bad"

    action_error = build_action_result_payload({"ok": False, "error": {"message": "blocked"}})
    assert action_error["ok"] is False
    assert action_error["success"] is False
    assert action_error["message"] == "blocked"
