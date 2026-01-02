from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.studio.server import start_server


def run_studio(path: str, port: int, dry: bool) -> int:
    sources: dict = {}
    try:
        app_path = _resolve_studio_app_path(path)
        program_ir, sources = load_program(app_path.as_posix())
        if dry:
            print(f"Studio: http://127.0.0.1:{port}/")
            return 0
        start_server(app_path, port)
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, sources)), file=sys.stderr)
        return 1


def _resolve_studio_app_path(path: str | None) -> Path:
    try:
        return resolve_app_path(path)
    except Namel3ssError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Studio needs an app file path to resolve tools/ bindings.",
                why="tools.yaml and tools/ require a project root.",
                fix="Run Studio from the folder that contains app.ai or pass the path explicitly.",
                example="cd <project-root> && n3 studio app.ai",
            )
        ) from err
