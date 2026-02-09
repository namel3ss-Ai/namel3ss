from __future__ import annotations

from pathlib import Path

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.data.migration_runner import apply_plan as apply_data_plan
from namel3ss.runtime.data.migration_runner import status_payload as data_status_payload
from namel3ss.runtime.migrations.schema_version import (
    MIGRATION_STATUS_SCHEMA_VERSION,
    STATE_SCHEMA_VERSION,
)
from namel3ss.runtime.storage.factory import create_store


def build_migration_status(program: object | None, *, project_root: str | Path | None) -> dict[str, object]:
    if project_root is None:
        return _empty_status()
    records = _program_records(program)
    payload = data_status_payload(records, project_root=project_root)
    return {
        "schema_version": MIGRATION_STATUS_SCHEMA_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "plan_id": str(payload.get("plan_id") or ""),
        "last_plan_id": str(payload.get("last_plan_id") or ""),
        "applied_plan_id": str(payload.get("applied_plan_id") or ""),
        "pending": bool(payload.get("pending", False)),
        "breaking": bool(payload.get("breaking", False)),
        "reversible": bool(payload.get("reversible", False)),
        "plan_changed": bool(payload.get("plan_changed", False)),
        "change_count": int(payload.get("change_count", 0) or 0),
    }


def apply_migrations(
    program: object | None,
    *,
    project_root: str | Path | None,
    config: AppConfig,
    dry_run: bool = False,
) -> dict[str, object]:
    status_before = build_migration_status(program, project_root=project_root)
    if dry_run or not status_before.get("pending"):
        return {
            "ok": True,
            "dry_run": bool(dry_run),
            "applied": False,
            "migration_status": status_before,
        }
    if project_root is None:
        return {
            "ok": False,
            "dry_run": False,
            "applied": False,
            "migration_status": status_before,
            "error": "project_root_missing",
        }
    records = _program_records(program)
    store = create_store(config=config)
    try:
        apply_data_plan(records, project_root=project_root, store=store)
    finally:
        _close_store(store)
    status_after = build_migration_status(program, project_root=project_root)
    return {
        "ok": True,
        "dry_run": False,
        "applied": True,
        "migration_status": status_after,
    }


def require_migration_ready(
    program: object | None,
    *,
    project_root: str | Path | None,
    allow_pending: bool,
) -> dict[str, object]:
    status = build_migration_status(program, project_root=project_root)
    if bool(status.get("pending")) and not allow_pending:
        raise Namel3ssError(_pending_migration_message())
    return status


def _program_records(program: object | None) -> list[object]:
    records = list(getattr(program, "records", []) or [])
    return sorted(records, key=lambda entry: str(getattr(entry, "name", "")))


def _close_store(store: object) -> None:
    closer = getattr(store, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _empty_status() -> dict[str, object]:
    return {
        "schema_version": MIGRATION_STATUS_SCHEMA_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "plan_id": "",
        "last_plan_id": "",
        "applied_plan_id": "",
        "pending": False,
        "breaking": False,
        "reversible": True,
        "plan_changed": False,
        "change_count": 0,
    }


def _pending_migration_message() -> str:
    return build_guidance_message(
        what="Pending migrations detected.",
        why="Runtime startup requires deterministic schema state before serving requests.",
        fix="Run n3 migrate or allow pending migrations explicitly.",
        example="n3 migrate --status",
    )


__all__ = [
    "apply_migrations",
    "build_migration_status",
    "require_migration_ready",
]
