from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.outcome.api import load_outcome_pack
from namel3ss.outcome.render_plain import render_what


def run_what_command(args: list[str]) -> int:
    json_mode = False
    if args:
        if args == ["--json"]:
            json_mode = True
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="Too many arguments for what.",
                    why="what only accepts an optional --json flag.",
                    fix="Run n3 what or n3 what --json.",
                    example="n3 what",
                )
            )
    return _run_what(json_mode=json_mode)


def _run_what(*, json_mode: bool) -> int:
    project_root = Path.cwd()
    outcome_dir = project_root / ".namel3ss" / "outcome"
    last_json = outcome_dir / "last.json"
    last_plain = outcome_dir / "last.plain"
    if last_json.exists():
        if json_mode:
            print(last_json.read_text(encoding="utf-8").rstrip())
            return 0
        if last_plain.exists():
            print(last_plain.read_text(encoding="utf-8").rstrip())
            return 0
        pack = load_outcome_pack(last_json)
        if pack is None:
            print("Outcome pack is incomplete. Run a flow to regenerate.")
            return 1
        print(render_what(pack).rstrip())
        return 0
    print("No run outcome recorded yet. Run a flow to generate an outcome pack.")
    return 1


__all__ = ["run_what_command"]
