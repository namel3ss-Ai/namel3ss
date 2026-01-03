from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.spec_check.api import check_spec_for_program, load_spec_pack
from namel3ss.spec_check.render_plain import render_when


def run_when_command(args: list[str]) -> int:
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
                    why="when only accepts an optional app path and --json.",
                    fix="Run n3 when or n3 when app.ai.",
                    example="n3 when app.ai",
                )
            )
        if app_path is None:
            app_path = arg
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for when.",
                why="when accepts at most one app path.",
                fix="Run n3 when or n3 when app.ai.",
                example="n3 when app.ai",
            )
        )

    return _run_when(app_path, json_mode=json_mode)


def _run_when(app_path: str | None, *, json_mode: bool) -> int:
    project_root = Path.cwd()
    spec_dir = project_root / ".namel3ss" / "spec"
    last_json = spec_dir / "last.json"
    last_plain = spec_dir / "last.plain"

    if app_path is None and last_json.exists():
        if json_mode:
            print(last_json.read_text(encoding="utf-8").rstrip())
            return 0
        if last_plain.exists():
            print(last_plain.read_text(encoding="utf-8").rstrip())
            return 0
        pack = load_spec_pack(last_json)
        if pack is None:
            print("Spec artifacts are incomplete. Run `n3 when app.ai`.")
            return 1
        print(render_when(pack).rstrip())
        return 0

    resolved = _resolve_app_path(app_path)
    if resolved is None:
        if app_path:
            print(f"Missing app file: {app_path}. Run `n3 when app.ai`.")
        else:
            print("Missing app.ai in this folder. Run `n3 when app.ai`.")
        return 1

    program, _ = load_program(resolved.as_posix())
    declared_spec = getattr(program, "spec_version", None)
    pack = check_spec_for_program(program, str(declared_spec or ""))

    if json_mode and last_json.exists():
        print(last_json.read_text(encoding="utf-8").rstrip())
        return 0
    if last_plain.exists():
        print(last_plain.read_text(encoding="utf-8").rstrip())
        return 0
    print(render_when(pack).rstrip())
    return 0


def _resolve_app_path(app_path: str | None) -> Path | None:
    try:
        return resolve_app_path(app_path)
    except Namel3ssError:
        return None


__all__ = ["run_when_command"]
