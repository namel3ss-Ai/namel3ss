from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.federation.contracts_errors import (
    duplicate_contract_message,
    invalid_auth_message,
    invalid_config_message,
    invalid_rate_limit_message,
    invalid_schema_message,
    invalid_usage_message,
    missing_config_message,
    missing_contract_message,
    missing_field_message,
    rate_limit_exceeded_message,
    schema_mismatch_message,
)
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


FEDERATION_FILENAME = "federation.yaml"
USAGE_FILENAME = "federation_usage.jsonl"


@dataclass(frozen=True)
class FederationContract:
    source_tenant: str
    target_tenant: str
    flow_name: str
    input_schema: tuple[tuple[str, str], ...]
    output_schema: tuple[tuple[str, str], ...]
    auth: dict[str, str]
    rate_limit_calls_per_minute: int | None

    def contract_id(self) -> str:
        return _contract_id(self.source_tenant, self.target_tenant, self.flow_name)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_tenant": self.source_tenant,
            "target_tenant": self.target_tenant,
            "flow_name": self.flow_name,
            "input_schema": {name: type_name for name, type_name in self.input_schema},
            "output_schema": {name: type_name for name, type_name in self.output_schema},
            "auth": {key: self.auth[key] for key in sorted(self.auth.keys())},
        }
        if self.rate_limit_calls_per_minute is not None:
            payload["rate_limit"] = {"calls_per_minute": int(self.rate_limit_calls_per_minute)}
        return payload


@dataclass(frozen=True)
class FederationConfig:
    contracts: tuple[FederationContract, ...]

    def sorted_contracts(self) -> tuple[FederationContract, ...]:
        return tuple(
            sorted(
                self.contracts,
                key=lambda item: (item.source_tenant, item.target_tenant, item.flow_name),
            )
        )

    def find(self, source_tenant: str, target_tenant: str, flow_name: str) -> FederationContract | None:
        source = _normalize_tenant(source_tenant)
        target = _normalize_tenant(target_tenant)
        flow = _normalize_flow(flow_name)
        for contract in self.contracts:
            if contract.source_tenant == source and contract.target_tenant == target and contract.flow_name == flow:
                return contract
        return None


def federation_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / FEDERATION_FILENAME


def load_federation_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> FederationConfig:
    path = federation_path(project_root, app_path)
    if path is None:
        if required:
            raise Namel3ssError(missing_config_message("federation.yaml"))
        return FederationConfig(contracts=())
    if not path.exists():
        if required:
            raise Namel3ssError(missing_config_message(path.as_posix()))
        return FederationConfig(contracts=())
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(invalid_config_message(path, str(err))) from err
    contracts = _parse_contracts(payload, path=path)
    return FederationConfig(contracts=tuple(contracts))


