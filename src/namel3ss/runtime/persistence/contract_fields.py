from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.runtime.migrations.migration_runner import build_migration_status
from namel3ss.runtime.migrations.schema_version import STATE_SCHEMA_VERSION
from namel3ss.runtime.persistence import describe_persistence_backend
from namel3ss.ui.manifest.elements.state_inspector import inject_state_inspector_elements


def attach_persistence_contract_fields(
    response: dict,
    *,
    program_ir: object | None,
    config: AppConfig | None,
) -> dict:
    if not isinstance(response, dict):
        return response
    if config is None:
        return response
    project_root = _as_path(getattr(program_ir, "project_root", None))
    app_path = _as_path(getattr(program_ir, "app_path", None))
    backend = describe_persistence_backend(
        config,
        project_root=project_root,
        app_path=app_path,
    )
    migration_status = _safe_migration_status(program_ir, project_root)
    response["persistence_backend"] = backend
    response["state_schema_version"] = str(migration_status.get("state_schema_version") or STATE_SCHEMA_VERSION)
    response["migration_status"] = migration_status
    ui_payload = response.get("ui")
    if isinstance(ui_payload, dict):
        ui_payload["persistence_backend"] = backend
        ui_payload["state_schema_version"] = response["state_schema_version"]
        ui_payload["migration_status"] = migration_status
        inject_state_inspector_elements(
            ui_payload,
            persistence_backend=backend,
            migration_status=migration_status,
            state_schema_version=response["state_schema_version"],
        )
    return response


def _safe_migration_status(program_ir: object | None, project_root: Path | None) -> dict[str, object]:
    try:
        return build_migration_status(program_ir, project_root=project_root)
    except Exception:
        return {
            "schema_version": "migration_status@1",
            "state_schema_version": STATE_SCHEMA_VERSION,
            "plan_id": "",
            "last_plan_id": "",
            "applied_plan_id": "",
            "pending": False,
            "breaking": False,
            "reversible": True,
            "plan_changed": False,
            "change_count": 0,
            "error": "migration_status_unavailable",
        }


def _as_path(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text:
            return Path(text)
    return None


__all__ = ["attach_persistence_contract_fields"]
