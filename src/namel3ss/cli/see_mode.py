from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ui.explain.builder import build_ui_explain_pack, write_ui_explain_artifacts


def run_see_command(args: list[str]) -> int:
    if args:
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for see.",
                why="see does not accept extra input.",
                fix="Run n3 see.",
                example="n3 see",
            )
        )
    _run_see()
    return 0


def _run_see() -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    ui_dir = project_root / ".namel3ss" / "ui"
    last_json = ui_dir / "last.json"
    last_text = ui_dir / "last.see.txt"
    if last_json.exists():
        payload = _read_json(last_json)
        if payload is not None:
            if last_text.exists():
                print(last_text.read_text(encoding="utf-8").rstrip())
                return
            text = write_ui_explain_artifacts(project_root, payload)
            print(text)
            return

    pack = build_ui_explain_pack(project_root, app_path.as_posix())
    text = write_ui_explain_artifacts(project_root, pack)
    print(text)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = ["run_see_command"]
