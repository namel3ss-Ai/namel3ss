from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.data.backend_interface import BackendDescriptor, register_backend


def _replica_descriptors(config: AppConfig) -> tuple[str, ...]:
    raw = list(getattr(config.persistence, "replica_urls", []) or [])
    return tuple("url set" if str(value or "").strip() else "url missing" for value in raw)


class PostgresBackend:
    name = "postgres"

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
        descriptor = "postgres url set" if config.persistence.database_url else "postgres url missing"
        return BackendDescriptor(
            target="postgres",
            kind="postgres",
            enabled=True,
            descriptor=descriptor,
            replicas=_replica_descriptors(config),
        )

    def sql_type_for(self, type_name: str) -> str:
        name = type_name.lower()
        if name in {"string", "str", "text", "json"}:
            return "TEXT"
        if name in {"int", "integer"}:
            return "BIGINT"
        if name in {"boolean", "bool"}:
            return "BOOLEAN"
        if name == "number":
            return "NUMERIC"
        return "TEXT"

    def normalize_error(self, err: Exception) -> str:
        return "postgres error"


register_backend(PostgresBackend())


__all__ = ["PostgresBackend"]
