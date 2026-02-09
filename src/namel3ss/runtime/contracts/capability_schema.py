from __future__ import annotations

from namel3ss.runtime.contracts.schema_model import ContractField, ContractSchema


CAPABILITY_PACK_SCHEMA = ContractSchema(
    name="capability_pack",
    notes="Versioned capability pack metadata exposed to Studio and headless clients.",
    additional_fields=True,
    fields=(
        ContractField("name", "string"),
        ContractField("version", "string"),
        ContractField("provided_actions", "array", required=False, item_type="string", default=()),
        ContractField("required_permissions", "array", required=False, item_type="string", default=()),
        ContractField("runtime_bindings", "object", required=False, default=None),
        ContractField("effect_capabilities", "array", required=False, item_type="string", default=()),
        ContractField("contract_version", "string"),
        ContractField("purity", "string"),
        ContractField("replay_mode", "string"),
    ),
)

CAPABILITY_USAGE_SCHEMA = ContractSchema(
    name="capability_usage",
    notes="Deterministic capability usage entries emitted into run artifacts for replay/audit.",
    additional_fields=True,
    fields=(
        ContractField("pack_name", "string"),
        ContractField("pack_version", "string"),
        ContractField("action", "string"),
        ContractField("capability", "string"),
        ContractField("status", "string"),
        ContractField("reason", "string", required=False, default=None),
        ContractField("purity", "string"),
        ContractField("replay_mode", "string"),
        ContractField("required_permissions", "array", required=False, item_type="string", default=()),
    ),
)


__all__ = ["CAPABILITY_PACK_SCHEMA", "CAPABILITY_USAGE_SCHEMA"]
