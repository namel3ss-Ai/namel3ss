from __future__ import annotations

from namel3ss.runtime.capabilities.registry import capability_pack_names, list_capability_packs
from namel3ss.runtime.capabilities.validation import parse_capability_pack_requests, validate_capability_packs
from namel3ss.runtime.contracts.runtime_schema import RUNTIME_UI_CONTRACT_VERSION


def test_capability_registry_is_stable_and_sorted() -> None:
    first = list_capability_packs()
    second = list_capability_packs()
    assert first == second
    assert capability_pack_names() == ("email_sender", "http_client", "sql_database")
    assert [pack.name for pack in first] == sorted(pack.name for pack in first)


def test_capability_validation_unknown_pack_is_explicit() -> None:
    requests = parse_capability_pack_requests(["capability.unknown_pack@1.0.0"])
    result = validate_capability_packs(
        permissions=("http", "files", "secrets", "third_party_apis"),
        runtime_contract_version=RUNTIME_UI_CONTRACT_VERSION,
        requests=requests,
    )
    assert result.packs == ()
    assert result.diagnostics
    assert result.diagnostics[0]["stable_code"].startswith("runtime.runtime_internal.capability_unknown.")


def test_capability_validation_version_mismatch_is_explicit() -> None:
    requests = parse_capability_pack_requests(["capability.http_client@9.9.9"])
    result = validate_capability_packs(
        permissions=("http",),
        runtime_contract_version=RUNTIME_UI_CONTRACT_VERSION,
        requests=requests,
    )
    assert result.packs == ()
    assert result.diagnostics
    assert result.diagnostics[0]["stable_code"].startswith("runtime.runtime_internal.capability_version_mismatch.")


def test_capability_validation_missing_permissions_is_explicit() -> None:
    requests = parse_capability_pack_requests(["capability.email_sender"])
    result = validate_capability_packs(
        permissions=("third_party_apis",),
        runtime_contract_version=RUNTIME_UI_CONTRACT_VERSION,
        requests=requests,
    )
    assert result.packs == ()
    assert result.diagnostics
    assert result.diagnostics[0]["category"] == "policy_denied"
    assert result.diagnostics[0]["stable_code"].startswith("runtime.policy_denied.capability_permission.")
