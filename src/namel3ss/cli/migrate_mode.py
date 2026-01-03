from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.compatibility import apply_migration, detect_declared_spec, plan_migration
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


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


__all__ = ["run_migrate_command"]
