from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.persistence.backend_base import PersistenceBackendDescriptor


class MemoryPersistenceBackend:
    name = "memory"

    def describe(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> PersistenceBackendDescriptor:
        return PersistenceBackendDescriptor(
            target="memory",
            kind="memory",
            enabled=False,
            durable=False,
            deterministic_ordering=True,
            descriptor="memory",
            requires_network=False,
            replicas=(),
        )

    def list_state_keys(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> list[str]:
        return ["persistence.backend"]

    def inspect_state_key(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
        key: str,
    ) -> object:
        if key != "persistence.backend":
            return None
        return self.describe(config, project_root=project_root, app_path=app_path).as_dict()

    def export_state(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> dict[str, object]:
        backend = self.describe(config, project_root=project_root, app_path=app_path).as_dict()
        return {
            "keys": ["persistence.backend"],
            "items": {"persistence.backend": backend},
        }


__all__ = ["MemoryPersistenceBackend"]
