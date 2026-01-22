from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from namel3ss.config.model import AppConfig

_BACKENDS: dict[str, "BackendAdapter"] = {}


@dataclass(frozen=True)
class BackendDescriptor:
    target: str
    kind: str
    enabled: bool
    descriptor: str | None = None
    replicas: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "target": self.target,
            "kind": self.kind,
            "enabled": self.enabled,
            "descriptor": self.descriptor,
            "replicas": list(self.replicas),
        }


class BackendAdapter(Protocol):
    name: str

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor: ...

    def sql_type_for(self, type_name: str) -> str: ...

    def normalize_error(self, err: Exception) -> str: ...


def register_backend(adapter: BackendAdapter) -> None:
    _BACKENDS[adapter.name] = adapter


def resolve_backend(target: str) -> BackendAdapter | None:
    _ensure_default_backends()
    return _BACKENDS.get(target)


def describe_backend(config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
    adapter = resolve_backend((config.persistence.target or "memory").strip().lower())
    if adapter is not None:
        return adapter.describe(config, project_root=project_root)
    return BackendDescriptor(
        target=config.persistence.target or "memory",
        kind="unknown",
        enabled=False,
        descriptor="unsupported",
        replicas=_replica_descriptors(config),
    )


def _replica_descriptors(config: AppConfig) -> tuple[str, ...]:
    raw = list(getattr(config.persistence, "replica_urls", []) or [])
    descriptors = []
    for value in raw:
        text = str(value or "").strip()
        descriptors.append("url set" if text else "url missing")
    return tuple(descriptors)


class _MemoryBackend:
    name = "memory"

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
        return BackendDescriptor(
            target="memory",
            kind="memory",
            enabled=False,
            descriptor="memory",
            replicas=_replica_descriptors(config),
        )

    def sql_type_for(self, type_name: str) -> str:
        return "TEXT"

    def normalize_error(self, err: Exception) -> str:
        return "memory store error"


class _EdgeBackend:
    name = "edge"

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
        descriptor = "edge url set" if config.persistence.edge_kv_url else "edge url missing"
        return BackendDescriptor(
            target="edge",
            kind="edge",
            enabled=False,
            descriptor=descriptor,
            replicas=_replica_descriptors(config),
        )

    def sql_type_for(self, type_name: str) -> str:
        return "TEXT"

    def normalize_error(self, err: Exception) -> str:
        return "edge store error"


def _ensure_default_backends() -> None:
    if "memory" not in _BACKENDS:
        register_backend(_MemoryBackend())
    if "edge" not in _BACKENDS:
        register_backend(_EdgeBackend())
    if "postgres" not in _BACKENDS:
        from namel3ss.runtime.data import postgres_backend  # noqa: F401
    if "sqlite" not in _BACKENDS:
        from namel3ss.runtime.data import sqlite_backend  # noqa: F401
    if "mysql" not in _BACKENDS:
        from namel3ss.runtime.data import mysql_backend  # noqa: F401


__all__ = [
    "BackendAdapter",
    "BackendDescriptor",
    "describe_backend",
    "register_backend",
    "resolve_backend",
]
