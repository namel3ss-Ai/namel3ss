from __future__ import annotations

from namel3ss.persistence.store import StoredDefinitions
from namel3ss.runtime.security import load_sensitive_config
from namel3ss.security_encryption import load_encryption_service
from namel3ss.runtime.security.encryption_utils import encrypt_prompt_entry


def build_definitions(program) -> StoredDefinitions:
    routes = [_route_payload(route) for route in getattr(program, "routes", []) or []]
    flow_names = {route.get("flow") for route in routes if route.get("flow")}
    flows = [{"name": name} for name in sorted(flow_names)]
    sensitive_config = load_sensitive_config(getattr(program, "project_root", None), getattr(program, "app_path", None))
    requires_key = any(sensitive_config.flows.values())
    service = load_encryption_service(
        getattr(program, "project_root", None),
        getattr(program, "app_path", None),
        required=requires_key,
    )
    models = _ai_models(program, sensitive_config, service)
    return StoredDefinitions(routes=routes, flows=flows, models=models)


def should_persist(definitions: StoredDefinitions) -> bool:
    return bool(definitions.routes or definitions.models)


def _route_payload(route) -> dict:
    return {
        "name": route.name,
        "path": route.path,
        "method": route.method,
        "flow": route.flow_name,
        "upload": bool(route.upload) if route.upload else False,
        "generated": bool(getattr(route, "generated", False)),
        "parameters": _field_payload(route.parameters),
        "request": _field_payload(route.request),
        "response": _field_payload(route.response),
    }


def _field_payload(fields: dict | None) -> dict | None:
    if not fields:
        return None
    return {name: getattr(field, "type_name", None) for name, field in fields.items()}


def _ai_models(program, sensitive_config, service) -> list[dict]:
    entries: dict[str, dict] = {}
    for flow in getattr(program, "flows", []) or []:
        metadata = getattr(flow, "ai_metadata", None)
        if metadata is None:
            continue
        key = flow.name
        payload = _model_payload(flow.name, metadata)
        if service and sensitive_config.is_sensitive(flow.name):
            payload = encrypt_prompt_entry(payload, service)
        entries[key] = payload
    for flow in getattr(program, "ai_flows", []) or []:
        key = flow.name
        payload = {
            "flow": flow.name,
            "kind": flow.kind,
            "model": flow.model,
            "prompt": flow.prompt,
            "dataset": flow.dataset,
            "output_type": flow.output_type,
            "labels": list(flow.labels) if flow.labels else None,
            "sources": list(flow.sources) if flow.sources else None,
        }
        if service and sensitive_config.is_sensitive(flow.name):
            payload = encrypt_prompt_entry(payload, service)
        entries[key] = payload
    ordered = sorted(entries.items(), key=lambda item: item[0])
    return [item[1] for item in ordered]


def _model_payload(name: str, metadata) -> dict:
    return {
        "flow": name,
        "kind": getattr(metadata, "kind", None),
        "model": metadata.model,
        "prompt": metadata.prompt,
        "dataset": metadata.dataset,
        "output_type": getattr(metadata, "output_type", None),
        "labels": list(getattr(metadata, "labels", []) or []) or None,
        "sources": list(getattr(metadata, "sources", []) or []) or None,
    }


__all__ = ["build_definitions", "should_persist"]
