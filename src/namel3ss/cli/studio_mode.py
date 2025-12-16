from __future__ import annotations

import sys

from namel3ss.cli.app_loader import load_program
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.render import format_error
from namel3ss.studio.server import start_server


def run_studio(path: str, port: int, dry: bool) -> int:
    source = ""
    try:
        program_ir, source = load_program(path)
        if dry:
            print(f"Studio: http://127.0.0.1:{port}/")
            return 0
        start_server(path, port)
        return 0
    except Namel3ssError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
