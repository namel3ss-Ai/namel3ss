from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def run_fix_command(args: list[str]) -> int:
    json_mode = False
    if args:
        if args == ["--json"]:
            json_mode = True
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="Too many arguments for fix.",
                    why="fix only accepts an optional --json flag.",
                    fix="Run n3 fix or n3 fix --json.",
                    example="n3 fix",
                )
            )
    return _run_fix(json_mode=json_mode)


def _run_fix(*, json_mode: bool) -> int:
    project_root = Path.cwd()
    errors_dir = project_root / ".namel3ss" / "errors"
    last_json = errors_dir / "last.json"
    last_plain = errors_dir / "last.plain"
    if last_json.exists():
        if json_mode:
            print(last_json.read_text(encoding="utf-8").rstrip())
            return 0
        if last_plain.exists():
            print(last_plain.read_text(encoding="utf-8").rstrip())
            return 0
        print("Error pack is incomplete. Run a failing flow to regenerate.")
        return 1
    print("No error recorded yet. Run a flow that fails to generate an error pack.")
    return 1


__all__ = ["run_fix_command"]
