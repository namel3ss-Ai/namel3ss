from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.contract.api import contract as build_contract
from namel3ss.contract.builder import build_contract_pack
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def run_exists_command(args: list[str]) -> int:
    app_path = None
    json_mode = False
    for arg in args:
        if arg == "--json":
            json_mode = True
            continue
        if arg.startswith("-"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="exists only accepts an optional app path and --json.",
                    fix="Run n3 exists or n3 exists app.ai.",
                    example="n3 exists app.ai",
                )
            )
        if app_path is None:
            app_path = arg
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for exists.",
                why="exists accepts at most one app path.",
                fix="Run n3 exists or n3 exists app.ai.",
                example="n3 exists app.ai",
            )
        )

    return _run_exists(app_path, json_mode=json_mode)


def _run_exists(app_path: str | None, *, json_mode: bool) -> int:
    project_root = Path.cwd()
    contract_dir = project_root / ".namel3ss" / "contract"
    last_json = contract_dir / "last.json"
    last_plain = contract_dir / "last.plain"
    last_exists = contract_dir / "last.exists.txt"

    if app_path is None and last_json.exists():
        if json_mode:
            print(last_json.read_text(encoding="utf-8").rstrip())
            return 0
        if last_plain.exists():
            print(last_plain.read_text(encoding="utf-8").rstrip())
            return 0
        print("Contract artifacts are incomplete. Run `n3 exists app.ai`.")
        return 1

    resolved = _resolve_app_path(app_path)
    if resolved is None:
        if app_path:
            print(f"Missing app file: {app_path}. Run `n3 exists app.ai`.")
        else:
            print("Missing app.ai in this folder. Run `n3 exists app.ai`.")
        return 1

    source = resolved.read_text(encoding="utf-8")
    contract_obj = build_contract(source)
    setattr(contract_obj.program, "app_path", resolved)
    setattr(contract_obj.program, "project_root", resolved.parent)
    build_contract_pack(contract_obj)

    if json_mode and last_json.exists():
        print(last_json.read_text(encoding="utf-8").rstrip())
        return 0
    if last_exists.exists():
        print(last_exists.read_text(encoding="utf-8").rstrip())
        return 0
    print("Contract artifacts are missing. Run `n3 exists app.ai`.")
    return 1


def _resolve_app_path(app_path: str | None) -> Path | None:
    try:
        return resolve_app_path(app_path)
    except Namel3ssError:
        return None


__all__ = ["run_exists_command"]
