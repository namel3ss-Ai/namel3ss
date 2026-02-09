from __future__ import annotations

from namel3ss.runtime.contracts.action_schema import (
    HEADLESS_ACTION_RESPONSE_SCHEMA,
    UI_ACTION_RESULT_SCHEMA,
)
from namel3ss.runtime.contracts.capability_schema import CAPABILITY_PACK_SCHEMA, CAPABILITY_USAGE_SCHEMA
from namel3ss.runtime.contracts.schema_model import ContractField, ContractSchema, schema_to_payload
from namel3ss.runtime.contracts.ui_manifest_schema import (
    AUDIT_BUNDLE_SCHEMA,
    AUDIT_POLICY_STATUS_SCHEMA,
    CONTRACT_WARNING_SCHEMA,
    MANIFEST_PAGE_SCHEMA,
    MIGRATION_STATUS_SCHEMA,
    PERSISTENCE_BACKEND_SCHEMA,
    RAG_STATE_SCHEMA,
    REPRO_BUNDLE_SCHEMA,
    RETRIEVAL_PLAN_SCHEMA,
    RETRIEVAL_STATE_SCHEMA,
    RETRIEVAL_TRACE_ENTRY_SCHEMA,
    RUN_DIFF_CHANGE_SCHEMA,
    RUN_DIFF_SCHEMA,
    RUN_ARTIFACT_SCHEMA,
    RUNTIME_ERROR_SCHEMA,
    TRUST_SCORE_DETAILS_SCHEMA,
    UI_MANIFEST_SCHEMA,
    UI_STATE_SCHEMA,
)
from namel3ss.runtime.spec_version import NAMEL3SS_SPEC_VERSION, RUNTIME_SPEC_VERSION


RUNTIME_UI_CONTRACT_VERSION = "runtime-ui@1"

HEADLESS_UI_RESPONSE_SCHEMA = ContractSchema(
    name="headless_ui_response",
    notes="Response contract for GET /api/v1/ui.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="v1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("manifest", "object", required=False, ref="ui_manifest"),
        ContractField("hash", "string", required=False, default=None),
        ContractField("revision", "string", required=False, default=None),
        ContractField("state", "object", required=False, ref="ui_state_response"),
        ContractField("actions", "object", required=False, default=None),
        ContractField("error", "object", required=False, default=None),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
        ContractField("capabilities_enabled", "array", required=False, item_ref="capability_pack", default=()),
        ContractField("capability_versions", "object", required=False, default=None),
        ContractField("persistence_backend", "object", required=False, ref="persistence_backend"),
        ContractField("state_schema_version", "string", required=False, default=None),
        ContractField("migration_status", "object", required=False, ref="migration_status"),
        ContractField("run_artifact", "object", required=False, ref="run_artifact"),
        ContractField("audit_bundle", "object", required=False, ref="audit_bundle"),
        ContractField("audit_policy_status", "object", required=False, ref="audit_policy_status"),
        ContractField("workspace_id", "string", required=False, default=None),
        ContractField("session_id", "string", required=False, default=None),
        ContractField("run_diff", "object", required=False, ref="run_diff"),
        ContractField("repro_bundle", "object", required=False, ref="repro_bundle"),
        ContractField("run_history", "array", required=False, item_type="string", default=()),
        ContractField("contract_warnings", "array", required=False, item_ref="contract_warning", default=()),
    ),
)

UI_MANIFEST_RESPONSE_SCHEMA = ContractSchema(
    name="ui_manifest_response",
    notes="Response contract for GET /api/ui/manifest.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("manifest", "object", required=True, ref="ui_manifest"),
        ContractField("theme", "object", required=False, default=None),
        ContractField("revision", "string", required=False, default=None),
        ContractField("error", "object", required=False, default=None),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
        ContractField("capabilities_enabled", "array", required=False, item_ref="capability_pack", default=()),
        ContractField("capability_versions", "object", required=False, default=None),
        ContractField("persistence_backend", "object", required=False, ref="persistence_backend"),
        ContractField("state_schema_version", "string", required=False, default=None),
        ContractField("migration_status", "object", required=False, ref="migration_status"),
        ContractField("run_artifact", "object", required=False, ref="run_artifact"),
        ContractField("audit_bundle", "object", required=False, ref="audit_bundle"),
        ContractField("audit_policy_status", "object", required=False, ref="audit_policy_status"),
        ContractField("workspace_id", "string", required=False, default=None),
        ContractField("session_id", "string", required=False, default=None),
        ContractField("run_diff", "object", required=False, ref="run_diff"),
        ContractField("repro_bundle", "object", required=False, ref="repro_bundle"),
        ContractField("run_history", "array", required=False, item_type="string", default=()),
    ),
)

UI_ACTIONS_RESPONSE_SCHEMA = ContractSchema(
    name="ui_actions_response",
    notes="Response contract for GET /api/ui/actions.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("actions", "array", required=True, item_type="object", default=()),
        ContractField("warnings", "array", required=False, item_type="object", default=()),
        ContractField("revision", "string", required=False, default=None),
        ContractField("error", "object", required=False, default=None),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
        ContractField("workspace_id", "string", required=False, default=None),
        ContractField("session_id", "string", required=False, default=None),
    ),
)

