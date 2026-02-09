from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class PersistenceBackendDescriptor:
    target: str
    kind: str
    enabled: bool
    durable: bool
    deterministic_ordering: bool
    descriptor: str | None = None
    requires_network: bool = False
    replicas: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "kind": self.kind,
            "enabled": self.enabled,
            "durable": self.durable,
            "deterministic_ordering": self.deterministic_ordering,
            "descriptor": self.descriptor,
            "requires_network": self.requires_network,
            "replicas": list(self.replicas),
        }


class PersistenceBackend(Protocol):
    name: str

    def describe(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> PersistenceBackendDescriptor: ...

    def list_state_keys(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> list[str]: ...

    def inspect_state_key(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
        key: str,
    ) -> object: ...

    def export_state(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> dict[str, object]: ...


_BACKENDS: dict[str, PersistenceBackend] = {}


def register_persistence_backend(backend: PersistenceBackend) -> None:
    _BACKENDS[backend.name] = backend


def resolve_persistence_backend(config: AppConfig) -> PersistenceBackend:
    _ensure_default_backends()
    key = _backend_key(config)
    backend = _BACKENDS.get(key)
    if backend is None:
        raise Namel3ssError(f"Unsupported persistence backend target '{key}'.")
    return backend


def describe_persistence_backend(
    config: AppConfig,
    *,
    project_root: Path | None,
    app_path: Path | None,
) -> dict[str, object]:
    backend = resolve_persistence_backend(config)
    return backend.describe(config, project_root=project_root, app_path=app_path).as_dict()


def list_persistence_state_keys(
    config: AppConfig,
    *,
    project_root: Path | None,
    app_path: Path | None,
) -> list[str]:
    backend = resolve_persistence_backend(config)
    return backend.list_state_keys(config, project_root=project_root, app_path=app_path)


def inspect_persistence_state_key(
    config: AppConfig,
    *,
    project_root: Path | None,
    app_path: Path | None,
    key: str,
) -> object:
    backend = resolve_persistence_backend(config)
    return backend.inspect_state_key(config, project_root=project_root, app_path=app_path, key=key)


def export_persistence_state(
    config: AppConfig,
    *,
    project_root: Path | None,
    app_path: Path | None,
) -> dict[str, object]:
    backend = resolve_persistence_backend(config)
    return backend.export_state(config, project_root=project_root, app_path=app_path)


def _backend_key(config: AppConfig) -> str:
    target = str(getattr(config.persistence, "target", "memory") or "memory").strip().lower()
    if target == "sqlite":
        return "file"
    if target in {"postgres", "mysql"}:
        return "postgres"
    return target


def _ensure_default_backends() -> None:
    if _BACKENDS:
        return
    from namel3ss.runtime.persistence.file_backend import FilePersistenceBackend
    from namel3ss.runtime.persistence.memory_backend import MemoryPersistenceBackend
    from namel3ss.runtime.persistence.postgres_backend import PostgresPersistenceBackend

    register_persistence_backend(MemoryPersistenceBackend())
    register_persistence_backend(FilePersistenceBackend())
    register_persistence_backend(PostgresPersistenceBackend())


__all__ = [
    "PersistenceBackend",
    "PersistenceBackendDescriptor",
    "describe_persistence_backend",
    "export_persistence_state",
    "inspect_persistence_state_key",
    "list_persistence_state_keys",
    "register_persistence_backend",
    "resolve_persistence_backend",
]
