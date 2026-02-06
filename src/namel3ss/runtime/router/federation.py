from __future__ import annotations

from dataclasses import dataclass

from namel3ss.determinism import canonical_json_dumps
from namel3ss.federation.contracts import (
    FederationContract,
    record_contract_usage,
    validate_contract_call,
    validate_contract_output,
)

_INTERNAL_KEYS = {
    "filter",
    "format",
    "page",
    "page_size",
    "source_tenant",
    "target_tenant",
    "tenant",
    "tenant_id",
    "version",
}


@dataclass(frozen=True)
class FederationDispatchContext:
    source_tenant: str
    target_tenant: str

    @property
    def is_cross_tenant(self) -> bool:
        return bool(self.source_tenant and self.target_tenant and self.source_tenant != self.target_tenant)


def build_federation_context(
    *,
    headers: dict[str, str],
    query_values: dict[str, str],
    identity: dict | None,
    target_tenant: str | None,
) -> FederationDispatchContext | None:
    source = _source_tenant(headers=headers, query_values=query_values, identity=identity, target_tenant=target_tenant)
    target = str(target_tenant or "").strip().lower()
    if not source or not target:
        return None
    return FederationDispatchContext(source_tenant=source, target_tenant=target)


def validate_federated_input(
    *,
    project_root: str | None,
    app_path: str | None,
    context: FederationDispatchContext,
    flow_name: str,
    input_payload: dict[str, object],
) -> tuple[FederationContract, int]:
    payload = federation_payload(input_payload)
    contract = validate_contract_call(
        project_root=project_root,
        app_path=app_path,
        source_tenant=context.source_tenant,
        target_tenant=context.target_tenant,
        flow_name=flow_name,
        payload=payload,
    )
    return contract, _payload_size(payload)


def validate_federated_output_schema(contract: FederationContract, response_payload: dict[str, object]) -> int:
    payload = federation_payload(response_payload)
    validate_contract_output(contract, payload)
    return _payload_size(payload)


def record_federated_usage(
    *,
    project_root: str | None,
    app_path: str | None,
    contract: FederationContract | None,
    status: str,
    bytes_in: int,
    bytes_out: int,
    error: str = "",
) -> None:
    if contract is None:
        return
    try:
        record_contract_usage(
            project_root=project_root,
            app_path=app_path,
            contract=contract,
            status=status,
            bytes_in=max(0, int(bytes_in)),
            bytes_out=max(0, int(bytes_out)),
            error=str(error or "").strip(),
        )
    except Exception:
        # Usage logging should not mask route-level success/failure semantics.
        return


def federation_audit_details(
    *,
    context: FederationDispatchContext | None,
    contract: FederationContract | None,
    bytes_in: int,
    bytes_out: int,
) -> dict[str, object]:
    if context is None or not context.is_cross_tenant:
        return {}
    details: dict[str, object] = {
        "federated": True,
        "source_tenant": context.source_tenant,
        "target_tenant": context.target_tenant,
        "bytes_in": max(0, int(bytes_in)),
        "bytes_out": max(0, int(bytes_out)),
    }
    if contract is not None:
        details["contract_id"] = contract.contract_id()
    return details


def federation_payload(payload: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key in sorted(payload.keys(), key=lambda item: str(item)):
        name = str(key)
        if name in _INTERNAL_KEYS:
            continue
        out[name] = payload[key]
    return out


def _source_tenant(
    *,
    headers: dict[str, str],
    query_values: dict[str, str],
    identity: dict | None,
    target_tenant: str | None,
) -> str | None:
    explicit = str(
        query_values.get("source_tenant")
        or headers.get("X-N3-Source-Tenant")
        or headers.get("x-n3-source-tenant")
        or ""
    ).strip().lower()
    if explicit:
        return explicit
    if isinstance(identity, dict):
        for key in ("tenant", "tenant_id"):
            value = str(identity.get(key) or "").strip().lower()
            if value:
                return value
        tenants = identity.get("tenants")
        if isinstance(tenants, list):
            values = [str(item or "").strip().lower() for item in tenants if str(item or "").strip()]
            if values:
                fallback = str(target_tenant or "").strip().lower()
                if fallback in values and len(values) > 1:
                    for value in values:
                        if value != fallback:
                            return value
                return values[0]
    return str(target_tenant or "").strip().lower() or None


def _payload_size(payload: dict[str, object]) -> int:
    text = canonical_json_dumps(payload, pretty=False, drop_run_keys=False)
    return len(text.encode("utf-8"))


__all__ = [
    "FederationDispatchContext",
    "build_federation_context",
    "federation_audit_details",
    "federation_payload",
    "record_federated_usage",
    "validate_federated_input",
    "validate_federated_output_schema",
]
