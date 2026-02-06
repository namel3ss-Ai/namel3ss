from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class StoredDefinitions:
    routes: list[dict]
    flows: list[dict]
    models: list[dict]

    def as_dict(self) -> dict:
        return {"routes": list(self.routes), "flows": list(self.flows), "models": list(self.models)}


class Store(Protocol):
    def load_definitions(self) -> StoredDefinitions: ...
    def save_definitions(self, definitions: StoredDefinitions) -> None: ...
    def load_uploads(self) -> list[dict]: ...
    def save_uploads(self, uploads: list[dict]) -> None: ...
    def load_datasets(self) -> list[dict]: ...
    def save_datasets(self, datasets: list[dict]) -> None: ...


def normalize_definitions(payload: object | None) -> StoredDefinitions:
    if not isinstance(payload, dict):
        return StoredDefinitions(routes=[], flows=[], models=[])
    routes = payload.get("routes")
    flows = payload.get("flows")
    models = payload.get("models")
    return StoredDefinitions(
        routes=_normalize_entries(routes),
        flows=_normalize_entries(flows),
        models=_normalize_entries(models),
    )


def merge_definitions(existing: StoredDefinitions, current: StoredDefinitions) -> StoredDefinitions:
    routes = _merge_entries(existing.routes, current.routes, key=_route_key)
    flows = _merge_entries(existing.flows, current.flows, key=_flow_key)
    models = _merge_entries(existing.models, current.models, key=_model_key)
    return StoredDefinitions(routes=routes, flows=flows, models=models)


def _normalize_entries(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _merge_entries(existing: list[dict], current: list[dict], *, key: Callable[[dict], str]) -> list[dict]:
    merged: dict[str, dict] = {}
    for entry in existing:
        ident = key(entry)
        if ident:
            merged[ident] = dict(entry)
    for entry in current:
        ident = key(entry)
        if ident:
            merged[ident] = dict(entry)
    ordered = sorted(merged.items(), key=lambda item: item[0])
    return [item[1] for item in ordered]


def _route_key(entry: dict) -> str:
    return str(entry.get("name") or "")


def _flow_key(entry: dict) -> str:
    return str(entry.get("name") or "")


def _model_key(entry: dict) -> str:
    return str(entry.get("flow") or entry.get("name") or "")


__all__ = ["Store", "StoredDefinitions", "merge_definitions", "normalize_definitions"]
