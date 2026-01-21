from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.compatibility import apply_migration, detect_declared_spec, plan_migration
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.data.migration_runner import apply_plan, build_plan, rollback_plan, status_payload
from namel3ss.runtime.data.migration_store import MigrationState, load_state, write_plan, write_state
from namel3ss.runtime.storage.factory import create_store


@dataclass(frozen=True)
class _MigrateParams:
    app_arg: str | None
    from_version: str | None
    to_version: str | None
    dry: bool
    check: bool
    json_mode: bool


def run_migrate_command(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    if remaining and remaining[0] in {"plan", "apply", "status", "rollback"}:
        return _run_data_migrate_command(remaining, overrides)
    return _run_spec_migrate_command(args)


def _run_spec_migrate_command(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    params = _parse_args(remaining)
    if params.app_arg and overrides.app_path:
        raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
    app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
    source = app_path.read_text(encoding="utf-8")
    declared = detect_declared_spec(source)
    if params.from_version and params.from_version != declared:
        raise Namel3ssError(
            build_guidance_message(
                what="Spec version does not match --from.",
                why=f"App declares {declared} but --from was {params.from_version}.",
                fix="Update the flag or edit the spec declaration before migrating.",
                example=f"n3 migrate --from {declared} --to 1.0",
            )
        )
    plan = plan_migration(source, from_version=declared, to_version=params.to_version)
    result = apply_migration(source, plan)

    if params.json_mode:
        payload = {
            "ok": True,
            "path": app_path.as_posix(),
            "changed": result.changed,
            "plan": asdict(result.plan),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human(app_path, declared, result)

    if params.check:
        return 1 if result.changed else 0
    if params.dry or not result.changed:
        return 0

    app_path.write_text(result.source, encoding="utf-8")
    return 0


@dataclass(frozen=True)
class _DataMigrateParams:
    command: str
    app_arg: str | None
    json_mode: bool


def _run_data_migrate_command(args: list[str], overrides) -> int:
    params = _parse_data_args(args)
    if params.app_arg and overrides.app_path:
        raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
    app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
    program, _sources = load_program(app_path.as_posix())
    config = load_config(app_path=app_path, root=overrides.project_root)
    records = list(getattr(program, "records", []))
    project_root = app_path.parent

    if params.command == "plan":
        plan = build_plan(records, project_root=project_root)
        state = load_state(project_root)
        write_plan(project_root, plan.plan_id, plan.as_dict())
        write_state(project_root, MigrationState(last_plan_id=plan.plan_id, applied_plan_id=state.applied_plan_id))
        if params.json_mode:
            _print_json({"ok": True, "plan": plan.as_dict()})
        else:
            _print_plan(plan)
        return 0

    if params.command == "status":
        payload = status_payload(records, project_root=project_root)
        if params.json_mode:
            _print_json(payload)
        else:
            _print_status(payload)
        return 0

    if params.command == "apply":
        store = create_store(config=config)
        try:
            payload = apply_plan(records, project_root=project_root, store=store)
        finally:
            _close_store(store)
        if params.json_mode:
            _print_json(payload)
        else:
            _print_apply(payload)
        return 0

    if params.command == "rollback":
        payload = rollback_plan(project_root=project_root)
        if params.json_mode:
            _print_json(payload)
        else:
            _print_rollback(payload)
        return 0

    raise Namel3ssError(f"Unknown migrate command '{params.command}'.")


def _parse_args(args: list[str]) -> _MigrateParams:
    app_arg = None
    from_version = None
    to_version = None
    dry = False
    check = False
    json_mode = False
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--from":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--from"))
            from_version = args[idx + 1]
            idx += 2
            continue
        if arg == "--to":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--to"))
            to_version = args[idx + 1]
            idx += 2
            continue
        if arg == "--dry":
            dry = True
            idx += 1
            continue
        if arg == "--check":
            check = True
            idx += 1
            continue
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message())
    return _MigrateParams(
        app_arg=app_arg,
        from_version=from_version,
        to_version=to_version,
        dry=dry,
        check=check,
        json_mode=json_mode,
    )


