from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.audit import list_audit_entries, summarize_status
from namel3ss.runtime.security import read_sensitive_audit



def run_audit_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    if remaining and remaining[0] in {"list", "filter"}:
        command = remaining[0]
        tail = remaining[1:]
        if command == "list":
            return _list_audit(app_arg, tail)
        return _filter_audit(app_arg, tail)

    # Backward-compatible legacy behavior: n3 audit [app.ai] [--json]
    json_mode = "--json" in remaining
    if remaining and not json_mode:
        raise Namel3ssError("Usage: n3 audit [app.ai] [--json] OR n3 audit list|filter [app.ai] [--json]")
    app_path = resolve_app_path(app_arg)
    entries = read_sensitive_audit(app_path.parent, app_path)
    if json_mode:
        print(canonical_json_dumps({"entries": entries}, pretty=True, drop_run_keys=False))
        return 0
    if not entries:
        print("No sensitive audit entries recorded.")
        return 0
    print("Sensitive audit:")
    for entry in entries:
        flow_name = entry.get("flow_name") or ""
        action = entry.get("action") or ""
        user = entry.get("user") or ""
        step = entry.get("step_count") or 0
        route = entry.get("route")
        if route:
            print(f"- {flow_name} ({action}, route {route}) by {user} at step {step}")
        else:
            print(f"- {flow_name} ({action}) by {user} at step {step}")
    return 0



def _list_audit(app_arg: str | None, args: list[str]) -> int:
    app_override, json_mode = _parse_list_args(app_arg, args, command="list")
    app_path = resolve_app_path(app_override)
    entries = list_audit_entries(app_path.parent, app_path)
    payload = {
        "ok": True,
        "count": len(entries),
        "entries": entries,
        "status": summarize_status(entries),
    }
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    print("Audit entries")
    print(f"  count: {payload['count']}")
    for entry in entries:
        print(
            f"  - t={entry.get('timestamp')} user={entry.get('user')} "
            f"action={entry.get('action')} resource={entry.get('resource')} status={entry.get('status')}"
        )
    return 0



def _filter_audit(app_arg: str | None, args: list[str]) -> int:
    app_override = app_arg
    json_mode = False
    user = None
    action = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg == "--user":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--user"))
            user = args[idx + 1]
            idx += 2
            continue
        if arg == "--action":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--action"))
            action = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_override is None:
            app_override = arg
            idx += 1
            continue
        raise Namel3ssError(_too_many_args_message("filter"))

    app_path = resolve_app_path(app_override)
    entries = list_audit_entries(app_path.parent, app_path, user=user, action=action)
    payload = {
        "ok": True,
        "count": len(entries),
        "entries": entries,
        "status": summarize_status(entries),
        "filters": {
            "user": user or "",
            "action": action or "",
        },
    }
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    print("Filtered audit entries")
    print(f"  count: {payload['count']}")
    for entry in entries:
        print(
            f"  - t={entry.get('timestamp')} user={entry.get('user')} "
            f"action={entry.get('action')} resource={entry.get('resource')} status={entry.get('status')}"
        )
    return 0



def _parse_list_args(app_arg: str | None, args: list[str], *, command: str) -> tuple[str | None, bool]:
    app_override = app_arg
    json_mode = False
    for arg in args:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        if app_override is None:
            app_override = arg
            continue
        raise Namel3ssError(_too_many_args_message(command))
    return app_override, json_mode



def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args



def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This flag requires a value.",
        fix="Provide a value after the flag.",
        example=f"n3 audit filter {flag} alice",
    )



def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported flags are --json, --user, and --action.",
        fix="Remove unsupported flags.",
        example="n3 audit filter --user alice --json",
    )



def _too_many_args_message(command: str) -> str:
    return build_guidance_message(
        what=f"audit {command} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 audit {command} app.ai",
    )


__all__ = ["run_audit_command"]
