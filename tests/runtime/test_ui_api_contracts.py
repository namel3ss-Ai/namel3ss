from __future__ import annotations

from namel3ss.runtime.ui_api.contracts import (
    UI_API_VERSION,
    build_action_result_payload,
    build_ui_actions_payload,
    build_ui_manifest_payload,
    build_ui_state_payload,
)
from namel3ss.runtime.contracts.runtime_schema import RUNTIME_UI_CONTRACT_VERSION
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION


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
        "diagnostics_enabled": True,
    }

    payload = build_ui_manifest_payload(manifest, revision="abc123")

    assert payload["ok"] is True
    assert payload["api_version"] == UI_API_VERSION
    assert payload["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
    assert payload["manifest"]["flows"] == ["echo"]
    assert payload["manifest"]["components"] == ["button", "form", "input"]
    assert payload["manifest"]["diagnostics_enabled"] is True
    assert payload["revision"] == "abc123"


def test_manifest_contract_collects_components_from_layout_pages() -> None:
    manifest = {
        "ok": True,
        "pages": [
            {
                "name": "chat",
                "layout": {
                    "header": [{"type": "title"}],
                    "sidebar_left": [{"type": "list"}],
                    "main": [{"type": "chat", "children": [{"type": "messages"}, {"type": "composer"}]}],
                    "drawer_right": [],
                    "footer": [{"type": "text"}],
                },
            }
        ],
        "actions": {
            "page.chat.composer.send": {"type": "call_flow", "flow": "send"},
        },
    }

    payload = build_ui_manifest_payload(manifest)
    assert payload["manifest"]["components"] == ["chat", "composer", "list", "messages", "text", "title"]


def test_manifest_and_actions_contract_include_warnings() -> None:
    warning = {
        "code": "copy.missing_page_title",
        "message": "Add a page title.",
        "fix": "Declare a title at the top of the page.",
        "path": "page.home",
        "line": 10,
        "column": 3,
        "category": "copy",
        "enforced_at": None,
    }
    manifest = {
        "ok": True,
        "pages": [{"name": "home", "elements": []}],
        "actions": {"page.home.button.run": {"type": "call_flow", "flow": "run"}},
        "warnings": [warning],
    }

    manifest_payload = build_ui_manifest_payload(manifest)
    assert manifest_payload["manifest"]["warnings"] == [warning]

    actions_payload = build_ui_actions_payload(manifest)
    assert actions_payload["warnings"] == [warning]


def test_manifest_contract_includes_upload_requests_when_available() -> None:
    manifest = {
        "ok": True,
        "pages": [{"name": "home", "elements": [{"type": "upload", "name": "receipt"}]}],
        "actions": {"page.home.upload.receipt": {"type": "upload_select", "name": "receipt"}},
        "upload_requests": [
            {
                "name": "receipt",
                "accept": ["application/pdf"],
                "multiple": False,
                "required": True,
                "label": "Upload receipt",
                "preview": True,
            }
        ],
    }
    payload = build_ui_manifest_payload(manifest)
    assert payload["manifest"]["upload_requests"] == manifest["upload_requests"]


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
    assert payload["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
    assert [item["id"] for item in payload["actions"]] == ["a.action", "b.action"]


def test_actions_contract_preserves_upload_action_metadata() -> None:
    manifest = {
        "ok": True,
        "actions": {
            "page.home.upload.receipt": {
                "type": "upload_select",
                "name": "receipt",
                "multiple": True,
                "required": True,
            },
            "page.home.upload.receipt.clear": {
                "type": "upload_clear",
                "name": "receipt",
            },
        },
    }

    payload = build_ui_actions_payload(manifest)
    action_map = {entry["id"]: entry for entry in payload["actions"]}
    select_action = action_map["page.home.upload.receipt"]
    clear_action = action_map["page.home.upload.receipt.clear"]

    assert select_action["name"] == "receipt"
    assert select_action["multiple"] is True
    assert select_action["required"] is True
    assert clear_action["name"] == "receipt"


def test_state_and_action_result_contracts() -> None:
    state_payload = build_ui_state_payload({"ok": True, "state": {"counter": 1, "page": "home"}, "revision": "rev1"})
    assert state_payload["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert state_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert state_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
    assert state_payload["state"]["current_page"] == "home"
    assert state_payload["state"]["values"] == {"counter": 1, "page": "home"}
    assert state_payload["revision"] == "rev1"

    action_payload = build_action_result_payload({"ok": True, "state": {"counter": 2}, "result": "ok", "revision": "rev2"})
    assert action_payload["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert action_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert action_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
    assert action_payload["success"] is True
    assert action_payload["new_state"] == {"counter": 2}
    assert action_payload["result"] == "ok"
    assert action_payload["revision"] == "rev2"


def test_contract_error_payloads_are_explicit() -> None:
    manifest_error = build_ui_manifest_payload({"ok": False, "error": {"message": "bad"}})
    assert manifest_error["ok"] is False
    assert manifest_error["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert manifest_error["error"]["message"] == "bad"

    action_error = build_action_result_payload({"ok": False, "error": {"message": "blocked"}})
    assert action_error["ok"] is False
    assert action_error["success"] is False
    assert action_error["message"] == "blocked"


def test_action_contract_preserves_runtime_error_payload() -> None:
    runtime_error = {
        "category": "policy_denied",
        "message": "Policy blocked this action.",
        "hint": "Update policy rules.",
        "origin": "policy",
        "stable_code": "runtime.policy_denied",
    }
    payload = build_action_result_payload(
        {
            "ok": False,
            "error": {"message": "blocked"},
            "runtime_error": runtime_error,
            "runtime_errors": [runtime_error],
        }
    )
    assert payload["runtime_error"] == runtime_error
    assert payload["runtime_errors"] == [runtime_error]