def save_federation_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: FederationConfig,
) -> Path:
    path = federation_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Federation config path could not be resolved.")
    payload = {"contracts": [item.to_dict() for item in config.sorted_contracts()]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def add_contract(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    source_tenant: str,
    target_tenant: str,
    flow_name: str,
    input_schema: dict[str, str] | None = None,
    output_schema: dict[str, str] | None = None,
    auth: dict[str, str] | None = None,
    rate_limit_calls_per_minute: int | None = None,
) -> tuple[Path, FederationContract]:
    contract = FederationContract(
        source_tenant=_normalize_tenant(source_tenant),
        target_tenant=_normalize_tenant(target_tenant),
        flow_name=_normalize_flow(flow_name),
        input_schema=_normalize_schema(input_schema or {}),
        output_schema=_normalize_schema(output_schema or {}),
        auth=_normalize_auth(auth or {}),
        rate_limit_calls_per_minute=_normalize_rate_limit(rate_limit_calls_per_minute),
    )
    config = load_federation_config(project_root, app_path)
    updated: list[FederationContract] = []
    replaced = False
    for item in config.contracts:
        if item.contract_id() == contract.contract_id():
            if not replaced:
                updated.append(contract)
                replaced = True
            continue
        updated.append(item)
    if not replaced:
        updated.append(contract)
    path = save_federation_config(project_root, app_path, FederationConfig(contracts=tuple(updated)))
    return path, contract


def remove_contract(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    source_tenant: str,
    target_tenant: str,
    flow_name: str,
) -> tuple[Path, FederationContract]:
    config = load_federation_config(project_root, app_path, required=True)
    target = _contract_id(source_tenant, target_tenant, flow_name)
    removed: FederationContract | None = None
    kept: list[FederationContract] = []
    for item in config.contracts:
        if item.contract_id() == target:
            removed = item
            continue
        kept.append(item)
    if removed is None:
        raise Namel3ssError(missing_contract_message(target))
    path = save_federation_config(project_root, app_path, FederationConfig(contracts=tuple(kept)))
    return path, removed


def list_contracts(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    config = load_federation_config(project_root, app_path)
    return [contract.to_dict() for contract in config.sorted_contracts()]


def find_contract(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    source_tenant: str,
    target_tenant: str,
    flow_name: str,
) -> FederationContract | None:
    config = load_federation_config(project_root, app_path)
    return config.find(source_tenant, target_tenant, flow_name)


def validate_contract_call(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    source_tenant: str,
    target_tenant: str,
    flow_name: str,
    payload: dict[str, object],
) -> FederationContract:
    config = load_federation_config(project_root, app_path, required=True)
    contract = config.find(source_tenant, target_tenant, flow_name)
    if contract is None:
        raise Namel3ssError(
            missing_contract_message(_contract_id(source_tenant, target_tenant, flow_name)),
            details={"http_status": 403, "category": "permission", "reason_code": "federation_contract_missing"},
        )
    _enforce_rate_limit(project_root, app_path, contract)
    _validate_payload_schema(payload, contract.input_schema, label="input")
    return contract


def validate_contract_output(contract: FederationContract, payload: dict[str, object]) -> None:
    _validate_payload_schema(payload, contract.output_schema, label="output")


def record_contract_usage(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    contract: FederationContract,
    status: str,
    bytes_in: int,
    bytes_out: int,
    error: str = "",
) -> dict[str, object]:
    path = _usage_path(project_root, app_path, allow_create=True)
    if path is None:
        raise Namel3ssError("Federation usage path could not be resolved.")
    records = _load_usage_records(project_root, app_path)
    step_count = 1 if not records else max(int(row.get("step_count") or 0) for row in records) + 1
    payload = {
        "contract_id": contract.contract_id(),
        "source_tenant": contract.source_tenant,
        "target_tenant": contract.target_tenant,
        "flow_name": contract.flow_name,
        "status": str(status or "").strip().lower() or "unknown",
        "bytes_in": max(0, int(bytes_in)),
        "bytes_out": max(0, int(bytes_out)),
        "error": str(error or "").strip(),
        "step_count": step_count,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(payload, pretty=False, drop_run_keys=False) + "\n")
    return payload


def _parse_contracts(payload: object, *, path: Path) -> list[FederationContract]:
    if isinstance(payload, dict):
        values = payload.get("contracts", payload)
    else:
        values = payload
    if not isinstance(values, list):
        raise Namel3ssError(invalid_config_message(path, "contracts must be a list"))
    items: list[FederationContract] = []
    seen: set[str] = set()
    for row in values:
        if not isinstance(row, dict):
            raise Namel3ssError(invalid_config_message(path, "contract entry must be an object"))
        contract = FederationContract(
            source_tenant=_normalize_tenant(row.get("source_tenant")),
            target_tenant=_normalize_tenant(row.get("target_tenant")),
            flow_name=_normalize_flow(row.get("flow_name")),
            input_schema=_normalize_schema(row.get("input_schema") or {}),
            output_schema=_normalize_schema(row.get("output_schema") or {}),
            auth=_normalize_auth(row.get("auth") or {}),
            rate_limit_calls_per_minute=_parse_rate_limit(row.get("rate_limit")),
        )
        contract_id = contract.contract_id()
        if contract_id in seen:
            raise Namel3ssError(duplicate_contract_message(contract_id))
        seen.add(contract_id)
        items.append(contract)
    return sorted(items, key=lambda item: (item.source_tenant, item.target_tenant, item.flow_name))


def _normalize_tenant(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        raise Namel3ssError(missing_field_message("source_tenant/target_tenant"))
    cleaned: list[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    if not normalized:
        raise Namel3ssError(missing_field_message("source_tenant/target_tenant"))
    return normalized


def _normalize_flow(value: object) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(missing_field_message("flow_name"))


def _normalize_schema(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise Namel3ssError(invalid_schema_message("schema must be a map"))
    rows: list[tuple[str, str]] = []
    for key in sorted(value.keys(), key=lambda item: str(item)):
        name = str(key or "").strip()
        type_name = str(value.get(key) or "").strip()
        if not name or not type_name:
            raise Namel3ssError(invalid_schema_message("schema fields must use name:type"))
        rows.append((name, type_name))
    return tuple(rows)


def _normalize_auth(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise Namel3ssError(invalid_auth_message())
    auth: dict[str, str] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        name = str(key or "").strip()
        if not name:
            continue
        auth[name] = str(value.get(key) or "").strip()
    return auth


def _normalize_rate_limit(value: int | None) -> int | None:
    if value is None:
        return None
    return _parse_rate_limit({"calls_per_minute": value})


def _parse_rate_limit(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = int(value)
    elif isinstance(value, dict):
        raw = value.get("calls_per_minute")
        if raw is None or isinstance(raw, bool):
            return None
        try:
            parsed = int(raw)
        except Exception as err:
            raise Namel3ssError(invalid_rate_limit_message()) from err
    else:
        raise Namel3ssError(invalid_rate_limit_message())
    if parsed <= 0:
        raise Namel3ssError(invalid_rate_limit_message())
    return parsed


def _enforce_rate_limit(
    project_root: str | Path | None,
    app_path: str | Path | None,
    contract: FederationContract,
) -> None:
    if contract.rate_limit_calls_per_minute is None:
        return
    records = _load_usage_records(project_root, app_path)
    used = 0
    for row in records:
        if str(row.get("contract_id")) != contract.contract_id():
            continue
        if str(row.get("status")).lower() != "success":
            continue
        used += 1
    if used >= int(contract.rate_limit_calls_per_minute):
        raise Namel3ssError(
            rate_limit_exceeded_message(contract.contract_id(), used, int(contract.rate_limit_calls_per_minute)),
            details={"http_status": 429, "category": "rate_limit", "reason_code": "federation_rate_limit"},
        )


def _usage_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / USAGE_FILENAME


def _load_usage_records(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    path = _usage_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception as err:
            raise Namel3ssError(invalid_usage_message(path)) from err
        if isinstance(payload, dict):
            rows.append(payload)
    return sorted(rows, key=lambda row: int(row.get("step_count") or 0))


def _validate_payload_schema(payload: dict[str, object], schema: tuple[tuple[str, str], ...], *, label: str) -> None:
    if not isinstance(payload, dict):
        raise Namel3ssError(schema_mismatch_message(label, "payload must be an object"))
    for field_name, type_name in schema:
        if field_name not in payload:
            raise Namel3ssError(schema_mismatch_message(label, f"missing field '{field_name}'"))
        value = payload.get(field_name)
        if not _value_matches_type(value, type_name):
            raise Namel3ssError(schema_mismatch_message(label, f"field '{field_name}' should be {type_name}"))


def _value_matches_type(value: object, type_name: str) -> bool:
    text = str(type_name or "").strip().lower()
    if not text:
        return True
    if text == "text":
        return isinstance(value, str)
    if text == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if text == "boolean":
        return isinstance(value, bool)
    if text.startswith("list<") and text.endswith(">"):
        if not isinstance(value, list):
            return False
        inner = text[5:-1].strip()
        return all(_value_matches_type(item, inner) for item in value)
    if text.startswith("map<"):
        return isinstance(value, dict)
    if text.startswith("record<"):
        return isinstance(value, dict)
    return True


def _contract_id(source_tenant: str, target_tenant: str, flow_name: str) -> str:
    return f"{_normalize_tenant(source_tenant)}->{_normalize_tenant(target_tenant)}:{_normalize_flow(flow_name)}"


__all__ = [
    "FEDERATION_FILENAME",
    "FederationConfig",
    "FederationContract",
    "add_contract",
    "federation_path",
    "find_contract",
    "list_contracts",
    "load_federation_config",
    "record_contract_usage",
    "remove_contract",
    "save_federation_config",
    "validate_contract_call",
    "validate_contract_output",
]
