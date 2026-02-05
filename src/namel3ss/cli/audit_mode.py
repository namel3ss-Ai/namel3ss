from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.security import read_sensitive_audit


def run_audit_command(args: list[str]) -> int:
    app_arg, remaining = _split_app_arg(args)
    json_mode = "--json" in remaining
    if remaining and not json_mode:
        raise Namel3ssError("Usage: n3 audit [app.ai] [--json]")
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


def _split_app_arg(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


__all__ = ["run_audit_command"]
