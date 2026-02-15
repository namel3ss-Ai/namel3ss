from __future__ import annotations

from types import SimpleNamespace

from namel3ss.config.model import AppConfig
from namel3ss.runtime.capabilities.contract_fields import attach_capability_contract_fields


def _studio_ui() -> dict:
    return {
        "ok": True,
        "mode": "studio",
        "pages": [
            {
                "name": "home",
                "slug": "home",
                "elements": [{"type": "text", "text": "hello"}],
            }
        ],
    }


def test_attach_capability_contract_fields_adds_metadata_and_ui_element() -> None:
    config = AppConfig()
    program = SimpleNamespace(capabilities=("http", "files", "third_party_apis", "secrets"))
    response = {
        "ok": True,
        "state": {},
        "ui": _studio_ui(),
    }
    enriched = attach_capability_contract_fields(response, program_ir=program, config=config)
    assert isinstance(enriched.get("capabilities_enabled"), list)
    assert [item.get("name") for item in enriched["capabilities_enabled"]] == [
        "email_sender",
        "http_client",
        "sql_database",
    ]
    assert enriched["capability_versions"] == {
        "email_sender": "1.0.0",
        "http_client": "1.0.0",
        "sql_database": "1.0.0",
    }
    ui = enriched["ui"]
    assert ui["capabilities_enabled"] == enriched["capabilities_enabled"]
    assert ui["capability_versions"] == enriched["capability_versions"]
    assert ui["pages"][0]["elements"][0]["type"] == "capabilities"


def test_attach_capability_contract_fields_blocks_invalid_explicit_request() -> None:
    config = AppConfig()
    config.tool_packs.enabled_packs = ["capability.unknown_pack@1.0.0"]
    program = SimpleNamespace(capabilities=("http",))
    response = {
        "ok": True,
        "state": {},
        "ui": _studio_ui(),
    }
    enriched = attach_capability_contract_fields(response, program_ir=program, config=config)
    assert enriched["ok"] is False
    assert isinstance(enriched.get("runtime_error"), dict)
    assert str(enriched["runtime_error"].get("stable_code", "")).startswith(
        "runtime.runtime_internal.capability_unknown."
    )


def test_attach_capability_contract_fields_hides_viewer_in_production_mode() -> None:
    config = AppConfig()
    program = SimpleNamespace(capabilities=("http", "files"))
    response = {
        "ok": True,
        "state": {},
        "ui": {
            "ok": True,
            "mode": "production",
            "diagnostics_enabled": True,
            "pages": [
                {
                    "name": "home",
                    "slug": "home",
                    "elements": [{"type": "text", "text": "hello"}],
                }
            ],
        },
    }
    enriched = attach_capability_contract_fields(response, program_ir=program, config=config)
    ui = enriched["ui"]
    assert ui["capabilities_enabled"] == enriched["capabilities_enabled"]
    assert ui["capability_versions"] == enriched["capability_versions"]
    assert ui["pages"][0]["elements"][0]["type"] == "text"
