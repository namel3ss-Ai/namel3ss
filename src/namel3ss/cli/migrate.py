from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.migrate_mode import run_migrate_command as run_legacy_migrate_command
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.lifecycle.hooks import run_startup_hooks


@dataclass(frozen=True)
class _MigrateParams:
    app_arg: str | None
    dry_run: bool
    status_only: bool
    json_mode: bool
    allow_pending: bool
    auto_apply: bool


def run_migrate_command(args: list[str]) -> int:
    if _delegate_to_legacy(args):
        return run_legacy_migrate_command(args)
    overrides, remaining = parse_project_overrides(args)
    params = _parse_args(remaining)
    if params.app_arg and overrides.app_path:
        raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
    app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
    program, _sources = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=overrides.project_root)
    snapshot = run_startup_hooks(
        target="local",
        program=program,
        config=config,
        project_root=app_path.parent,
        app_path=app_path,
        allow_pending_migrations=params.allow_pending or params.status_only or params.dry_run,
        auto_migrate=params.auto_apply,
        dry_run=params.dry_run,
    )
    payload = {
        "ok": True,
        "target": "local",
        "persistence_backend": snapshot.persistence_backend,
        "migration_status": snapshot.migration_status,
        "state_schema_version": snapshot.migration_status.get("state_schema_version", "state_schema@1"),
        "phases": list(snapshot.phases),
        "dry_run": params.dry_run,
    }
    if params.status_only:
        payload["dry_run"] = False
    if params.json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
    else:
        _print_human(payload)
    return 0


def _delegate_to_legacy(args: list[str]) -> bool:
    if not args:
        return False
    first = args[0]
    if first in {"plan", "apply", "status", "rollback"}:
        return True
    return any(token in {"--from", "--to", "--check"} for token in args)


def _parse_args(args: list[str]) -> _MigrateParams:
    app_arg = None
    dry_run = False
    status_only = False
    json_mode = False
    allow_pending = False
    auto_apply = True
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--dry-run":
            dry_run = True
            auto_apply = False
            idx += 1
            continue
        if arg == "--status":
            status_only = True
            auto_apply = False
            idx += 1
            continue
        if arg == "--allow-pending":
            allow_pending = True
            auto_apply = False
            idx += 1
            continue
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg.startswith("-"):
            raise Namel3ssError(f"Unknown migrate flag '{arg}'.")
        if app_arg is None:
            app_arg = arg
            idx += 1
            continue
        raise Namel3ssError("Too many arguments for migrate command.")
    return _MigrateParams(
        app_arg=app_arg,
        dry_run=dry_run,
        status_only=status_only,
        json_mode=json_mode,
        allow_pending=allow_pending,
        auto_apply=auto_apply,
    )


def _print_human(payload: dict) -> None:
    backend = payload.get("persistence_backend") if isinstance(payload.get("persistence_backend"), dict) else {}
    status = payload.get("migration_status") if isinstance(payload.get("migration_status"), dict) else {}
    print(f"Target: {payload.get('target', 'local')}")
    print(f"Persistence backend: {backend.get('target', 'memory')}")
    print(f"State schema version: {payload.get('state_schema_version', 'state_schema@1')}")
    print(f"Pending migrations: {'yes' if status.get('pending') else 'no'}")
    print(f"Applied plan: {status.get('applied_plan_id') or 'none'}")
    if payload.get("dry_run"):
        print("Dry run: yes")


__all__ = ["run_migrate_command"]
