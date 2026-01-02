from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.cli.targets_store import write_json
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.verify import run_verify
from namel3ss.governance.verify_dx import run_verify_dx
from namel3ss.secrets import set_audit_root, set_engine_target
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _VerifyParams:
    app_arg: str | None
    target_raw: str | None
    prod: bool
    dx: bool
    json_mode: bool
    write: bool
    allow_unsafe: bool


def run_verify_command(args: list[str]) -> int:
    params = _parse_args(args)
    if params.dx:
        app_path = resolve_app_path(params.app_arg) if params.app_arg else None
        project_root = app_path.parent if app_path else Path.cwd()
        set_audit_root(project_root)
        report = run_verify_dx(app_path=app_path, project_root=project_root)
        if params.write:
            write_json(project_root / ".namel3ss" / "verify.dx.json", report)
        if params.json_mode:
            print(dumps_pretty(report))
        else:
            _print_dx_summary(report)
        return 0 if report.get("ok") is True else 1
    app_path = resolve_app_path(params.app_arg)
    project_root = app_path.parent
    target = _resolve_target(params.target_raw, project_root)
    set_engine_target(target)
    set_audit_root(project_root)
    report = run_verify(app_path, target=target, prod=params.prod, allow_unsafe=params.allow_unsafe)
    if params.write:
        write_json(project_root / ".namel3ss" / "verify.json", report)
    if params.json_mode:
        print(dumps_pretty(report))
    else:
        _print_summary(report)
    return 0 if report.get("status") == "ok" else 1


def _parse_args(args: list[str]) -> _VerifyParams:
    app_arg = None
    target = None
    prod = False
    dx = False
    json_mode = False
    write = True
    allow_unsafe = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--prod":
            prod = True
            i += 1
            continue
        if arg == "--dx":
            dx = True
            i += 1
            continue
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--allow-unsafe":
            allow_unsafe = True
            i += 1
            continue
        if arg == "--write":
            write = True
            i += 1
            continue
        if arg == "--no-write":
            write = False
            i += 1
            continue
        if arg == "--target":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--target flag is missing a value.",
                        why="Verify needs a target name.",
                        fix="Provide local, service, or edge.",
                        example="n3 verify --target service",
                    )
                )
            target = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --prod, --dx, --json, --allow-unsafe, --target, --write.",
                    fix="Remove the unsupported flag.",
                    example="n3 verify --dx --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="Verify accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 verify app.ai",
            )
        )
    return _VerifyParams(app_arg, target, prod, dx, json_mode, write, allow_unsafe)


def _resolve_target(target_raw: str | None, project_root) -> str:
    if target_raw:
        return parse_target(target_raw).name
    state = load_state(project_root)
    active = state.get("active") or {}
    if active.get("target"):
        return str(active.get("target"))
    return parse_target(None).name


def _print_summary(report: dict) -> None:
    status = report.get("status", "unknown")
    print(f"Verify: {status.upper()}")
    for check in report.get("checks", []):
        label = f"- {check.get('id')}: {check.get('status')}"
        message = check.get("message") or ""
        fix = check.get("fix") or ""
        print(f"{label} • {message}")
        if fix and fix != "None.":
            print(f"  Fix: {fix}")


def _print_dx_summary(report: dict) -> None:
    status = "ok" if report.get("ok") else "fail"
    print(f"Verify DX: {status.upper()}")
    for name, check in report.get("dx", {}).items():
        label = f"- {name}: {check.get('status')}"
        message = check.get("message") or ""
        print(f"{label} • {message}")


__all__ = ["run_verify_command"]
