from __future__ import annotations

from pathlib import Path

from namel3ss.errors.guidance import build_guidance_message


def missing_config_message(path: str) -> str:
    return build_guidance_message(
        what="Federation config is missing.",
        why=f"Expected {path}.",
        fix="Create federation.yaml and add at least one contract.",
        example="contracts:\n  - source_tenant: acme\n    target_tenant: beta\n    flow_name: get_customer_info",
    )


def invalid_config_message(path: Path, detail: str) -> str:
    return build_guidance_message(
        what="Federation config is invalid.",
        why=f"{path.as_posix()} could not be parsed: {detail}.",
        fix="Fix federation.yaml and retry.",
        example="contracts:\n  - source_tenant: acme\n    target_tenant: beta\n    flow_name: get_customer_info",
    )


def invalid_usage_message(path: Path) -> str:
    return build_guidance_message(
        what="Federation usage log is invalid.",
        why=f"{path.as_posix()} contains malformed JSON lines.",
        fix="Repair or clear the usage file.",
        example="rm .namel3ss/federation_usage.jsonl",
    )


def duplicate_contract_message(contract_id: str) -> str:
    return build_guidance_message(
        what=f"Contract '{contract_id}' is duplicated.",
        why="Each source/target/flow combination must be unique.",
        fix="Keep one contract per source, target, and flow.",
        example="n3 federation remove-contract acme beta get_customer_info",
    )


def missing_contract_message(contract_id: str) -> str:
    return build_guidance_message(
        what=f"Federation contract '{contract_id}' was not found.",
        why="Cross-tenant calls need an explicit contract.",
        fix="Add the contract first.",
        example="n3 federation add-contract acme beta get_customer_info",
    )


def missing_field_message(field_name: str) -> str:
    return build_guidance_message(
        what=f"{field_name} is required.",
        why="Federation contracts need source_tenant, target_tenant, and flow_name.",
        fix="Set the missing field.",
        example="source_tenant: acme",
    )


def invalid_schema_message(detail: str) -> str:
    return build_guidance_message(
        what="Contract schema is invalid.",
        why=detail,
        fix="Use field:type entries.",
        example="input_schema:\n  customer_id: number",
    )


def invalid_auth_message() -> str:
    return build_guidance_message(
        what="Contract auth is invalid.",
        why="auth must be a map of key/value strings.",
        fix="Set auth fields as key/value.",
        example="auth:\n  client_id: acme_beta_client\n  token: abc123",
    )


def invalid_rate_limit_message() -> str:
    return build_guidance_message(
        what="Contract rate_limit is invalid.",
        why="calls_per_minute must be a positive integer.",
        fix="Set a valid positive integer.",
        example="rate_limit:\n  calls_per_minute: 60",
    )


def rate_limit_exceeded_message(contract_id: str, used: int, limit: int) -> str:
    return build_guidance_message(
        what=f"Federation rate limit exceeded for '{contract_id}'.",
        why=f"Used {used} calls and limit is {limit}.",
        fix="Increase rate_limit or reduce request volume.",
        example="rate_limit:\n  calls_per_minute: 120",
    )


def schema_mismatch_message(label: str, detail: str) -> str:
    return build_guidance_message(
        what=f"Federation {label} schema check failed.",
        why=detail,
        fix="Match payload fields and types to federation.yaml.",
        example="input_schema:\n  customer_id: number",
    )


__all__ = [
    "duplicate_contract_message",
    "invalid_auth_message",
    "invalid_config_message",
    "invalid_rate_limit_message",
    "invalid_schema_message",
    "invalid_usage_message",
    "missing_config_message",
    "missing_contract_message",
    "missing_field_message",
    "rate_limit_exceeded_message",
    "schema_mismatch_message",
]
