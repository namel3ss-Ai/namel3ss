from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.app_loader import load_app_archive
from namel3ss.runtime.app_validator import build_inspection_payload, validate_loaded_archive
from namel3ss.ui.manifest.display_mode import DISPLAY_MODE_PRODUCTION, DISPLAY_MODE_STUDIO


def run_app_command(args: list[str], *, legacy_runner) -> int:
    if not args:
        return legacy_runner(args)

    first = args[0]
    if _looks_like_archive(first):
        return _run_packaged(args)
    return legacy_runner(args)


def _run_packaged(args: list[str]) -> int:
    try:
        archive_path, mode = _parse_packaged_args(args)
        archive = load_app_archive(archive_path)
        validate_loaded_archive(archive, mode=mode)
        inspection = build_inspection_payload(archive)
        payload = {
            "ok": True,
            "app": inspection.get("app"),
            "checksum": inspection.get("checksum"),
            "mode": mode,
            "namel3ss_version": inspection.get("namel3ss_version"),
        }
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0
    except Namel3ssError as err:
        print(str(err), file=sys.stderr)
        return 1


def _parse_packaged_args(args: list[str]) -> tuple[Path, str]:
    if not args:
        raise Namel3ssError("Run needs an app.n3a file.")
    archive_path = Path(args[0])
    if len(args) == 1:
        mode = DISPLAY_MODE_PRODUCTION
    elif len(args) == 2:
        mode_token = str(args[1]).strip().lower()
        if mode_token not in {DISPLAY_MODE_PRODUCTION, DISPLAY_MODE_STUDIO}:
            raise Namel3ssError("Run mode must be production or studio.")
        mode = mode_token
    else:
        raise Namel3ssError("Run takes app.n3a and optional studio mode.")
    return archive_path, mode


def _looks_like_archive(value: str) -> bool:
    return str(value).strip().lower().endswith(".n3a")


__all__ = ["run_app_command"]
