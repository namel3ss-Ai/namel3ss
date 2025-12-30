from __future__ import annotations

from dataclasses import dataclass

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.secrets import discover_required_secrets, read_secret_audit, set_audit_root, set_engine_target
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _SecretsParams:
    app_arg: str | None
    target_raw: str | None
    json_mode: bool
    subcommand: str


def run_secrets_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    project_root = app_path.parent
    target = _resolve_target(params.target_raw, project_root)
    set_engine_target(target)
    set_audit_root(project_root)
    if params.subcommand == "audit":
        return _run_audit(project_root, json_mode=params.json_mode)
    return _run_status(app_path, target, json_mode=params.json_mode)


def _run_status(app_path, target: str, *, json_mode: bool) -> int:
    project = load_project(app_path)
    config = load_config(app_path=project.app_path, root=project.app_path.parent)
    refs = discover_required_secrets(project.program, config, target=target, app_path=project.app_path)
    payload = {
        "schema_version": 1,
        "target": target,
        "secrets": [
            {"name": ref.name, "source": ref.source, "available": ref.available, "target": ref.target}
            for ref in refs
        ],
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Secrets status target {target}")
    if not refs:
        print("No secrets required for this app.")
        return 0
    for ref in refs:
        state = "available" if ref.available else "missing"
        print(f"- {ref.name}: {state} source {ref.source}")
    return 0


def _run_audit(project_root, *, json_mode: bool) -> int:
    events = read_secret_audit(project_root)
    payload = {"schema_version": 1, "events": events}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print("Secrets audit")
    if not events:
        print("No secret access recorded yet.")
        return 0
    for entry in events:
        line = f"- {entry.get('secret_name')} by {entry.get('caller')} target {entry.get('target')}"
        print(line)
    return 0


def _parse_args(args: list[str]) -> _SecretsParams:
    app_arg = None
    target = None
    json_mode = False
    subcommand = "status"
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in {"status", "audit"}:
            subcommand = arg
            i += 1
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="Secrets status needs a target name.",
                        fix="Provide local, service, or edge.",
                        example="n3 secrets status --target service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --json, --target.",
                    fix="Remove the unsupported flag.",
                    example="n3 secrets status --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Secrets accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 secrets status app.ai",
            )
        )
    return _SecretsParams(app_arg, target, json_mode, subcommand)


def _resolve_target(target_raw: str | None, project_root) -> str:
    if target_raw:
        return parse_target(target_raw).name
    state = load_state(project_root)
    active = state.get("active") or {}
    if active.get("target"):
        return str(active.get("target"))
    return parse_target(None).name


__all__ = ["run_secrets_command"]