UI_STATE_RESPONSE_SCHEMA = ContractSchema(
    name="ui_state_response",
    notes="Response contract for GET /api/ui/state.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("state", "object", ref="ui_state"),
        ContractField("revision", "string", required=False, default=None),
        ContractField("error", "object", required=False, default=None),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
    ),
)

RUN_RESPONSE_SCHEMA = ContractSchema(
    name="run_response",
    notes="Forward-compatible aggregate envelope used by SDK examples.",
    additional_fields=True,
    fields=(
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("ui", "object", required=False, ref="headless_ui_response"),
        ContractField("state", "object", required=False, ref="ui_state"),
        ContractField("result", "object", required=False, ref="headless_action_response"),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("capabilities_enabled", "array", required=False, item_ref="capability_pack", default=()),
        ContractField("capability_versions", "object", required=False, default=None),
        ContractField("persistence_backend", "object", required=False, ref="persistence_backend"),
        ContractField("state_schema_version", "string", required=False, default=None),
        ContractField("migration_status", "object", required=False, ref="migration_status"),
        ContractField("run_artifact", "object", required=False, ref="run_artifact"),
        ContractField("audit_bundle", "object", required=False, ref="audit_bundle"),
        ContractField("audit_policy_status", "object", required=False, ref="audit_policy_status"),
        ContractField("workspace_id", "string", required=False, default=None),
        ContractField("session_id", "string", required=False, default=None),
        ContractField("run_diff", "object", required=False, ref="run_diff"),
        ContractField("repro_bundle", "object", required=False, ref="repro_bundle"),
        ContractField("run_history", "array", required=False, item_type="string", default=()),
    ),
)

RUNTIME_CONTRACT_SCHEMAS: dict[str, ContractSchema] = {
    "runtime_error": RUNTIME_ERROR_SCHEMA,
    "contract_warning": CONTRACT_WARNING_SCHEMA,
    "capability_pack": CAPABILITY_PACK_SCHEMA,
    "capability_usage": CAPABILITY_USAGE_SCHEMA,
    "persistence_backend": PERSISTENCE_BACKEND_SCHEMA,
    "migration_status": MIGRATION_STATUS_SCHEMA,
    "audit_policy_status": AUDIT_POLICY_STATUS_SCHEMA,
    "audit_bundle": AUDIT_BUNDLE_SCHEMA,
    "run_diff_change": RUN_DIFF_CHANGE_SCHEMA,
    "run_diff": RUN_DIFF_SCHEMA,
    "repro_bundle": REPRO_BUNDLE_SCHEMA,
    "run_artifact": RUN_ARTIFACT_SCHEMA,
    "retrieval_trace_entry": RETRIEVAL_TRACE_ENTRY_SCHEMA,
    "retrieval_plan": RETRIEVAL_PLAN_SCHEMA,
    "trust_score_details": TRUST_SCORE_DETAILS_SCHEMA,
    "retrieval_state": RETRIEVAL_STATE_SCHEMA,
    "rag_state": RAG_STATE_SCHEMA,
    "ui_state": UI_STATE_SCHEMA,
    "manifest_page": MANIFEST_PAGE_SCHEMA,
    "ui_manifest": UI_MANIFEST_SCHEMA,
    "headless_ui_response": HEADLESS_UI_RESPONSE_SCHEMA,
    "headless_action_response": HEADLESS_ACTION_RESPONSE_SCHEMA,
    "ui_manifest_response": UI_MANIFEST_RESPONSE_SCHEMA,
    "ui_actions_response": UI_ACTIONS_RESPONSE_SCHEMA,
    "ui_state_response": UI_STATE_RESPONSE_SCHEMA,
    "ui_action_result": UI_ACTION_RESULT_SCHEMA,
    "run_response": RUN_RESPONSE_SCHEMA,
}

RUNTIME_CONTRACT_SCHEMA_ORDER: tuple[str, ...] = (
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
)


def runtime_contract_schema_catalog() -> dict[str, object]:
    schema_map: dict[str, object] = {}
    for name in RUNTIME_CONTRACT_SCHEMA_ORDER:
        schema = RUNTIME_CONTRACT_SCHEMAS[name]
        schema_map[name] = schema_to_payload(schema)
    return {
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "spec_version": NAMEL3SS_SPEC_VERSION,
        "runtime_spec_version": RUNTIME_SPEC_VERSION,
        "schema_version": "runtime_contract_schema@1",
        "schemas": schema_map,
    }


__all__ = [
    "HEADLESS_ACTION_RESPONSE_SCHEMA",
    "HEADLESS_UI_RESPONSE_SCHEMA",
    "RUNTIME_CONTRACT_SCHEMAS",
    "RUNTIME_CONTRACT_SCHEMA_ORDER",
    "RUNTIME_UI_CONTRACT_VERSION",
    "RUN_RESPONSE_SCHEMA",
    "UI_ACTIONS_RESPONSE_SCHEMA",
    "UI_ACTION_RESULT_SCHEMA",
    "UI_MANIFEST_RESPONSE_SCHEMA",
    "UI_STATE_RESPONSE_SCHEMA",
    "runtime_contract_schema_catalog",
]
