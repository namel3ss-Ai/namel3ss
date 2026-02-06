from __future__ import annotations

import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.governance.audit import record_audit_entry
from namel3ss.governance.policy import check_policies_for_app, enforce_policies_for_app



def run_policy_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params["app_arg"])
        project_root = app_path.parent

        if params["subcommand"] == "check":
            payload = check_policies_for_app(project_root=project_root, app_path=app_path)
            payload["checked_app"] = app_path.as_posix()
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user="cli",
                action="policy_check",
                resource=app_path.name,
                status="success" if bool(payload.get("ok")) else "failure",
                details={"violation_count": int(payload.get("count") or 0)},
            )
            return _emit(payload, json_mode=params["json_mode"])

        if params["subcommand"] == "enforce":
            enforce_policies_for_app(project_root=project_root, app_path=app_path)
            payload = {
                "ok": True,
                "count": 0,
                "violations": [],
                "checked_app": app_path.as_posix(),
            }
            record_audit_entry(
                project_root=project_root,
                app_path=app_path,
                user="cli",
                action="policy_enforce",
                resource=app_path.name,
                status="success",
                details={"violation_count": 0},
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
    if subcommand not in {"check", "enforce"}:
        raise Namel3ssError(_unknown_subcommand_message(subcommand))

    json_mode = False
    app_arg = None
    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg, subcommand=subcommand))
        if app_arg is None:
            app_arg = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message(subcommand))

    return {"subcommand": subcommand, "app_arg": app_arg, "json_mode": json_mode}



def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    if bool(payload.get("ok")):
        print("Policy check passed.")
        return 0
    print("Policy check failed.")
    print(f"  violations: {payload.get('count')}")
    for row in payload.get("violations") or []:
        if not isinstance(row, dict):
            continue
        print(f"  - {row.get('rule_id')}: {row.get('description')}")
    return 1



def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 policy check [app.ai] [--json]\n"
        "  n3 policy enforce [app.ai] [--json]"
    )



def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown policy command '{subcommand}'.",
        why="Supported commands are check and enforce.",
        fix="Use one of the supported subcommands.",
        example="n3 policy check --json",
    )



def _unknown_flag_message(flag: str, *, subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why=f"policy {subcommand} supports only --json.",
        fix="Remove the unsupported flag.",
        example=f"n3 policy {subcommand} --json",
    )



def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"policy {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 policy {subcommand} app.ai",
    )


__all__ = ["run_policy_command"]
