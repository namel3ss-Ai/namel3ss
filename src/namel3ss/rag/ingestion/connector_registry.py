from __future__ import annotations

from copy import deepcopy


CONNECTOR_REGISTRY_SCHEMA_VERSION = "rag.connector_registry@1"

_DEFAULT_CONNECTOR_SPECS = [
    {
        "connector_id": "connector.gdrive",
        "name": "Google Drive",
        "source_type": "connector:gdrive",
        "sync_mode": "incremental",
        "cursor_field": "cursor",
        "enabled": False,
    },
    {
        "connector_id": "connector.github",
        "name": "GitHub",
        "source_type": "connector:github",
        "sync_mode": "incremental",
        "cursor_field": "cursor",
        "enabled": False,
    },
    {
        "connector_id": "connector.slack",
        "name": "Slack",
        "source_type": "connector:slack",
        "sync_mode": "incremental",
        "cursor_field": "cursor",
        "enabled": False,
    },
]


def ensure_connector_registry(
    state: dict,
    *,
    connector_specs: list[dict[str, object]] | None = None,
    schema_version: str = CONNECTOR_REGISTRY_SCHEMA_VERSION,
) -> dict[str, object]:
    rag_connectors = state.get("rag_connectors")
    if not isinstance(rag_connectors, dict):
        rag_connectors = {}

    registry_source = rag_connectors.get("registry")
    existing = registry_source if isinstance(registry_source, list) else []
    baseline = list_default_connectors() if connector_specs is None else [_normalize_spec(entry) for entry in connector_specs]

    merged: dict[str, dict[str, object]] = {entry["connector_id"]: dict(entry) for entry in baseline}
    for entry in existing:
        normalized = _normalize_spec(entry)
        connector_id = normalized["connector_id"]
        if connector_id in merged:
            merged[connector_id] = _merge_spec(merged[connector_id], normalized)
        else:
            merged[connector_id] = normalized

    rag_connectors = {
        "schema_version": _text(rag_connectors.get("schema_version")) or schema_version,
        "registry": [merged[key] for key in sorted(merged.keys())],
    }
    state["rag_connectors"] = rag_connectors
    return deepcopy(rag_connectors)


def list_default_connectors() -> list[dict[str, object]]:
    rows = [_normalize_spec(entry) for entry in _DEFAULT_CONNECTOR_SPECS]
    rows.sort(key=lambda entry: entry["connector_id"])
    return rows


def list_connector_specs(state: dict, *, include_disabled: bool = True) -> list[dict[str, object]]:
    registry = ensure_connector_registry(state)
    rows = list(registry.get("registry") or [])
    if not include_disabled:
        rows = [entry for entry in rows if bool(entry.get("enabled"))]
    return [deepcopy(_normalize_spec(entry)) for entry in rows]


def upsert_connector_spec(state: dict, connector_spec: dict[str, object]) -> dict[str, object]:
    normalized = _normalize_spec(connector_spec)
    registry = ensure_connector_registry(state)
    rows = list(registry.get("registry") or [])
    mapped: dict[str, dict[str, object]] = {entry["connector_id"]: _normalize_spec(entry) for entry in rows}
    connector_id = normalized["connector_id"]
    if connector_id in mapped:
        mapped[connector_id] = _merge_spec(mapped[connector_id], normalized)
    else:
        mapped[connector_id] = normalized
    state["rag_connectors"] = {
        "schema_version": _text(registry.get("schema_version")) or CONNECTOR_REGISTRY_SCHEMA_VERSION,
        "registry": [mapped[key] for key in sorted(mapped.keys())],
    }
    return deepcopy(mapped[connector_id])


def set_connector_enabled(state: dict, connector_id: str, enabled: bool) -> dict[str, object]:
    specs = list_connector_specs(state)
    connector_key = _text(connector_id)
    mapped: dict[str, dict[str, object]] = {entry["connector_id"]: dict(entry) for entry in specs}
    if connector_key not in mapped:
        mapped[connector_key] = _normalize_spec(
            {
                "connector_id": connector_key,
                "name": connector_key,
                "source_type": connector_key,
                "enabled": bool(enabled),
            }
        )
    mapped[connector_key]["enabled"] = bool(enabled)
    state["rag_connectors"] = {
        "schema_version": CONNECTOR_REGISTRY_SCHEMA_VERSION,
        "registry": [mapped[key] for key in sorted(mapped.keys())],
    }
    return deepcopy(mapped[connector_key])


def _merge_spec(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    payload = dict(base)
    for key in sorted(override.keys()):
        payload[key] = override[key]
    return _normalize_spec(payload)


def _normalize_spec(value: object) -> dict[str, object]:
    data = value if isinstance(value, dict) else {}
    connector_id = _text(data.get("connector_id") or data.get("id"))
    source_type = _text(data.get("source_type"))
    return {
        "connector_id": connector_id,
        "cursor_field": _text(data.get("cursor_field")) or "cursor",
        "enabled": bool(data.get("enabled")),
        "name": _text(data.get("name")) or connector_id,
        "source_type": source_type or connector_id,
        "sync_mode": _text(data.get("sync_mode")) or "incremental",
    }


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


__all__ = [
    "CONNECTOR_REGISTRY_SCHEMA_VERSION",
    "ensure_connector_registry",
    "list_connector_specs",
    "list_default_connectors",
    "set_connector_enabled",
    "upsert_connector_spec",
]
