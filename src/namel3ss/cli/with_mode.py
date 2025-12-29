from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.tools_with.api import load_tools_pack
from namel3ss.tools_with.render_plain import render_with


def run_with_command(args: list[str]) -> int:
    json_mode = False
    if args:
        if args == ["--json"]:
            json_mode = True
        else:
            raise Namel3ssError(
                build_guidance_message(
                    what="Too many arguments for with.",
                    why="with only accepts an optional --json flag.",
                    fix="Run n3 with or n3 with --json.",
                    example="n3 with",
                )
            )
    return _run_with(json_mode=json_mode)


def _run_with(*, json_mode: bool) -> int:
    project_root = Path.cwd()
    tools_dir = project_root / ".namel3ss" / "tools"
    last_json = tools_dir / "last.json"
    last_plain = tools_dir / "last.plain"
    if last_json.exists():
        if json_mode:
            print(last_json.read_text(encoding="utf-8").rstrip())
            return 0
        if last_plain.exists():
            print(last_plain.read_text(encoding="utf-8").rstrip())
            return 0
        pack = load_tools_pack(last_json)
        if pack is None:
            print("Tool report is incomplete. Run a flow to regenerate.")
            return 1
        print(render_with(pack).rstrip())
        return 0
    print("No tool report recorded yet. Run a flow that calls tools to generate it.")
    return 1


__all__ = ["run_with_command"]
