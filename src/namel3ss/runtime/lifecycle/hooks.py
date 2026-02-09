from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.migrations.migration_runner import (
    apply_migrations,
    build_migration_status,
    require_migration_ready,
)
from namel3ss.runtime.persistence import describe_persistence_backend


@dataclass(frozen=True)
class LifecycleSnapshot:
    target: str
    persistence_backend: dict[str, object]
    migration_status: dict[str, object]
    phases: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "persistence_backend": self.persistence_backend,
            "migration_status": self.migration_status,
            "phases": list(self.phases),
        }


def run_startup_hooks(
    *,
    target: str,
    program: object | None,
    config: AppConfig,
    project_root: str | Path | None,
    app_path: str | Path | None,
    allow_pending_migrations: bool,
    auto_migrate: bool,
    dry_run: bool = False,
) -> LifecycleSnapshot:
    project_root_path = _as_path(project_root)
    app_path_path = _as_path(app_path)
    backend = describe_persistence_backend(
        config,
        project_root=project_root_path,
        app_path=app_path_path,
    )
    phases = ["startup"]
    if auto_migrate:
        result = apply_migrations(
            program,
            project_root=project_root_path,
            config=config,
            dry_run=dry_run,
        )
        status = result.get("migration_status") if isinstance(result.get("migration_status"), dict) else {}
    else:
        status = require_migration_ready(
            program,
            project_root=project_root_path,
            allow_pending=allow_pending_migrations,
        )
    phases.append("migrate")
    if not status:
        status = build_migration_status(program, project_root=project_root_path)
    phases.append("ready")
    return LifecycleSnapshot(
        target=str(target or "local"),
        persistence_backend=backend,
        migration_status=status,
        phases=tuple(phases),
    )


def run_shutdown_hooks(snapshot: LifecycleSnapshot | None) -> dict[str, object]:
    if snapshot is None:
        return {"phase": "shutdown", "ok": True}
    payload = snapshot.as_dict()
    payload["phase"] = "shutdown"
    payload["ok"] = True
    return payload


def _as_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    return Path(value)


__all__ = ["LifecycleSnapshot", "run_shutdown_hooks", "run_startup_hooks"]
