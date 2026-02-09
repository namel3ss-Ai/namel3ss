from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.app_loader import load_app_archive
from namel3ss.runtime.app_validator import build_inspection_payload, validate_loaded_archive
from namel3ss.tools.app_packager import inspect_source_app


def run_inspect_command(args: list[str]) -> int:
    try:
        target = _parse_args(args)
        if target.suffix == ".ai":
            payload = inspect_source_app(target)
        elif target.suffix == ".n3a":
            archive = load_app_archive(target)
            validate_loaded_archive(archive, mode="production")
            payload = build_inspection_payload(archive)
        else:
            raise Namel3ssError("This file is not a namel3ss app.")
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    except Namel3ssError as err:
        print(str(err), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> Path:
    if len(args) != 1:
        raise Namel3ssError("Inspect takes one app file.")
    path = Path(args[0])
    if not path.exists() or not path.is_file():
        raise Namel3ssError("This file is not a namel3ss app.")
    return path


__all__ = ["run_inspect_command"]
