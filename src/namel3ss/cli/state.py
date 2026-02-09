from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.migrations import build_migration_status
from namel3ss.runtime.persistence import (
    describe_persistence_backend,
    export_persistence_state,
    inspect_persistence_state_key,
    list_persistence_state_keys,
)


@dataclass(frozen=True)
class _StateParams:
    command: str
    app_arg: str | None
    key: str | None
    json_mode: bool


def run_state_command(args: list[str]) -> int:
    overrides, remaining = parse_project_overrides(args)
    params = _parse_state_args(remaining)
    if params.app_arg and overrides.app_path:
        raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
    app_path = resolve_app_path(params.app_arg or overrides.app_path, project_root=overrides.project_root)
    config = load_config(app_path=app_path, root=overrides.project_root)
    project_root = app_path.parent
    backend = describe_persistence_backend(config, project_root=project_root, app_path=app_path)
    migration = build_migration_status(None, project_root=project_root)

    if params.command == "list":
        payload = {
            "ok": True,
            "persistence_backend": backend,
            "state_schema_version": str(migration.get("state_schema_version") or "state_schema@1"),
            "migration_status": migration,
            "keys": list_persistence_state_keys(config, project_root=project_root, app_path=app_path),
        }
        return _print_payload(payload, json_mode=params.json_mode)

    if params.command == "inspect":
        assert params.key is not None
        value = inspect_persistence_state_key(
            config,
            project_root=project_root,
            app_path=app_path,
            key=params.key,
        )
        payload = {
            "ok": value is not None,
            "persistence_backend": backend,
            "state_schema_version": str(migration.get("state_schema_version") or "state_schema@1"),
            "migration_status": migration,
            "key": params.key,
            "value": value,
        }
        return _print_payload(payload, json_mode=params.json_mode)

    if params.command == "export":
        payload = {
            "ok": True,
            "persistence_backend": backend,
            "state_schema_version": str(migration.get("state_schema_version") or "state_schema@1"),
            "migration_status": migration,
            "state": export_persistence_state(config, project_root=project_root, app_path=app_path),
        }
        return _print_payload(payload, json_mode=True if params.json_mode else False)

    raise Namel3ssError(f"Unknown state command '{params.command}'.")


def _parse_state_args(args: list[str]) -> _StateParams:
    command = "list"
    app_arg = None
    key = None
    json_mode = False
    idx = 0
    if idx < len(args) and not args[idx].startswith("-") and args[idx] not in {"list", "inspect", "export"}:
        app_arg = args[idx]
        idx += 1
    if idx < len(args) and args[idx] in {"list", "inspect", "export"}:
        command = args[idx]
        idx += 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if command == "inspect" and key is None and not arg.startswith("-"):
            key = arg
            idx += 1
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            idx += 1
            continue
        raise Namel3ssError("Too many arguments for state command.")
    if command == "inspect" and not key:
        raise Namel3ssError(_missing_key_message())
    return _StateParams(command=command, app_arg=app_arg, key=key, json_mode=json_mode)


def _print_payload(payload: dict, *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if payload.get("ok", True) else 1
    if payload.get("key"):
        print(f"Key: {payload.get('key')}")
        print(f"Found: {'yes' if payload.get('ok') else 'no'}")
    backend = payload.get("persistence_backend") if isinstance(payload.get("persistence_backend"), dict) else {}
    print(f"Backend: {backend.get('target', 'memory')}")
    migration = payload.get("migration_status") if isinstance(payload.get("migration_status"), dict) else {}
    print(f"Pending migrations: {'yes' if migration.get('pending') else 'no'}")
    if isinstance(payload.get("keys"), list):
        print("Keys:")
        for key in payload["keys"]:
            print(f"- {key}")
    if payload.get("key") and payload.get("value") is not None:
        print(canonical_json_dumps({"value": payload.get("value")}, pretty=True, drop_run_keys=False))
    if payload.get("state") is not None:
        print(canonical_json_dumps({"state": payload.get("state")}, pretty=True, drop_run_keys=False))
    return 0 if payload.get("ok", True) else 1


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="state command accepts only --json.",
        fix="Remove unsupported flags.",
        example="n3 state list --json",
    )


def _missing_key_message() -> str:
    return build_guidance_message(
        what="Missing state key.",
        why="state inspect requires a key argument.",
        fix="Provide the key from n3 state list.",
        example="n3 state inspect migrations.state",
    )


__all__ = ["run_state_command"]
