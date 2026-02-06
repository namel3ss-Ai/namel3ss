from __future__ import annotations

import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.governance.audit import record_audit_entry
from namel3ss.runtime.security.compliance_status import build_security_status


def run_security_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params["app_arg"])
        payload = build_security_status(app_path.parent, app_path)
        payload["checked_app"] = app_path.as_posix()
        record_audit_entry(
            project_root=app_path.parent,
            app_path=app_path,
            user="cli",
            action="security_check",
            resource=app_path.name,
            status="success" if bool(payload.get("ok")) else "failure",
            details={"violation_count": int(payload.get("count") or 0)},
        )
        return _emit(payload, json_mode=params["json_mode"])
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "app_arg": None, "json_mode": False}
    subcommand = str(args[0]).strip().lower()
    if subcommand != "check":
        raise Namel3ssError(_unknown_subcommand_message(subcommand))
    app_arg = None
    json_mode = False
    for arg in args[1:]:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_arg is None:
            app_arg = arg
            continue
        raise Namel3ssError(_too_many_args_message())
    return {
        "subcommand": "check",
        "app_arg": app_arg,
        "json_mode": json_mode,
    }


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Security check")
    print(f"  ok: {payload.get('ok')}")
    print(f"  violations: {payload.get('count')}")
    configs = payload.get("configs")
    if isinstance(configs, dict):
        for name in ("auth", "security", "retention"):
            item = configs.get(name)
            if not isinstance(item, dict):
                continue
            print(f"  - {name}: configured={item.get('configured')}")
            if item.get("error"):
                print(f"    error: {item.get('error')}")
    requires = payload.get("requires")
    if isinstance(requires, dict):
        print(
            "  requires:"
            f" flows={requires.get('mutating_flow_count', 0)}"
            f" unguarded_flows={requires.get('unguarded_flow_count', 0)}"
            f" pages={requires.get('mutating_page_count', 0)}"
            f" unguarded_pages={requires.get('unguarded_page_count', 0)}"
        )
    violations = payload.get("violations")
    if isinstance(violations, list):
        for row in violations:
            if not isinstance(row, dict):
                continue
            print(f"  * {row.get('code')}: {row.get('message')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print("Usage:\n  n3 security check [app.ai] [--json]")


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown security command '{subcommand}'.",
        why="Supported command is check.",
        fix="Use security check.",
        example="n3 security check --json",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="security check supports only --json.",
        fix="Remove unsupported flags.",
        example="n3 security check --json",
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="security check has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra values.",
        example="n3 security check app.ai",
    )


__all__ = ["run_security_command"]
