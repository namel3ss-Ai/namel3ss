from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.contracts.runtime_schema import runtime_contract_schema_catalog
from namel3ss.runtime.server.headless_api import build_headless_action_payload, build_headless_ui_payload
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION
from namel3ss.runtime.ui_api.contracts import (
    build_action_result_payload,
    build_ui_actions_payload,
    build_ui_manifest_payload,
    build_ui_state_payload,
)


REQUIRED_SPEC_DOCS = (
    "docs/spec/namel3ss_spec.md",
    "docs/spec/grammar.md",
    "docs/spec/runtime_semantics.md",
    "docs/spec/retrieval_semantics.md",
    "docs/spec/contracts.md",
    "docs/spec/errors.md",
    "docs/governance/compatibility.md",
    "docs/governance/deprecations.md",
    "docs/governance/contributing.md",
)


def test_governance_spec_documents_exist() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for relative in REQUIRED_SPEC_DOCS:
        target = repo_root / relative
        assert target.exists(), f"Missing governance/spec document: {relative}"


def test_headless_payloads_include_runtime_spec_versions() -> None:
    ui_payload = build_headless_ui_payload(manifest={"ok": True, "pages": []})
    assert ui_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert ui_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION

    action_payload, status = build_headless_action_payload(action_id="page.home.button.run", action_response={"ok": True})
    assert status == 200
    assert action_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert action_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION


def test_ui_contract_payloads_include_runtime_spec_versions() -> None:
    manifest_payload = build_ui_manifest_payload({"ok": True, "pages": [], "actions": {}})
    assert manifest_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert manifest_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION

    actions_payload = build_ui_actions_payload({"ok": True, "actions": {}})
    assert actions_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert actions_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION

    state_payload = build_ui_state_payload({"ok": True, "state": {}})
    assert state_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert state_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION

    action_payload = build_action_result_payload({"ok": True, "state": {}})
    assert action_payload["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert action_payload["runtime_spec_version"] == RUNTIME_SPEC_VERSION


def test_runtime_contract_catalog_declares_spec_versions() -> None:
    catalog = runtime_contract_schema_catalog()
    assert catalog["spec_version"] == NAMEL3SS_SPEC_VERSION
    assert catalog["runtime_spec_version"] == RUNTIME_SPEC_VERSION
