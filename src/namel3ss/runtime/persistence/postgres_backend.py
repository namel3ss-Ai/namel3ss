from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.persistence.backend_base import PersistenceBackendDescriptor


class PostgresPersistenceBackend:
    name = "postgres"

    def describe(
        self,
        config: AppConfig,
        *,
        project_root: Path | None,
        app_path: Path | None,
    ) -> PersistenceBackendDescriptor:
        target = str(config.persistence.target or "postgres").strip().lower()
        kind = "postgres" if target == "postgres" else "mysql"
        descriptor = f"{kind} url set" if str(config.persistence.database_url or "").strip() else f"{kind} url missing"
        replicas = tuple(sorted(str(item) for item in (config.persistence.replica_urls or ()) if str(item).strip()))
        return PersistenceBackendDescriptor(
            target=kind,
            kind=kind,
            enabled=bool(str(config.persistence.database_url or "").strip()),
            durable=True,
            deterministic_ordering=True,
            descriptor=descriptor,
            requires_network=True,
            replicas=replicas,
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


__all__ = ["PostgresPersistenceBackend"]
