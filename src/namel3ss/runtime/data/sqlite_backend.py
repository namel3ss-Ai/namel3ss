from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.data.backend_interface import BackendDescriptor, register_backend


def _replica_descriptors(config: AppConfig) -> tuple[str, ...]:
    raw = list(getattr(config.persistence, "replica_urls", []) or [])
    return tuple("url set" if str(value or "").strip() else "url missing" for value in raw)


def _normalize_path(path_value: str | None, project_root: Path | None) -> str | None:
    if path_value is None:
        return None
    try:
        path = Path(path_value)
    except Exception:
        return str(path_value)
    if not path.is_absolute():
        return path.as_posix()
    if project_root:
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except Exception:
            return path.name
    return path.name


class SQLiteBackend:
    name = "sqlite"

    def describe(self, config: AppConfig, *, project_root: Path | None) -> BackendDescriptor:
        path = config.persistence.db_path or ".namel3ss/data.db"
        descriptor = _normalize_path(path, project_root)
        return BackendDescriptor(
            target="sqlite",
            kind="sqlite",
            enabled=True,
            descriptor=descriptor,
            replicas=_replica_descriptors(config),
        )

    def sql_type_for(self, type_name: str) -> str:
        name = type_name.lower()
        if name in {"string", "str", "text", "json"}:
            return "TEXT"
        if name in {"int", "integer"}:
            return "INTEGER"
        if name in {"boolean", "bool"}:
            return "INTEGER"
        if name == "number":
            return "TEXT"
        return "TEXT"

    def normalize_error(self, err: Exception) -> str:
        return "sqlite error"


register_backend(SQLiteBackend())


__all__ = ["SQLiteBackend"]
