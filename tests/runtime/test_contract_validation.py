from __future__ import annotations

import json
from pathlib import Path

from namel3ss.runtime.contracts.runtime_schema import (
    RUNTIME_UI_CONTRACT_VERSION,
    runtime_contract_schema_catalog,
)
from namel3ss.runtime.contracts.validate_payload import (
    validate_contract_payload,
    validate_contract_payload_for_mode,
    with_contract_warnings,
)
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION


def test_runtime_contract_catalog_is_stable() -> None:
    payload = runtime_contract_schema_catalog()
    assert payload["contract_version"] == RUNTIME_UI_CONTRACT_VERSION
    assert payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION
    assert payload["schema_version"] == "runtime_contract_schema@1"
    schema_names = list(payload["schemas"].keys())
    assert schema_names == [
        "runtime_error",
        "contract_warning",
        "capability_pack",
        "capability_usage",
        "persistence_backend",
        "migration_status",
        "audit_policy_status",
        "audit_bundle",
        "run_diff_change",
        "run_diff",
        "repro_bundle",
        "run_artifact",
        "retrieval_trace_entry",
        "retrieval_plan",
        "trust_score_details",
        "retrieval_state",
        "rag_state",
        "ui_state",
        "manifest_page",
        "ui_manifest",
        "headless_ui_response",
        "headless_action_response",
        "ui_manifest_response",
        "ui_actions_response",
        "ui_state_response",
        "ui_action_result",
        "run_response",
    ]


def test_validate_headless_ui_payload_detects_missing_contract_version() -> None:
    payload = {
        "ok": True,
        "api_version": "v1",
        "manifest": {"pages": []},
        "hash": "a" * 64,
    }
    warnings = validate_contract_payload(payload, schema_name="headless_ui_response")
    assert any(entry["code"] == "schema.missing_field" for entry in warnings)
    assert any(entry["path"] == "$.contract_version" for entry in warnings)


def test_validate_headless_action_payload_is_deterministic() -> None:
    payload = {
        "ok": True,
        "api_version": "v1",
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "spec_version": NAMEL3SS_SPEC_VERSION,
        "runtime_spec_version": RUNTIME_SPEC_VERSION,
        "action_id": "page.home.button.run",
        "state": {"uploads": {}, "ingestion": {}, "retrieval": {}},
    }
    one = validate_contract_payload(payload, schema_name="headless_action_response")
    two = validate_contract_payload(payload, schema_name="headless_action_response")
    assert one == two


def test_validate_contract_payload_for_mode_only_in_studio_or_diagnostics() -> None:
    payload = {"ok": True, "api_version": "v1"}
    production_warnings = validate_contract_payload_for_mode(
        payload,
        schema_name="headless_ui_response",
        ui_mode="production",
        diagnostics_enabled=False,
    )
    assert production_warnings == []

    studio_warnings = validate_contract_payload_for_mode(
        payload,
        schema_name="headless_ui_response",
        ui_mode="studio",
        diagnostics_enabled=False,
    )
    assert studio_warnings
    assert any(entry["path"] == "$.contract_version" for entry in studio_warnings)


def test_with_contract_warnings_does_not_mutate_payload() -> None:
    payload = {
        "ok": True,
        "api_version": "v1",
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "spec_version": NAMEL3SS_SPEC_VERSION,
        "runtime_spec_version": RUNTIME_SPEC_VERSION,
    }
    warnings = [{"code": "schema.missing_field", "path": "$.manifest", "message": "Missing required field 'manifest'."}]
    out = with_contract_warnings(payload, warnings)
    assert isinstance(out, dict)
    assert "contract_warnings" not in payload
    assert out["contract_warnings"] == warnings


def test_generated_sdk_schema_matches_runtime_catalog() -> None:
    expected = runtime_contract_schema_catalog()
    generated_path = Path("packages/namel3ss-client/src/runtime_contract_schema.json")
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    assert generated == expected
