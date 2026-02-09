from __future__ import annotations

from namel3ss.runtime.contracts.schema_model import ContractField, ContractSchema


HEADLESS_ACTION_RESPONSE_SCHEMA = ContractSchema(
    name="headless_action_response",
    notes="Response contract for POST /api/v1/actions/<action_id>.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="v1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("action_id", "string"),
        ContractField("state", "object", required=False, ref="rag_state"),
        ContractField("manifest", "object", required=False, ref="ui_manifest"),
        ContractField("hash", "string", required=False, default=None),
        ContractField("messages", "array", required=False, item_type="object", default=()),
        ContractField("result", "any", required=False, default=None),
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

UI_ACTION_RESULT_SCHEMA = ContractSchema(
    name="ui_action_result",
    notes="Response contract for POST /api/ui/action.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean"),
        ContractField("api_version", "string", default="1"),
        ContractField("contract_version", "string"),
        ContractField("spec_version", "string"),
        ContractField("runtime_spec_version", "string"),
        ContractField("success", "boolean"),
        ContractField("new_state", "object", ref="rag_state"),
        ContractField("message", "string"),
        ContractField("result", "any", required=False, default=None),
        ContractField("revision", "string", required=False, default=None),
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


__all__ = [
    "HEADLESS_ACTION_RESPONSE_SCHEMA",
    "UI_ACTION_RESULT_SCHEMA",
]
