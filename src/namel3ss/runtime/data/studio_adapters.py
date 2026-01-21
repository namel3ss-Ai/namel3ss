from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.module_loader import load_project
from namel3ss.runtime.data.data_routes import (
    build_data_status_payload,
    build_migrations_plan_payload,
    build_migrations_status_payload,
)


def get_data_status_payload(source: str, app_path: str | None) -> dict:
    app_file = _require_app_path(app_path)
    config = load_config(app_path=app_file)
    return build_data_status_payload(config, project_root=app_file.parent, app_path=app_file)


def get_migrations_status_payload(source: str, app_path: str | None) -> dict:
    app_file = _require_app_path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    return build_migrations_status_payload(project.program, project_root=app_file.parent)


def get_migrations_plan_payload(source: str, app_path: str | None) -> dict:
    app_file = _require_app_path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    return build_migrations_plan_payload(project.program, project_root=app_file.parent)


def _require_app_path(app_path: str | None) -> Path:
    if app_path:
        return Path(app_path)
    raise ValueError("app path is required for studio data payloads")


__all__ = [
    "get_data_status_payload",
    "get_migrations_plan_payload",
    "get_migrations_status_payload",
]
