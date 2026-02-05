from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.security import load_sensitive_config, save_sensitive_config
from namel3ss.security_encryption import initialize_encryption_key


def run_sensitive_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    cmd = remaining[0] if remaining else "list"
    tail = remaining[1:] if remaining else []
    if cmd == "list":
        return _list_sensitive(app_arg, tail)
    if cmd == "add":
        return _add_sensitive(app_arg, tail)
    if cmd == "remove":
        return _remove_sensitive(app_arg, tail)
    if cmd in {"init-key", "init"}:
        return _init_key(app_arg, tail)
    raise Namel3ssError(f"Unknown sensitive subcommand '{cmd}'. Supported: list, add, remove, init-key")


def _list_sensitive(app_arg: str | None, args: list[str]) -> int:
    json_mode = "--json" in args
    app_path = resolve_app_path(app_arg)
    config = load_sensitive_config(app_path.parent, app_path)
    flows = sorted([name for name, value in config.flows.items() if value])
    if json_mode:
        payload = {"sensitive_flows": flows}
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if not flows:
        print("No sensitive flows configured.")
        return 0
    print("Sensitive flows:")
    for name in flows:
        print(f"- {name}")
    return 0


def _add_sensitive(app_arg: str | None, args: list[str]) -> int:
    flow_name = _require_flow_name(args, "add")
    app_path = resolve_app_path(app_arg)
    config = load_sensitive_config(app_path.parent, app_path)
    updated = dict(config.flows)
    updated[flow_name] = True
    save_sensitive_config(app_path.parent, app_path, type(config)(flows=updated))
    print(f'Marked "{flow_name}" as sensitive.')
    return 0


def _remove_sensitive(app_arg: str | None, args: list[str]) -> int:
    flow_name = _require_flow_name(args, "remove")
    app_path = resolve_app_path(app_arg)
    config = load_sensitive_config(app_path.parent, app_path)
    updated = dict(config.flows)
    if flow_name in updated:
        updated.pop(flow_name, None)
        save_sensitive_config(app_path.parent, app_path, type(config)(flows=updated))
        print(f'Removed "{flow_name}" from sensitive flows.')
        return 0
    print(f'"{flow_name}" is not marked sensitive.')
    return 0


def _init_key(app_arg: str | None, args: list[str]) -> int:
    if args:
        raise Namel3ssError("Usage: n3 sensitive init-key")
    app_path = resolve_app_path(app_arg)
    path = initialize_encryption_key(app_path.parent, app_path)
    print(f"Encryption key ready: {Path(path).as_posix()}")
    return 0


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _require_flow_name(args: list[str], command: str) -> str:
    if not args or args[0].startswith("-"):
        raise Namel3ssError(_missing_flow_name_message(command))
    if len(args) > 1:
        raise Namel3ssError(_too_many_args_message(command))
    return args[0]


def _missing_flow_name_message(command: str) -> str:
    return build_guidance_message(
        what=f"Sensitive {command} requires a flow name.",
        why="No flow name was provided.",
        fix="Provide a flow name after the command.",
        example=f"n3 sensitive {command} process_order",
    )


def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"Too many arguments for sensitive {command}.",
        why="Sensitive commands accept a single flow name.",
        fix="Remove extra arguments.",
        example=f"n3 sensitive {command} process_order",
    )


__all__ = ["run_sensitive_command"]
