from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.authoring_bundle import bundle_pack
from namel3ss.runtime.packs.authoring_paths import resolve_pack_dir
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_bundle(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    target = None
    out_dir = Path(".")
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--out":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_message("--out"))
            out_dir = Path(args[idx + 1])
            idx += 2
            continue
        if item.startswith("--out="):
            out_dir = Path(item.split("=", 1)[1])
            idx += 1
            continue
        if target is None:
            target = item
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not target:
        raise Namel3ssError(_missing_target_message())
    pack_dir = _resolve_pack_dir(target)
    result = bundle_pack(pack_dir, out_dir=out_dir)
    payload = {
        "status": "ok",
        "pack_id": result.pack_id,
        "version": result.version,
        "bundle_path": str(result.bundle_path),
        "file_count": result.file_count,
        "digest": result.digest,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Bundle created at {result.bundle_path.as_posix()}")
    return 0


def _print_usage() -> None:
    usage = """Usage:
  n3 packs bundle path_or_pack --out dir --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _resolve_pack_dir(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    app_path = resolve_app_path(None)
    return resolve_pack_dir(app_path.parent, value)


def _missing_target_message() -> str:
    return build_guidance_message(
        what="Pack target is missing.",
        why="You must provide a path or pack id.",
        fix="Pass a pack directory or pack id.",
        example="n3 packs bundle ./pack --out ./dist",
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs bundle accepts --out only.",
        fix="Remove the extra arguments.",
        example="n3 packs bundle ./pack --out ./dist",
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Missing value for {flag}.",
        why="The flag expects a value.",
        fix="Provide a value after the flag.",
        example=f"{flag} ./dist",
    )


__all__ = ["run_packs_bundle"]
