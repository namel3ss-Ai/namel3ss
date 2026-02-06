from __future__ import annotations

import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.governance.audit import record_audit_entry
from namel3ss.governance.secrets import (
    add_secret,
    get_secret,
    list_secrets,
    master_key_path,
    remove_secret,
)



def run_secret_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params["app_arg"])
        project_root = app_path.parent

        if params["subcommand"] == "list":
            secrets = list_secrets(project_root, app_path)
            payload = {
                "ok": True,
                "count": len(secrets),
                "master_key_path": master_key_path().as_posix(),
                "secrets": secrets,
            }
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user="cli",
                action="secret_list",
                resource="vault",
                status="success",
                details={"count": len(secrets)},
            )
            return _emit(payload, json_mode=params["json_mode"])

        if params["subcommand"] == "add":
            path, entry = add_secret(
                project_root=project_root,
                app_path=app_path,
                name=params["name"],
                value=params["value"],
                owner=params["owner"] or "cli",
            )
            payload = {
                "ok": True,
                "vault_path": path.as_posix(),
                "secret": entry.to_public_dict(),
                "master_key_path": master_key_path().as_posix(),
            }
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user=params["owner"] or "cli",
                action="secret_add",
                resource=str(params["name"]),
                status="success",
                details={"vault_path": path.as_posix()},
            )
            return _emit(payload, json_mode=params["json_mode"])

        if params["subcommand"] == "get":
            value = get_secret(
                project_root=project_root,
                app_path=app_path,
                name=params["name"],
            )
            payload = {
                "ok": True,
                "name": params["name"],
                "value": value,
            }
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user="cli",
                action="secret_get",
                resource=str(params["name"]),
                status="success",
                details={"source": "vault"},
            )
            return _emit(payload, json_mode=params["json_mode"])

        if params["subcommand"] == "remove":
            path, removed = remove_secret(
                project_root=project_root,
                app_path=app_path,
                name=params["name"],
            )
            payload = {
                "ok": True,
                "vault_path": path.as_posix(),
                "removed": removed,
                "master_key_path": master_key_path().as_posix(),
            }
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user=params["owner"] or "cli",
                action="secret_remove",
                resource=str(params["name"]),
                status="success",
                details={"vault_path": path.as_posix()},
            )
            return _emit(payload, json_mode=params["json_mode"])

        raise Namel3ssError(_unknown_subcommand_message(str(params["subcommand"])))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1



def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "app_arg": None, "json_mode": False}

    subcommand = str(args[0]).strip().lower()
    json_mode = False
    owner = None
    positional: list[str] = []
    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg == "--owner":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message("--owner"))
            owner = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg, subcommand=subcommand))
        positional.append(arg)
        idx += 1

    if subcommand == "list":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "app_arg": app_arg,
            "json_mode": json_mode,
            "owner": owner,
        }

    if subcommand == "add":
        if len(positional) < 2:
            raise Namel3ssError(_missing_secret_message(subcommand))
        name = positional[0]
        value = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "app_arg": app_arg,
            "json_mode": json_mode,
            "name": name,
            "value": value,
            "owner": owner,
        }

    if subcommand == "get":
        if not positional:
            raise Namel3ssError(_missing_secret_message(subcommand))
        name = positional[0]
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "app_arg": app_arg,
            "json_mode": json_mode,
            "name": name,
            "owner": owner,
        }

    if subcommand == "remove":
        if not positional:
            raise Namel3ssError(_missing_secret_message(subcommand))
        name = positional[0]
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return {
            "subcommand": subcommand,
            "app_arg": app_arg,
            "json_mode": json_mode,
            "name": name,
            "owner": owner,
        }

    raise Namel3ssError(_unknown_subcommand_message(subcommand))



def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    if not bool(payload.get("ok")):
        print("Secret command failed.")
        return 1
    if "secrets" in payload:
        print("Secrets")
        print(f"  count: {payload.get('count')}")
        print(f"  master_key_path: {payload.get('master_key_path')}")
        for item in payload.get("secrets") or []:
            if not isinstance(item, dict):
                continue
            print(f"  - {item.get('name')} owner={item.get('owner')} created_at={item.get('created_at')}")
        return 0
    if "secret" in payload and isinstance(payload["secret"], dict):
        secret = payload["secret"]
        print("Secret added")
        print(f"  name: {secret.get('name')}")
        print(f"  owner: {secret.get('owner')}")
        print(f"  vault_path: {payload.get('vault_path')}")
        return 0
    if "removed" in payload and isinstance(payload["removed"], dict):
        removed = payload["removed"]
        print("Secret removed")
        print(f"  name: {removed.get('name')}")
        print(f"  owner: {removed.get('owner')}")
        print(f"  vault_path: {payload.get('vault_path')}")
        return 0
    print(payload.get("value") or "")
    return 0



def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 secret list [app.ai] [--json]\n"
        "  n3 secret add <name> <value> [--owner USER] [app.ai] [--json]\n"
        "  n3 secret get <name> [app.ai] [--json]\n"
        "  n3 secret remove <name> [app.ai] [--json]"
    )



def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown secret command '{subcommand}'.",
        why="Supported commands are list, add, get, and remove.",
        fix="Use one of the supported subcommands.",
        example="n3 secret list --json",
    )



def _unknown_flag_message(flag: str, *, subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why=f"secret {subcommand} does not accept this flag.",
        fix="Remove the unsupported flag.",
        example=f"n3 secret {subcommand} --json",
    )



def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example="n3 secret add db_password value --owner alice",
    )



def _missing_secret_message(subcommand: str) -> str:
    if subcommand == "add":
        return build_guidance_message(
            what="secret add is missing arguments.",
            why="Both name and value are required.",
            fix="Provide secret name and value.",
            example="n3 secret add db_password supersecret",
        )
    if subcommand == "remove":
        return build_guidance_message(
            what="secret remove is missing secret name.",
            why="remove requires one secret name.",
            fix="Provide the secret name.",
            example="n3 secret remove db_password",
        )
    return build_guidance_message(
        what="secret get is missing secret name.",
        why="get requires one secret name.",
        fix="Provide the secret name.",
        example="n3 secret get db_password",
    )



def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"secret {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 secret {subcommand} app.ai",
    )


__all__ = ["run_secret_command"]
