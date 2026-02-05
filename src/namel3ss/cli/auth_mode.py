from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.auth.route_permissions import (
    RoutePermissions,
    RouteRequirement,
    load_route_permissions,
    save_route_permissions,
)


def run_auth_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    cmd = remaining[0] if remaining else "list"
    tail = remaining[1:] if remaining else []
    if cmd == "list":
        return _list_permissions(app_arg, tail)
    if cmd == "require":
        return _require_permissions(app_arg, tail)
    if cmd == "clear":
        return _clear_permissions(app_arg, tail)
    if cmd == "config":
        return _config_path(app_arg)
    raise Namel3ssError(f"Unknown auth subcommand '{cmd}'. Supported: list, require, clear, config")


def _list_permissions(app_arg: str | None, args: list[str]) -> int:
    json_mode = "--json" in args
    if args and not json_mode:
        raise Namel3ssError("Usage: n3 auth list [--json]")
    app_path = resolve_app_path(app_arg)
    permissions = load_route_permissions(app_path.parent, app_path)
    payload = {
        "routes": {
            name: {
                "roles": list(req.roles),
                "permissions": list(req.permissions),
            }
            for name, req in sorted(permissions.routes.items())
        }
    }
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    if not payload["routes"]:
        print("No route permissions configured.")
        return 0
    print("Route permissions:")
    for name, req in payload["routes"].items():
        roles = ", ".join(req.get("roles") or []) or "none"
        perms = ", ".join(req.get("permissions") or []) or "none"
        print(f"- {name}: roles={roles} permissions={perms}")
    return 0


def _require_permissions(app_arg: str | None, args: list[str]) -> int:
    route_name, roles, permissions = _parse_require_args(args)
    if not roles and not permissions:
        raise Namel3ssError(_missing_requirement_message())
    app_path = resolve_app_path(app_arg)
    current = load_route_permissions(app_path.parent, app_path)
    updated = dict(current.routes)
    updated[route_name] = RouteRequirement(roles=tuple(sorted(roles)), permissions=tuple(sorted(permissions)))
    save_route_permissions(app_path.parent, app_path, RoutePermissions(routes=updated))
    print(f'Updated permissions for "{route_name}".')
    return 0


def _clear_permissions(app_arg: str | None, args: list[str]) -> int:
    route_name = _require_route_name(args, "clear")
    app_path = resolve_app_path(app_arg)
    current = load_route_permissions(app_path.parent, app_path)
    if route_name not in current.routes:
        print(f'No permissions configured for "{route_name}".')
        return 0
    updated = dict(current.routes)
    updated.pop(route_name, None)
    save_route_permissions(app_path.parent, app_path, RoutePermissions(routes=updated))
    print(f'Cleared permissions for "{route_name}".')
    return 0


def _config_path(app_arg: str | None) -> int:
    app_path = resolve_app_path(app_arg)
    path = Path(app_path).parent / ".namel3ss" / "permissions.yaml"
    print(path.as_posix())
    return 0


def _parse_require_args(args: list[str]) -> tuple[str, list[str], list[str]]:
    route_name = None
    roles: list[str] = []
    permissions: list[str] = []
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--role":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--role"))
            roles.append(args[idx + 1])
            idx += 2
            continue
        if arg == "--permission":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--permission"))
            permissions.append(args[idx + 1])
            idx += 2
            continue
        if arg.startswith("-"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if route_name is None:
            route_name = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message("require"))
    if not route_name:
        raise Namel3ssError(_missing_route_name_message("require"))
    return route_name, roles, permissions


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _require_route_name(args: list[str], command: str) -> str:
    if not args or args[0].startswith("-"):
        raise Namel3ssError(_missing_route_name_message(command))
    if len(args) > 1:
        raise Namel3ssError(_too_many_args_message(command))
    return args[0]


def _missing_route_name_message(command: str) -> str:
    return build_guidance_message(
        what=f"Auth {command} requires a route name.",
        why="No route name was provided.",
        fix="Provide a route name after the command.",
        example=f"n3 auth {command} get_user",
    )


def _missing_requirement_message() -> str:
    return build_guidance_message(
        what="Route permissions require a role or permission.",
        why="No roles or permissions were provided.",
        fix="Provide --role or --permission.",
        example="n3 auth require get_user --role admin",
    )


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="The role or permission name is required.",
        fix=f"Provide a value after {flag}.",
        example=f"{flag} admin",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags: --role, --permission.",
        fix="Remove the unsupported flag.",
        example="n3 auth require get_user --role admin",
    )


def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"Too many arguments for auth {command}.",
        why="Auth commands accept a single route name.",
        fix="Remove extra arguments.",
        example=f"n3 auth {command} get_user",
    )


__all__ = ["run_auth_command"]
