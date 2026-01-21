from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.data.backend_interface import describe_backend
from namel3ss.runtime.data.data_export import load_last_export
from namel3ss.runtime.data.data_import import load_last_import
from namel3ss.runtime.data.migration_runner import build_plan, status_payload
from namel3ss.runtime.data.migration_store import load_last_plan
from namel3ss.secrets import collect_secret_values


def build_data_status_payload(
    config: AppConfig,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> dict:
    backend = describe_backend(config, project_root=Path(project_root) if project_root else None)
    payload: dict[str, object] = {
        "ok": True,
        "backend": backend.as_dict(),
    }
    if project_root:
        export_summary = load_last_export(project_root)
        if export_summary:
            payload["export"] = export_summary
        import_summary = load_last_import(project_root)
        if import_summary:
            payload["import"] = import_summary
    secret_values = collect_secret_values(config)
    scrubbed = scrub_payload(
        payload,
        secret_values=secret_values,
        project_root=project_root,
        app_path=app_path,
    )
    return scrubbed if isinstance(scrubbed, dict) else payload


def build_migrations_status_payload(program, *, project_root: str | Path) -> dict:
    records = sorted(getattr(program, "records", []), key=lambda rec: rec.name)
    return status_payload(records, project_root=project_root)


def build_migrations_plan_payload(program, *, project_root: str | Path) -> dict:
    last_plan = load_last_plan(project_root)
    if isinstance(last_plan, dict):
        return {"ok": True, "plan": last_plan}
    records = sorted(getattr(program, "records", []), key=lambda rec: rec.name)
    plan = build_plan(records, project_root=project_root)
    return {"ok": True, "plan": plan.as_dict()}


__all__ = [
    "build_data_status_payload",
    "build_migrations_plan_payload",
    "build_migrations_status_payload",
]
