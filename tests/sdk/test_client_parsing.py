from __future__ import annotations

import json
from pathlib import Path


def test_official_sdk_package_files_exist() -> None:
    package_json = Path("packages/namel3ss-client/package.json")
    index_ts = Path("packages/namel3ss-client/src/index.ts")
    types_ts = Path("packages/namel3ss-client/src/types.ts")
    validate_ts = Path("packages/namel3ss-client/src/validate.ts")
    schema_json = Path("packages/namel3ss-client/src/runtime_contract_schema.json")

    assert package_json.exists()
    assert index_ts.exists()
    assert types_ts.exists()
    assert validate_ts.exists()
    assert schema_json.exists()

    package = json.loads(package_json.read_text(encoding="utf-8"))
    assert package["name"] == "@namel3ss/client"
    assert package["main"] == "src/index.ts"
    assert package["types"] == "src/types.ts"


def test_sdk_exposes_strict_headless_calls() -> None:
    source = Path("packages/namel3ss-client/src/index.ts").read_text(encoding="utf-8")
    for token in [
        "class Namel3ssClient",
        "getUi",
        "getManifest",
        "getState",
        "getActions",
        "runAction",
        "/api/${HEADLESS_API_VERSION}/ui",
        "/api/${HEADLESS_API_VERSION}/actions/",
        "validateHeadlessUiResponse",
        "validateHeadlessActionResponse",
        "runtime_error",
        "contract_warnings",
    ]:
        assert token in source


def test_sdk_validator_uses_generated_runtime_schema() -> None:
    source = Path("packages/namel3ss-client/src/validate.ts").read_text(encoding="utf-8")
    assert 'from "./runtime_contract_schema.json"' in source
    for token in [
        "validatePayload",
        "validateHeadlessUiResponse",
        "validateHeadlessActionResponse",
        "schema.type_mismatch",
        "schema.missing_field",
    ]:
        assert token in source


def test_sdk_types_include_retrieval_plan_trace_and_trust_details() -> None:
    source = Path("packages/namel3ss-client/src/types.ts").read_text(encoding="utf-8")
    for token in [
        "interface RetrievalTraceEntry",
        "interface RetrievalPlan",
        "interface TrustScoreDetails",
        "interface RetrievalState",
        "retrieval_plan",
        "retrieval_trace",
        "trust_score_details",
    ]:
        assert token in source


def test_sdk_types_include_audit_artifact_contracts() -> None:
    source = Path("packages/namel3ss-client/src/types.ts").read_text(encoding="utf-8")
    for token in [
        "interface AuditPolicyStatus",
        "interface AuditBundle",
        "interface RunArtifact",
        "run_artifact",
        "audit_bundle",
        "audit_policy_status",
    ]:
        assert token in source


def test_sdk_types_include_persistence_and_migration_contracts() -> None:
    source = Path("packages/namel3ss-client/src/types.ts").read_text(encoding="utf-8")
    for token in [
        "interface PersistenceBackend",
        "interface MigrationStatus",
        "persistence_backend",
        "state_schema_version",
        "migration_status",
    ]:
        assert token in source


def test_sdk_types_include_capability_contracts() -> None:
    source = Path("packages/namel3ss-client/src/types.ts").read_text(encoding="utf-8")
    for token in [
        "interface CapabilityPack",
        "interface CapabilityUsage",
        "capabilities_enabled",
        "capability_versions",
        "capability_usage",
    ]:
        assert token in source
