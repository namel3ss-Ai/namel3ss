from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.conventions.formats import load_formats_config


def run_formats_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    cmd = remaining[0] if remaining else "list"
    tail = remaining[1:] if remaining else []
    if cmd == "list":
        return _list_formats(app_arg, tail)
    raise Namel3ssError(f"Unknown formats subcommand '{cmd}'. Supported: list")


def _list_formats(app_arg: str | None, args: list[str]) -> int:
    json_mode = "--json" in args
    if args and not json_mode:
        raise Namel3ssError("Usage: n3 formats list [--json]")
    app_path = resolve_app_path(app_arg)
    config = load_formats_config(app_path.parent, app_path)
    payload = {name: list(formats) for name, formats in sorted(config.routes.items())}
    if json_mode:
        print(canonical_json_dumps({"routes": payload}, pretty=True, drop_run_keys=False))
        return 0
    if not payload:
        print("No route formats configured.")
        return 0
    print("Route formats:")
    for name, formats in payload.items():
        joined = ", ".join(formats) if formats else "json"
        print(f"- {name}: {joined}")
    return 0


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


__all__ = ["run_formats_command"]
