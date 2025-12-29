from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.errors.explain.builder import build_error_explain_pack, write_error_explain_artifacts


def run_fix_command(args: list[str]) -> int:
    if args:
        raise Namel3ssError(
            build_guidance_message(
                what="Too many arguments for fix.",
                why="fix does not accept extra input.",
                fix="Run n3 fix.",
                example="n3 fix",
            )
        )
    _run_fix()
    return 0


def _run_fix() -> None:
    app_path = resolve_app_path(None)
    project_root = Path(app_path).parent
    errors_dir = project_root / ".namel3ss" / "errors"
    last_json = errors_dir / "last.json"
    last_text = errors_dir / "last.fix.txt"
    if last_json.exists():
        payload = _read_json(last_json)
        if payload is not None:
            if last_text.exists():
                print(last_text.read_text(encoding="utf-8").rstrip())
                return
            text = write_error_explain_artifacts(project_root, payload)
            print(text)
            return

    if not _run_pack_exists(project_root):
        print("No run found yet. Try: n3 run app.ai")
        return

    pack = build_error_explain_pack(project_root)
    if pack is None:
        print("No run found yet. Try: n3 run app.ai")
        return
    text = write_error_explain_artifacts(project_root, pack)
    print(text)


def _run_pack_exists(project_root: Path) -> bool:
    run_last = project_root / ".namel3ss" / "run" / "last.json"
    return run_last.exists()


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = ["run_fix_command"]
