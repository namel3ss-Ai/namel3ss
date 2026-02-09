from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.cli.build_mode import run_build_command
from namel3ss.errors.base import Namel3ssError
from namel3ss.tools.app_packager import build_app_archive


def run_build_archive_command(args: list[str]) -> int:
    if _should_delegate_to_legacy(args):
        return run_build_command(args)
    try:
        app_path, out_path = _parse_build_args(args)
        payload = build_app_archive(app_path, out_path=out_path)
        print(Path(str(payload["archive"])).as_posix())
        return 0
    except Namel3ssError as err:
        print(str(err), file=sys.stderr)
        return 1


def _parse_build_args(args: list[str]) -> tuple[Path, Path | None]:
    if not args:
        raise Namel3ssError("Build needs an app.ai file.")
    app_path: Path | None = None
    out_path: Path | None = None
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--out":
            if i + 1 >= len(args):
                raise Namel3ssError("Build needs a path after --out.")
            out_path = Path(args[i + 1])
            i += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError("Build supports only --out.")
        if app_path is None:
            app_path = Path(token)
            i += 1
            continue
        raise Namel3ssError("Build takes one app file.")
    if app_path is None:
        raise Namel3ssError("Build needs an app.ai file.")
    return app_path, out_path


def _should_delegate_to_legacy(args: list[str]) -> bool:
    if not args:
        return True
    for token in args:
        if token in {"--target", "--json"}:
            return True
    return False


__all__ = ["run_build_archive_command"]