def _parse_data_args(args: list[str]) -> _DataMigrateParams:
    if not args:
        raise Namel3ssError(_data_usage_message())
    command = args[0]
    if command not in {"plan", "apply", "status", "rollback"}:
        raise Namel3ssError(_data_usage_message())
    app_arg = None
    json_mode = False
    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message())
    return _DataMigrateParams(command=command, app_arg=app_arg, json_mode=json_mode)


def _print_json(payload: dict) -> None:
    print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))


def _print_plan(plan) -> None:
    summary = plan.summary or {}
    pending = "yes" if summary.get("pending") else "no"
    breaking = "yes" if summary.get("breaking") else "no"
    print(f"Migration plan: {plan.plan_id}")
    print(f"Pending: {pending}")
    print(f"Breaking: {breaking}")
    if not summary.get("pending"):
        print("No migrations pending.")
        return
    print("Changes:")
    for change in plan.changes:
        print(f"  - {_format_change(change)}")


def _print_status(payload: dict) -> None:
    pending = "yes" if payload.get("pending") else "no"
    breaking = "yes" if payload.get("breaking") else "no"
    reversible = "yes" if payload.get("reversible") else "no"
    plan_id = payload.get("plan_id") or "none"
    applied = payload.get("applied_plan_id") or "none"
    print(f"Plan: {plan_id}")
    print(f"Applied: {applied}")
    print(f"Pending: {pending}")
    print(f"Breaking: {breaking}")
    print(f"Reversible: {reversible}")
    if payload.get("plan_changed"):
        print("Plan changed: yes")


def _print_apply(payload: dict) -> None:
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    plan_id = plan.get("plan_id") or "none"
    print(f"Applied migration plan: {plan_id}")


def _print_rollback(payload: dict) -> None:
    rolled = payload.get("rolled_back") or "none"
    print(f"Rolled back migration plan: {rolled}")


def _close_store(store) -> None:
    closer = getattr(store, "close", None)
    if callable(closer):
        try:
            closer()
        except Exception:
            pass


def _print_human(app_path: Path, declared: str, result) -> None:
    if not result.changed:
        print(f"{app_path.name} is already compatible with spec {declared}.")
        return
    print(f"Migrated {app_path.name} spec {result.plan.from_version} -> {result.plan.to_version}.")
    if result.plan.steps:
        print("Steps:")
        for step in result.plan.steps:
            print(f"  - {step}")


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="Migration flags require a version value.",
        fix=f"Pass a version after {flag}.",
        example=f"n3 migrate {flag} 1.0",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="migrate supports --from, --to, --dry, --check, and --json.",
        fix="Remove the unsupported flag.",
        example="n3 migrate app.ai --to 1.0",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many arguments for migrate.",
        why="migrate accepts a single app path plus flags.",
        fix="Remove extra positional arguments.",
        example="n3 migrate app.ai --to 1.0",
    )


def _data_usage_message() -> str:
    return build_guidance_message(
        what="Migration command is missing a subcommand.",
        why="Use plan, apply, status, or rollback to manage data migrations.",
        fix="Pick a migrate subcommand.",
        example="n3 migrate plan app.ai",
    )


def _format_change(change: dict) -> str:
    kind = str(change.get("kind") or "")
    record = change.get("record") or ""
    field = change.get("field") or ""
    if kind == "record_removed":
        return f'record "{record}" was removed'
    if kind == "record_added":
        return f'record "{record}" was added'
    if kind == "record_tenant_key_changed":
        before = change.get("before")
        after = change.get("after")
        return f'record "{record}" tenant_key changed from {before} to {after}'
    if kind == "record_ttl_changed":
        before = change.get("before")
        after = change.get("after")
        return f'record "{record}" ttl_hours changed from {before} to {after}'
    if kind == "field_removed":
        return f'record "{record}" field "{field}" was removed'
    if kind == "field_added_required":
        return f'record "{record}" added required field "{field}"'
    if kind == "field_added_optional":
        return f'record "{record}" added optional field "{field}"'
    if kind == "field_type_changed":
        before = change.get("before")
        after = change.get("after")
        return f'record "{record}" field "{field}" changed type from {before} to {after}'
    if kind == "field_constraint_changed":
        before = change.get("before")
        after = change.get("after")
        return f'record "{record}" field "{field}" changed constraints from {before} to {after}'
    return f"{kind} on record {record}"


__all__ = ["run_migrate_command"]
